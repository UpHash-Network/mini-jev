"""CPU-only service contract tests. No torch, transformers, or model needed."""
from __future__ import annotations

import copy
import http.client
import json
import math
import io
import socket
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

from .client import APIError, Choice, ChoiceAnswer, Client, Noul, NoulAnswer, Score, ScoreAnswer
from .schema import Limits, ValidationError, decode_json, validate_request, validate_response
from .server import LocalServer


PAYLOAD = {"state": {"message": "請求を確認してください"}, "questions": {
    "route": {"type": "choice", "instructions": "どの部署？", "criteria": {"billing": "請求", "support": "操作"}},
    "urgent": {"type": "noul", "instructions": "緊急？"},
    "score": {"type": "score", "instructions": "重要度", "criteria": ["低", "中", "高"]},
}}


class FakeEngine:
    model_id = "fake-local-v1"
    max_input_tokens = 128
    ready = True

    def __init__(self, delay=0, error=None, corrupt=None, gate=None):
        self.delay, self.error, self.corrupt = delay, error, corrupt
        self.gate = gate
        self.calls = []
        self.active = 0
        self.max_active = 0
        self.entered = threading.Event()

    def decide_many(self, cases):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.entered.set()
        try:
            self.calls.append(copy.deepcopy(cases))
            if self.gate is not None and not self.gate.wait(3):
                raise RuntimeError("test inference gate was not released")
            time.sleep(self.delay)
            if self.error:
                raise self.error
            output = []
            for case in cases:
                kind = case["type"]
                keys = list(case["criteria"]) if kind != "score" else [str(i) for i in range(len(case["criteria"]))]
                probs = {key: (0.8 if i == 0 else 0.2 / (len(keys) - 1)) for i, key in enumerate(keys)}
                value = keys[0] if kind == "choice" else (probs["true"] if kind == "noul" else sum(int(k) * p for k, p in probs.items()))
                answer = {"type": kind, "label": keys[0], kind: value, "probabilities": probs,
                          "calibrated": False, "probability_semantics": "conditional_on_allowed_label_tokens",
                          "input_tokens": 23, "output_tokens": 0}
                if self.corrupt:
                    self.corrupt(answer)
                output.append(answer)
            return output
        finally:
            self.active -= 1


@contextmanager
def running_server(engine=None, **kwargs):
    engine = engine or FakeEngine()
    server = LocalServer(("127.0.0.1", 0), engine, **kwargs)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield server, engine
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request(server, payload=PAYLOAD, *, raw=None, method="POST", path="/v1/systemone", headers=None):
    connection = http.client.HTTPConnection(*server.server_address, timeout=3)
    body = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode()
    default_headers = {"Content-Type": "application/json"}
    default_headers.update(headers or {})
    try:
        connection.request(method, path, body=None if method == "GET" else body, headers=default_headers)
        response = connection.getresponse()
        return response.status, decode_json(response.read())
    finally:
        connection.close()


class SchemaTests(unittest.TestCase):
    def test_key_ids_are_routing_only_and_state_shared(self):
        identifiers, cases = validate_request(PAYLOAD)
        self.assertEqual(identifiers, ["route", "urgent", "score"])
        self.assertTrue(all(set(case) == {"state", "type", "instructions", "criteria"} for case in cases))
        self.assertTrue(all(case["state"] is PAYLOAD["state"] for case in cases))

    def test_state_types(self):
        for state in ("", [], {}, [1, None, True, {"text": "hello"}]):
            with self.subTest(state=state):
                validate_request({**PAYLOAD, "state": state})
        for state in (None, True, 1, 1.5):
            with self.subTest(state=state), self.assertRaises(ValidationError):
                validate_request({**PAYLOAD, "state": state})

    def test_duplicate_and_nonfinite_and_utf16_json(self):
        for raw in (b'{"state":1,"state":2}', b'{"x":{"a":1,"a":2}}', b'{"x":NaN}', b'{"x":Infinity}', '{"x":1}'.encode("utf-16")):
            with self.subTest(raw=raw), self.assertRaises(ValidationError):
                decode_json(raw)
        for number in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValidationError):
                validate_request({**PAYLOAD, "state": {"number": number}})

    def test_unknown_fields_missing_fields_and_model(self):
        for payload in ({**PAYLOAD, "staet": "x"}, {"state": "x"}, {**PAYLOAD, "model": None},
                        {**PAYLOAD, "model": "wrong"}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                validate_request(payload, active_model="fake-local-v1")
        validate_request({**PAYLOAD, "model": "fake-local-v1"}, active_model="fake-local-v1")
        question = {**PAYLOAD["questions"]["route"], "intruction": "typo"}
        with self.assertRaises(ValidationError):
            validate_request({"state": "x", "questions": {"q": question}})

    def test_choice_and_score_bounds(self):
        for count in (2, 26):
            for kind in ("choice", "score"):
                criteria = {str(i): "description" for i in range(count)} if kind == "choice" else ["description"] * count
                validate_request({"state": "x", "questions": {"q": {"type": kind, "instructions": "choose", "criteria": criteria}}})
        for count in (0, 1, 27):
            for kind in ("choice", "score"):
                criteria = {str(i): "description" for i in range(count)} if kind == "choice" else ["description"] * count
                with self.assertRaises(ValidationError):
                    validate_request({"state": "x", "questions": {"q": {"type": kind, "instructions": "choose", "criteria": criteria}}})

    def test_noul_criteria_and_empty_descriptions(self):
        for criteria in (None, {}, {"true": "yes"}, {"false": "no", "true": ""}, {"false": 0, "true": "yes"}):
            with self.assertRaises(ValidationError):
                validate_request({"state": "x", "questions": {"q": {"type": "noul", "instructions": "question", "criteria": criteria}}})

    def test_limits_and_nesting(self):
        for payload, limits in ((PAYLOAD, Limits(max_questions=2)), (PAYLOAD, Limits(max_body_bytes=10)),
                                ({**PAYLOAD, "state": "abcd"}, Limits(max_text_chars=3))):
            with self.assertRaises(ValidationError):
                validate_request(payload, limits)
        value = {"x": {"y": {"z": "deep"}}}
        with self.assertRaises(ValidationError):
            validate_request({**PAYLOAD, "state": value}, Limits(max_depth=2))


class HTTPTests(unittest.TestCase):
    def test_health_and_typed_response(self):
        with running_server() as (server, engine):
            status, health = request(server, method="GET", path="/health")
            self.assertEqual(status, 200)
            self.assertTrue(health["ready"])
            status, body = request(server)
            self.assertEqual(status, 200)
            identifiers, cases = validate_request(PAYLOAD)
            validate_response(body, identifiers, cases)
            self.assertEqual(body["usage"], {"input_tokens": 69, "output_tokens": 0, "questions": 3})
            self.assertTrue(all("route" not in case for case in engine.calls[0]))
            self.assertEqual(body["answers"]["urgent"]["noul"], 0.2)
            self.assertAlmostEqual(body["answers"]["score"]["score"], 0.3)
            self.assertEqual(body["answers"]["score"]["legend"], {"0": "低", "1": "中", "2": "高"})

    def test_health_not_ready(self):
        engine = FakeEngine()
        engine.ready = False
        with running_server(engine) as (server, _):
            status, body = request(server, method="GET", path="/health")
            self.assertEqual(status, 503)
            self.assertFalse(body["ready"])
            self.assertEqual(request(server)[0], 503)

    def test_confidence_and_calibration_metadata(self):
        def metadata(answer):
            p = answer["probabilities"]
            answer.update(confidence=1 + sum(value * math.log(value) for value in p.values()) / math.log(len(p)),
                          confidence_definition="one_minus_normalized_entropy_not_probability_of_correctness",
                          temperature_calibration_applied=True, calibration_generalization_validated=False)
        with running_server(FakeEngine(corrupt=metadata)) as (server, _):
            client = Client(f"http://127.0.0.1:{server.server_address[1]}")
            result = client.system_one("x", {"q": Noul("question")})
            self.assertGreater(result.answers["q"].confidence, 0)
            self.assertTrue(result.answers["q"].temperature_calibration_applied)
            self.assertFalse(result.answers["q"].calibration_generalization_validated)

    def test_input_read_deadline(self):
        with running_server(request_timeout=0.05) as (server, engine):
            conn = http.client.HTTPConnection(*server.server_address, timeout=1)
            try:
                conn.putrequest("POST", "/v1/systemone")
                conn.putheader("Content-Type", "application/json")
                conn.putheader("Content-Length", "20")
                conn.endheaders(b"{")
                response = conn.getresponse()
                self.assertEqual(response.status, 408)
                response.read()
                self.assertEqual(engine.calls, [])
            finally:
                conn.close()

    def test_duplicate_nonfinite_invalid_json_rejected_before_engine(self):
        with running_server() as (server, engine):
            for raw in (b'{"state": "x", "state": "y", "questions": {}}', b'{"state": [NaN], "questions": {}}', b'{broken', b'{"state":[1e999],"questions":{}}'):
                with self.subTest(raw=raw):
                    self.assertEqual(request(server, raw=raw)[0], 422)
            self.assertEqual(engine.calls, [])

    def test_media_length_size_method_and_path(self):
        with running_server(limits=Limits(max_body_bytes=512)) as (server, engine):
            self.assertEqual(request(server, raw=b"x" * 513)[0], 413)
            self.assertEqual(request(server, raw=b"{}", headers={"Content-Type": "text/plain"})[0], 415)
            self.assertEqual(request(server, raw=b"{}", headers={"Transfer-Encoding": "chunked"})[0], 400)
            self.assertEqual(request(server, raw=b"{}", headers={"Content-Length": "-1"})[0], 400)
            self.assertEqual(request(server, path="/nope")[0], 404)
            self.assertEqual(request(server, method="DELETE")[0], 501)
            self.assertEqual(engine.calls, [])

    def test_browser_origin_and_rebinding_rejected(self):
        with running_server() as (server, engine):
            for headers in ({"Origin": "https://example.test"}, {"Host": "example.test"}):
                self.assertEqual(request(server, headers=headers)[0], 403)
            self.assertEqual(engine.calls, [])
        with self.assertRaises(ValueError):
            LocalServer(("0.0.0.0", 0), FakeEngine())

    def test_model_mismatch_rejected(self):
        with running_server() as (server, engine):
            self.assertEqual(request(server, {**PAYLOAD, "model": "other"})[0], 422)
            self.assertEqual(engine.calls, [])

    def test_engine_input_rejection_is_422(self):
        with running_server(FakeEngine(error=ValueError("private input details"))) as (server, _):
            status, body = request(server)
            self.assertEqual(status, 422)
            self.assertNotIn("private", json.dumps(body))

    def test_engine_error_is_sanitized_and_worker_survives(self):
        with running_server(FakeEngine(error=RuntimeError("secret local path"))) as (server, engine):
            status, body = request(server)
            self.assertEqual(status, 500)
            self.assertNotIn("secret", json.dumps(body))
            engine.error = None
            self.assertEqual(request(server)[0], 200)

    def test_corrupt_results_never_escape(self):
        for corrupt in (lambda x: x.update(probabilities={"a": 1.0}),
                        lambda x: x.update(choice="bad"), lambda x: x.update(input_tokens=True),
                        lambda x: x.update(calibrated="yes"), lambda x: x.update(probabilities={"billing": float("nan"), "support": 0.0})):
            with self.subTest(corrupt=corrupt), running_server(FakeEngine(corrupt=corrupt)) as (server, _):
                self.assertEqual(request(server)[0], 500)

    def test_concurrent_requests_are_serialized(self):
        with running_server(FakeEngine(delay=0.04), max_pending=4) as (server, engine):
            with ThreadPoolExecutor(max_workers=4) as pool:
                statuses = list(pool.map(lambda _: request(server)[0], range(4)))
            self.assertEqual(statuses, [200] * 4)
            self.assertEqual(engine.max_active, 1)

    def test_queue_full_returns_503(self):
        with running_server(FakeEngine(delay=0.2), max_pending=1) as (server, engine):
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(request, server)
                self.assertTrue(engine.entered.wait(1))
                self.assertEqual(request(server)[0], 503)
                self.assertEqual(first.result()[0], 200)

    def test_running_timeout_retains_slot_and_queued_timeout_skips_engine(self):
        with running_server(FakeEngine(delay=0.2), max_pending=2, request_timeout=0.07) as (server, engine):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(request, server)
                self.assertTrue(engine.entered.wait(1))
                second = pool.submit(request, server)
                self.assertEqual(first.result()[0], 504)
                self.assertEqual(second.result()[0], 504)
                self.assertEqual(request(server)[0], 503)
            time.sleep(0.16)
            self.assertEqual(len(engine.calls), 1)
            engine.delay = 0
            self.assertEqual(request(server)[0], 200)

    def test_http_connection_limit(self):
        gate = threading.Event()
        with running_server(FakeEngine(gate=gate), max_connections=1) as (server, engine):
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(request, server)
                try:
                    self.assertTrue(engine.entered.wait(1))
                    status, body = request(server)
                    self.assertEqual(status, 503)
                    self.assertIn("connection limit", body["error"]["message"])
                    self.assertEqual(len(engine.calls), 1)
                finally:
                    gate.set()
                self.assertEqual(first.result()[0], 200)
            self._assert_capacity_recovers(server, engine)

    def _assert_capacity_recovers(self, server, engine):
        # Response receipt and handler teardown can happen on different CPUs.
        # Capacity must return promptly after the occupied request completes.
        deadline = time.monotonic() + 1
        while True:
            status, _ = request(server, method="GET", path="/health")
            if status == 200 or time.monotonic() >= deadline:
                break
            self.assertEqual(status, 503)
            time.sleep(0.005)
        self.assertEqual(status, 200)
        self.assertEqual(request(server)[0], 200)
        self.assertEqual(len(engine.calls), 2)

    def test_connection_rejection_drains_split_headers_and_body(self):
        gate = threading.Event()
        with running_server(FakeEngine(gate=gate), max_connections=1) as (server, engine):
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(request, server)
                try:
                    self.assertTrue(engine.entered.wait(1))
                    body = json.dumps(PAYLOAD).encode()
                    headers = (f"POST /v1/systemone HTTP/1.1\r\nHost: 127.0.0.1:{server.server_address[1]}\r\n"
                               f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n").encode()
                    with socket.create_connection(server.server_address, timeout=1) as connection:
                        connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        for fragment in (headers[:12], headers[12:45], headers[45:], body[:17], body[17:]):
                            connection.sendall(fragment)
                            time.sleep(0.01)
                        response = http.client.HTTPResponse(connection)
                        response.begin()
                        self.assertEqual(response.status, 503)
                        self.assertEqual(response.getheader("Retry-After"), "1")
                        decoded = decode_json(response.read())
                        self.assertEqual(decoded["error"]["code"], "busy")
                        response.close()
                    self.assertEqual(len(engine.calls), 1)
                finally:
                    gate.set()
                self.assertEqual(first.result()[0], 200)
            self._assert_capacity_recovers(server, engine)

    def test_connection_rejection_drains_valid_maximum_body(self):
        gate = threading.Event()
        with running_server(FakeEngine(gate=gate), max_connections=1) as (server, engine):
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(request, server)
                try:
                    self.assertTrue(engine.entered.wait(1))
                    encoded = json.dumps(PAYLOAD).encode()
                    body = encoded + b" " * (server.limits.max_body_bytes - len(encoded))
                    for _ in range(10):
                        status, result = request(server, raw=body)
                        self.assertEqual(status, 503)
                        self.assertEqual(result["error"]["code"], "busy")
                    self.assertEqual(len(engine.calls), 1)
                finally:
                    gate.set()
                self.assertEqual(first.result()[0], 200)
            self._assert_capacity_recovers(server, engine)

    def test_connection_rejection_deadline_releases_accept_loop(self):
        gate = threading.Event()
        with running_server(FakeEngine(gate=gate), max_connections=1) as (server, engine):
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(request, server)
                try:
                    self.assertTrue(engine.entered.wait(1))
                    with socket.create_connection(server.server_address, timeout=1) as slow:
                        slow.sendall(b"POST /v1/systemone HTTP/1.1\r\n")
                        response = http.client.HTTPResponse(slow)
                        response.begin()
                        self.assertEqual(response.status, 503)
                        self.assertEqual(decode_json(response.read())["error"]["code"], "busy")
                        # Dripping bytes must not restart the drain's deadline.
                        # A subsequent ordinary connection must still be served.
                        stop = threading.Event()
                        def trickle():
                            until = time.monotonic() + 2
                            while not stop.wait(0.02) and time.monotonic() < until:
                                try:
                                    slow.sendall(b"X")
                                except OSError:
                                    return
                        sender = threading.Thread(target=trickle, daemon=True)
                        sender.start()
                        try:
                            started = time.monotonic()
                            self.assertEqual(request(server)[0], 503)
                            self.assertLess(time.monotonic() - started, 0.8)
                        finally:
                            stop.set()
                            sender.join(timeout=1)
                            response.close()
                    self.assertEqual(len(engine.calls), 1)
                finally:
                    gate.set()
                self.assertEqual(first.result()[0], 200)
            self._assert_capacity_recovers(server, engine)

    def test_connection_rejection_byte_cap_finishes_before_long_deadline(self):
        gate = threading.Event()
        with running_server(FakeEngine(gate=gate), max_connections=1) as (server, engine):
            # Make the independent byte bound observable before a long timeout.
            server.rejection_timeout = 1.5
            rejected = threading.Event()
            reject = server._reject_connection
            def observed_rejection(connection):
                try:
                    reject(connection)
                finally:
                    rejected.set()
            server._reject_connection = observed_rejection
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(request, server)
                try:
                    self.assertTrue(engine.entered.wait(1))
                    with socket.create_connection(server.server_address, timeout=1) as oversized:
                        started = time.monotonic()
                        try:
                            oversized.sendall(b"POST /v1/systemone HTTP/1.1\r\nX-Fill: "
                                              + b"X" * (server.rejection_drain_bytes + 65536))
                        except (BrokenPipeError, ConnectionResetError):
                            # Oversized/incomplete requests exceed the graceful
                            # delivery policy; the bounded close may reset them.
                            pass
                        self.assertTrue(rejected.wait(0.8))
                        self.assertLess(time.monotonic() - started, 1)
                    self.assertEqual(len(engine.calls), 1)
                finally:
                    gate.set()
                self.assertEqual(first.result()[0], 200)
            self._assert_capacity_recovers(server, engine)

    def test_duplicate_content_length(self):
        with running_server() as (server, _):
            conn = http.client.HTTPConnection(*server.server_address, timeout=1)
            try:
                conn.putrequest("POST", "/v1/systemone")
                conn.putheader("Content-Type", "application/json")
                conn.putheader("Content-Length", "2")
                conn.putheader("Content-Length", "2")
                conn.endheaders(b"{}")
                response = conn.getresponse()
                self.assertEqual(response.status, 400)
                response.read()
            finally:
                conn.close()

    def test_duplicate_content_type(self):
        with running_server() as (server, engine):
            conn = http.client.HTTPConnection(*server.server_address, timeout=1)
            try:
                conn.putrequest("POST", "/v1/systemone")
                conn.putheader("Content-Type", "application/json")
                conn.putheader("Content-Type", "text/plain")
                conn.putheader("Content-Length", "2")
                conn.endheaders(b"{}")
                response = conn.getresponse()
                self.assertEqual(response.status, 415)
                response.read()
                self.assertEqual(engine.calls, [])
            finally:
                conn.close()


class ClientTests(unittest.TestCase):
    def test_typed_client_end_to_end(self):
        with running_server() as (server, _):
            client = Client(f"http://127.0.0.1:{server.server_address[1]}")
            self.assertTrue(client.health()["ready"])
            result = client.system_one("sample", {
                "choice": Choice("choose", {"yes": "yes", "no": "no"}),
                "noul": Noul("yes?"), "score": Score("rate", ("low", "high")),
            }, model="fake-local-v1")
            self.assertIsInstance(result.answers["choice"], ChoiceAnswer)
            self.assertIsInstance(result.answers["noul"], NoulAnswer)
            self.assertIsInstance(result.answers["score"], ScoreAnswer)
            self.assertEqual(result.answers["score"].legend, {"0": "low", "1": "high"})

    def test_client_validation_and_api_error(self):
        with running_server() as (server, engine):
            client = Client(f"http://127.0.0.1:{server.server_address[1]}")
            with self.assertRaises(ValidationError):
                client.system_one("x", {"q": Noul("")})
            with self.assertRaises(APIError) as context:
                client.system_one("x", {"q": Noul("question")}, model="wrong")
            self.assertEqual(context.exception.status, 422)
            self.assertEqual(context.exception.code, "validation_error")
            self.assertEqual(engine.calls, [])

    def test_client_refuses_remote_origins(self):
        for url in ("https://127.0.0.1:1", "http://example.test", "http://127.0.0.1/path", "http://user@127.0.0.1", "http://127.0.0.1?token=a",
                    "http://127.0.0.1:notaport", "http://127.0.0.1:0", "http://127.0.0.1:99999"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                Client(url)

    def test_client_context_manager_and_typed_groups(self):
        with running_server() as (server, _):
            with Client(f"http://127.0.0.1:{server.server_address[1]}") as client:
                response = client.system_one("x", {"c": Choice("choose", {"a": "A", "b": "B"}),
                                                     "n": Noul("question"), "s": Score("score", ["low", "high"])})
                self.assertEqual(set(response.choices), {"c"})
                self.assertEqual(set(response.nouls), {"n"})
                self.assertEqual(set(response.scores), {"s"})
                self.assertEqual(response.choices["c"].choice, "a")
            with self.assertRaisesRegex(RuntimeError, "closed"):
                client.health()
            with self.assertRaisesRegex(RuntimeError, "closed"):
                with client:
                    pass

    def test_client_rejects_inconsistent_responses(self):
        identifiers, cases = validate_request(PAYLOAD)
        with running_server() as (server, _):
            _, body = request(server)
        corruptions = (lambda x: x.update(unknown=1), lambda x: x.update(latency_ms=float("inf")),
                       lambda x: x["usage"].update(output_tokens=1),
                       lambda x: x["answers"]["route"].update(choice="support"),
                       lambda x: x["answers"]["route"].update(label=["billing"]),
                       lambda x: x["answers"]["route"].update(temperature_calibration_applied="yes"),
                       lambda x: x["answers"]["route"].update(confidence=1.0,
                           confidence_definition="one_minus_normalized_entropy_not_probability_of_correctness"),
                       lambda x: x["answers"]["urgent"].update(noul=0.99),
                       lambda x: x["answers"]["score"].update(legend={"0": "wrong"}),
                       lambda x: x["answers"]["score"].update(score=2.0))
        for corruption in corruptions:
            value = copy.deepcopy(body)
            corruption(value)
            with self.assertRaises(ValidationError):
                validate_response(value, identifiers, cases)


class LauncherTests(unittest.TestCase):
    def test_release_config_calibration_paths_and_opt_out(self):
        from run_service import load_config
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory).resolve()
            config = folder / "release_config.json"
            calibration = folder / "temperature.json"
            config.write_text(json.dumps({"model": "fake-local-v1", "revision": "pinned"}))
            calibration.write_text("{}")
            args = load_config(config)
            self.assertEqual(args["temperature_config"], str(calibration))
            self.assertEqual((args["dtype"], args["prompt_style"], args["attention"]), ("float32", "compact", "eager"))
            self.assertIsNone(load_config(config, without_calibration=True)["temperature_config"])
            config.write_text(json.dumps({"temperature_config": None}))
            self.assertIsNone(load_config(config)["temperature_config"])
            config.write_text(json.dumps({"temperature_config": "temperature.json"}))
            self.assertEqual(load_config(config)["temperature_config"], str(calibration))
            calibration.unlink()
            with self.assertRaisesRegex(ValueError, "does not exist"):
                load_config(config)

    def test_release_config_rejects_typos_and_invalid_values(self):
        from run_service import load_config
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "release_config.json"
            for value in ({"dtyep": "float32"}, {"local_files_only": "false"}, {"max_input_tokens": True},
                          {"dtype": "float8"}, {"attention": "flash"}, {"temperature": 0},
                          {"temperature": 10 ** 400}, {"revision": []}):
                config.write_text(json.dumps(value))
                with self.subTest(value=value), self.assertRaises(ValueError):
                    load_config(config)

    def test_print_config_does_not_load_a_model(self):
        from run_service import main
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "release_config.json"
            config.write_text(json.dumps({"model": "deliberately-nonexistent-model"}))
            output = io.StringIO()
            with redirect_stdout(output):
                main(["--config", str(config), "--print-config"])
            self.assertEqual(json.loads(output.getvalue())["model"], "deliberately-nonexistent-model")


if __name__ == "__main__":
    unittest.main(verbosity=2)

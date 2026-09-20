"""A bounded, loopback-only HTTP adapter over one persistent decision engine."""
from __future__ import annotations

import argparse
import concurrent.futures
import ipaddress
import json
import logging
import queue
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .schema import Limits, ValidationError, decode_json, public_answer, validate_request

LOG = logging.getLogger("mini_jev.service")


class BusyError(Exception):
    pass


class InferenceTimeout(Exception):
    pass


@dataclass
class _Job:
    cases: list[dict]
    deadline: float
    future: concurrent.futures.Future = field(default_factory=concurrent.futures.Future)


class InferenceWorker:
    """One engine thread; expired requests never enable overlapping GPU work.

    Running GPU work cannot be safely interrupted. A timed-out running job retains
    its admission slot until its engine call completes. Queued expired jobs skip
    the engine entirely. max_pending includes the currently running job.
    """

    def __init__(self, engine, max_pending=2):
        if type(max_pending) is not int or max_pending < 1:
            raise ValueError("max_pending must be a positive integer")
        self.engine = engine
        self._admission = threading.BoundedSemaphore(max_pending)
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._closed = False
        self._pending = 0
        self.thread = threading.Thread(target=self._run, name="mini-jev-inference", daemon=True)
        self.thread.start()

    @property
    def pending(self):
        with self._lock:
            return self._pending

    @property
    def ready(self):
        with self._lock:
            return not self._closed and self.thread.is_alive() and bool(getattr(self.engine, "ready", True))

    def submit(self, cases, deadline):
        with self._lock:
            if self._closed or not self._admission.acquire(blocking=False):
                raise BusyError()
            self._pending += 1
            job = _Job(cases, deadline)
            self._queue.put(job)
        return job

    def _run(self):
        while True:
            job = self._queue.get()
            if job is None:
                return
            try:
                if time.monotonic() >= job.deadline:
                    job.future.set_exception(InferenceTimeout())
                else:
                    job.future.set_result(self.engine.decide_many(job.cases))
            except Exception as exc:
                job.future.set_exception(exc)
            finally:
                with self._lock:
                    self._pending -= 1
                self._admission.release()

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._queue.put(None)
        self.thread.join(timeout=5)


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8
    rejection_timeout = 0.2
    rejection_drain_bytes = 256 * 1024

    def __init__(self, address, engine, *, limits=Limits(), max_pending=2,
                 request_timeout=30.0, max_connections=16):
        host, port = address
        if host == "localhost":
            host = "127.0.0.1"
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = False
        if not is_loopback or ":" in host:
            raise ValueError("server host must be an IPv4 loopback address (default 127.0.0.1)")
        if isinstance(request_timeout, bool) or not isinstance(request_timeout, (int, float)) or not 0 < request_timeout <= 300:
            raise ValueError("request_timeout must be in (0, 300] seconds")
        if type(max_connections) is not int or max_connections < 1:
            raise ValueError("max_connections must be a positive integer")
        if type(max_pending) is not int or max_pending < 1:
            raise ValueError("max_pending must be a positive integer")
        if not isinstance(getattr(engine, "model_id", None), str):
            raise ValueError("engine must expose model_id")
        self.engine = engine
        self.limits = limits
        self.request_timeout = request_timeout
        self._connections = threading.BoundedSemaphore(max_connections)
        super().__init__((host, port), Handler)
        self.worker = InferenceWorker(engine, max_pending=max_pending)

    def process_request(self, request, client_address):
        if not self._connections.acquire(blocking=False):
            # Do not create an unbounded HTTP handler thread under overload.
            self._reject_connection(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._connections.release()
            raise

    def _reject_connection(self, request):
        payload = b'{"error":{"code":"busy","message":"connection limit reached"}}'
        response = (b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\n"
                    b"Content-Type: application/json\r\nRetry-After: 1\r\nContent-Length: "
                    + str(len(payload)).encode() + b"\r\n\r\n" + payload)
        deadline = time.monotonic() + self.rejection_timeout
        try:
            request.settimeout(self.rejection_timeout)
            request.sendall(response)
            request.shutdown(socket.SHUT_WR)
            # Closing with unread request bytes can reset TCP while a normal
            # client is still sending its POST body, hiding the 503 response.
            # Half-close first and consume pending/following bytes until the
            # peer closes. One absolute deadline and byte cap bound accept-loop
            # work even when a slow or oversized sender never finishes.
            remaining_bytes = self.rejection_drain_bytes
            while remaining_bytes:
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    break
                request.settimeout(remaining_time)
                chunk = request.recv(min(65536, remaining_bytes))
                if not chunk:
                    break
                remaining_bytes -= len(chunk)
        except OSError:
            pass
        finally:
            self.shutdown_request(request)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connections.release()

    def server_close(self):
        super().server_close()
        if hasattr(self, "worker"):
            self.worker.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "MiniJev/1"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(min(10.0, self.server.request_timeout))
        self.started = time.monotonic()
        self.request_id = uuid.uuid4().hex

    def log_message(self, format, *args):
        # Do not log state, questions, URL query values, or request bodies.
        pass

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.close_connection = True
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Request-ID", self.request_id)
            if status == 503:
                self.send_header("Retry-After", "1")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass

    def _error(self, status, code, message):
        self._send(status, {"error": {"code": code, "message": message}, "request_id": self.request_id})

    def send_error(self, code, message=None, explain=None):
        self._error(code, "http_error", "invalid HTTP request")

    def _trusted_request(self):
        # No browser-origin callers or DNS-rebinding Host values. This is a local
        # programmatic API, without cross-origin headers or external listeners.
        if self.headers.get("Origin") is not None:
            self._error(403, "forbidden_origin", "browser-origin requests are not allowed")
            return False
        host_values = self.headers.get_all("Host", [])
        if len(host_values) != 1:
            self._error(400, "invalid_host", "exactly one loopback Host header is required")
            return False
        host = host_values[0].split(":", 1)[0].lower()
        if host != "localhost":
            try:
                if not ipaddress.ip_address(host).is_loopback:
                    raise ValueError()
            except ValueError:
                self._error(403, "invalid_host", "Host must be a loopback address")
                return False
        return True

    def do_GET(self):
        if not self._trusted_request():
            return
        if self.path != "/health":
            self._error(404, "not_found", "unknown endpoint")
            return
        ready = self.server.worker.ready
        self._send(200 if ready else 503, {"ready": ready, "model": self.server.engine.model_id,
                   "pending_requests": self.server.worker.pending,
                   "model_revision": getattr(self.server.engine, "model_revision", None),
                   "max_input_tokens": getattr(self.server.engine, "max_input_tokens", None)})

    def do_POST(self):
        if not self._trusted_request():
            return
        if self.path != "/v1/systemone":
            self._error(404, "not_found", "unknown endpoint")
            return
        if not self.server.worker.ready:
            self._error(503, "not_ready", "inference engine is not ready")
            return
        if self.headers.get("Transfer-Encoding") is not None:
            self._error(400, "invalid_encoding", "chunked requests are not supported")
            return
        lengths = self.headers.get_all("Content-Length", [])
        if not lengths:
            self._error(411, "length_required", "Content-Length is required")
            return
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            self._error(400, "invalid_length", "invalid Content-Length")
            return
        length = int(lengths[0]) if len(lengths[0]) < 16 else self.server.limits.max_body_bytes + 1
        if length > self.server.limits.max_body_bytes:
            self._error(413, "body_too_large", "request body exceeds the size limit")
            return
        if len(self.headers.get_all("Content-Type", [])) != 1 or self.headers.get_content_type() != "application/json":
            self._error(415, "unsupported_media_type", "Content-Type must be application/json")
            return
        try:
            parts, remaining = [], length
            while remaining:
                seconds_left = self.started + self.server.request_timeout - time.monotonic()
                if seconds_left <= 0:
                    raise TimeoutError()
                self.connection.settimeout(min(10.0, seconds_left))
                chunk = self.rfile.read1(min(65536, remaining))
                if not chunk:
                    break
                parts.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(parts)
            if len(raw) != length:
                self._error(400, "incomplete_body", "incomplete request body")
                return
            payload = decode_json(raw)
            identifiers, cases = validate_request(payload, self.server.limits, self.server.engine.model_id)
        except (socket.timeout, TimeoutError):
            self._error(408, "read_timeout", "request body read timed out")
            return
        except ValidationError as exc:
            self._error(422, "validation_error", str(exc))
            return
        deadline = self.started + self.server.request_timeout
        if time.monotonic() >= deadline:
            self._error(504, "deadline_exceeded", "request deadline exceeded")
            return
        try:
            job = self.server.worker.submit(cases, deadline)
        except BusyError:
            self._error(503, "busy", "inference queue is full or shutting down")
            return
        try:
            results = job.future.result(timeout=max(0.0, deadline - time.monotonic()))
        except (concurrent.futures.TimeoutError, InferenceTimeout):
            self._error(504, "deadline_exceeded", "request deadline exceeded; running inference may finish in the background")
            return
        except ValueError:
            self._error(422, "input_rejected", "engine rejected the input; check the model token limit and question criteria")
            return
        except Exception as exc:
            LOG.error("request %s inference failure: %s", self.request_id, type(exc).__name__)
            self._error(500, "inference_error", "inference failed")
            return
        if time.monotonic() >= deadline:
            self._error(504, "deadline_exceeded", "request deadline exceeded")
            return
        try:
            if not isinstance(results, list) or len(results) != len(cases):
                raise ValidationError("backend result count mismatch")
            answers = {identifier: public_answer(result, case)
                       for identifier, result, case in zip(identifiers, results, cases)}
            token_counts = [result.get("input_tokens") for result in results]
            if any(type(count) is not int or count < 0 for count in token_counts):
                raise ValidationError("backend input_tokens is invalid")
            response = {"model": self.server.engine.model_id, "answers": answers,
                        "usage": {"input_tokens": sum(token_counts), "output_tokens": 0, "questions": len(cases)},
                        "latency_ms": (time.monotonic() - self.started) * 1000, "request_id": self.request_id}
            self._send(200, response)
        except (ValidationError, ValueError, TypeError):
            LOG.error("request %s invalid backend output", self.request_id)
            self._error(500, "invalid_backend_output", "inference returned an invalid result")


def serve_engine(engine, *, host="127.0.0.1", port=8765, max_questions=8,
                 max_pending=2, request_timeout=30.0):
    """Serve an already initialized engine until Ctrl-C."""
    with LocalServer((host, port), engine, limits=Limits(max_questions=max_questions),
                     max_pending=max_pending, request_timeout=request_timeout) as server:
        LOG.info("MiniJev ready at http://%s:%s", *server.server_address)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            LOG.info("Stopping MiniJev")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default="Qwen/Qwen3-4B-Instruct-2507")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "mps", "cuda"))
    parser.add_argument("--dtype", default="float32", choices=("float16", "float32", "bfloat16"))
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--temperature-config", help="calibration JSON matching the loaded model runtime")
    parser.add_argument("--revision", help="pinned Hugging Face model revision")
    parser.add_argument("--prompt-style", default="compact", choices=("compact", "structured", "original"))
    parser.add_argument("--attention", default="eager", choices=("eager", "sdpa"))
    parser.add_argument("--allow-download", action="store_true", help="allow Hugging Face to download the selected model")
    parser.add_argument("--max-input-tokens", type=int, default=2048)
    parser.add_argument("--max-questions", type=int, default=8)
    parser.add_argument("--max-pending", type=int, default=2)
    parser.add_argument("--request-timeout", type=float, default=30.0)
    args = parser.parse_args()
    if not 1 <= args.max_questions <= 16:
        parser.error("--max-questions must be between 1 and 16")
    if not 1 <= args.max_input_tokens <= 8192:
        parser.error("--max-input-tokens must be between 1 and 8192")
    if not 0 < args.temperature < float("inf"):
        parser.error("--temperature must be finite and positive")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from release_engine import ReleaseEngine
    LOG.info("Loading %s once; HTTP listener starts after model initialization", args.model)
    engine = ReleaseEngine(model=args.model, device=args.device, dtype=args.dtype,
                           local_files_only=not args.allow_download,
                           max_input_tokens=args.max_input_tokens, temperature=args.temperature,
                           revision=args.revision, prompt_style=args.prompt_style,
                           temperature_config=args.temperature_config, attention=args.attention)
    serve_engine(engine, host=args.host, port=args.port, max_questions=args.max_questions,
                 max_pending=args.max_pending, request_timeout=args.request_timeout)


if __name__ == "__main__":
    main()

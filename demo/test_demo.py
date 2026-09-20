"""CPU integration tests: real local HTTP, existing SDK, test-only fake engine."""
import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import http.client
import json
from pathlib import Path
import threading
import unittest

from demo.server import DemoServer
from service.test_service import FakeEngine, running_server

PAYLOAD = {'state': 'Please check this invoice urgently.', 'questions': {
    'routing': {'type': 'choice', 'instructions': 'Choose the queue.',
                'criteria': {'billing': 'Invoices', 'account': 'Profile', 'technical': 'Software'}},
    'urgent': {'type': 'noul', 'instructions': 'Is urgent handling explicitly requested?',
               'criteria': {'false': 'No', 'true': 'Yes'}},
    'priority': {'type': 'score', 'instructions': 'Choose priority.',
                 'criteria': ['Routine', 'Soon', 'Immediate']}}}


@contextmanager
def running_demo(api_url, timeout=2.):
    server = DemoServer(0, api_url=api_url, api_timeout=timeout)
    worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    worker.start()
    try:
        yield server
    finally:
        server.shutdown(); server.server_close(); worker.join(timeout=2.)


def request(server, *, path='/api/decide', method='POST', payload=None, raw=None,
            headers=None, omit=(), extra_headers=()):
    body = raw if raw is not None else json.dumps(PAYLOAD if payload is None else payload).encode()
    if method == 'GET':
        body = b''
    host = f'127.0.0.1:{server.server_port}'
    fields = {'Host': host, 'Origin': f'http://{host}', 'X-Mini-Jev-Demo': '1',
              'Content-Type': 'application/json', 'Content-Length': str(len(body))}
    fields.update(headers or {})
    for name in omit:
        fields.pop(name, None)
    connection = http.client.HTTPConnection(*server.server_address, timeout=3.)
    try:
        connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for name, value in [*fields.items(), *extra_headers]:
            connection.putheader(name, value)
        connection.endheaders(body)
        response = connection.getresponse()
        data = response.read()
        mime = response.getheader('Content-Type', '')
        return response.status, json.loads(data) if mime.startswith('application/json') else data, dict(response.getheaders())
    finally:
        connection.close()


class DemoIntegrationTests(unittest.TestCase):
    def test_three_types_cross_bridge_with_existing_origin_block_unchanged(self):
        with running_server() as (api, engine), running_demo(f'http://127.0.0.1:{api.server_port}') as demo:
            status, body, _ = request(demo)
            self.assertEqual(status, 200)
            self.assertEqual(body['source'], 'live_api')
            self.assertGreater(body['elapsed_ms'], 0)
            response = body['response']
            self.assertEqual(response['answers']['routing']['choice'], 'billing')
            self.assertAlmostEqual(response['answers']['urgent']['noul'], .2)
            self.assertAlmostEqual(response['answers']['priority']['score'], .3)
            self.assertEqual(response['answers']['priority']['legend'], {'0': 'Routine', '1': 'Soon', '2': 'Immediate'})
            self.assertEqual(response['usage']['output_tokens'], 0)
            self.assertNotIn('confidence', response['answers']['routing'])
            self.assertEqual(len(engine.calls), 1)
            # A browser request still cannot call the original service directly.
            status, _, _ = request(api, path='/v1/systemone')
            self.assertEqual(status, 403)
            self.assertEqual(len(engine.calls), 1)

    def test_health_and_static_assets_need_no_inference(self):
        with running_server() as (api, engine), running_demo(f'http://127.0.0.1:{api.server_port}') as demo:
            status, health, _ = request(demo, method='GET', path='/api/health')
            self.assertEqual(status, 200); self.assertTrue(health['ready'])
            for path in ('/', '/app.js', '/style.css'):
                status, body, headers = request(demo, method='GET', path=path, omit=('Origin', 'X-Mini-Jev-Demo'))
                self.assertEqual(status, 200)
                self.assertTrue(body)
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
                self.assertNotIn('Access-Control-Allow-Origin', headers)
            self.assertEqual(engine.calls, [])
            for path in ('/../native_config.json', '/static/../../README.md', '/?path=secret', '/api/unknown'):
                self.assertEqual(request(demo, method='GET', path=path)[0], 404)

    def test_bad_origin_host_and_missing_custom_header_never_reach_api(self):
        with running_server() as (api, engine), running_demo(f'http://127.0.0.1:{api.server_port}') as demo:
            for headers, omit, extra in [
                ({'Origin': 'https://example.invalid'}, (), ()),
                ({'Origin': 'null'}, (), ()),
                ({'Host': 'evil.invalid'}, (), ()),
                ({'Host': '127.0.0.1:1'}, (), ()),
                ({'Sec-Fetch-Site': 'cross-site'}, (), ()),
                ({}, ('Origin',), ()), ({}, ('X-Mini-Jev-Demo',), ()),
                ({}, (), (('Host', 'localhost'),)),
                ({}, (), (('Origin', f'http://127.0.0.1:{demo.server_port}'),))]:
                with self.subTest(headers=headers, omit=omit, extra=extra):
                    self.assertEqual(request(demo, headers=headers, omit=omit, extra_headers=extra)[0], 403)
            self.assertEqual(engine.calls, [])

    def test_body_framing_limits_and_schema_fail_closed(self):
        with running_server() as (api, engine), running_demo(f'http://127.0.0.1:{api.server_port}') as demo:
            checks = [({'Content-Length': '65537'}, (), (), 413),
                      ({'Content-Length': '-1'}, (), (), 400),
                      ({'Content-Type': 'text/plain'}, (), (), 415),
                      ({'Transfer-Encoding': 'chunked'}, (), (), 400),
                      ({'Content-Encoding': 'gzip'}, (), (), 400),
                      ({}, ('Content-Length',), (), 411),
                      ({}, (), (('Content-Length', '1'),), 400)]
            for headers, omit, extra, status in checks:
                self.assertEqual(request(demo, headers=headers, omit=omit, extra_headers=extra)[0], status)
            for raw in (b'not-json', b'{"state":"x","state":"y"}', b'{"value":NaN}'):
                self.assertEqual(request(demo, raw=raw)[0], 422)
            wrong = copy.deepcopy(PAYLOAD); wrong['questions'].pop('urgent')
            self.assertEqual(request(demo, payload=wrong)[0], 422)
            wrong = copy.deepcopy(PAYLOAD); wrong['api_url'] = 'https://example.invalid'
            self.assertEqual(request(demo, payload=wrong)[0], 422)
            wrong = copy.deepcopy(PAYLOAD); wrong['state'] = 'x' * 8193
            self.assertEqual(request(demo, payload=wrong)[0], 422)
            self.assertEqual(engine.calls, [])

    def test_timeout_returns_error_and_never_a_simulated_answer(self):
        with running_server(FakeEngine(delay=.15)) as (api, _), running_demo(f'http://127.0.0.1:{api.server_port}', timeout=.03) as demo:
            status, body, _ = request(demo)
            self.assertEqual(status, 504)
            self.assertEqual(body['error']['code'], 'api_timeout')
            self.assertNotIn('response', body)

    def test_connection_failure_and_invalid_backend_return_visible_errors(self):
        with running_demo('http://127.0.0.1:1', timeout=.1) as demo:
            self.assertEqual(request(demo)[0], 503)
            status, body, _ = request(demo, method='GET', path='/api/health')
            self.assertEqual(status, 503); self.assertFalse(body['ready'])
        with running_server(FakeEngine(corrupt=lambda answer: answer.update(probabilities={}))) as (api, _), running_demo(f'http://127.0.0.1:{api.server_port}') as demo:
            status, body, _ = request(demo)
            self.assertEqual(status, 500)
            self.assertNotIn('response', body)

    def test_only_one_demo_inference_can_be_in_flight(self):
        gate = threading.Event()
        with running_server(FakeEngine(gate=gate)) as (api, engine), running_demo(f'http://127.0.0.1:{api.server_port}') as demo, ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(request, demo)
            try:
                self.assertTrue(engine.entered.wait(1))
                status, body, _ = request(demo)
                self.assertEqual(status, 429); self.assertEqual(body['error']['code'], 'demo_busy')
            finally:
                gate.set()
            self.assertEqual(first.result(timeout=2)[0], 200)
            self.assertEqual(len(engine.calls), 1)

    def test_no_remote_upstream_configuration(self):
        for url in ('https://example.com', 'http://example.com', 'http://127.0.0.1:8765/path', 'http://user:pass@127.0.0.1:8765'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                DemoServer(0, api_url=url)
        for timeout in (float('nan'), 0, 61):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                DemoServer(0, api_timeout=timeout)


if __name__ == '__main__':
    unittest.main()

"""Serve the Mini Jev browser demo on loopback; never load or simulate a model."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import socket
import threading
import time
import urllib.error

from service import Client
from service.client import APIError
from service.schema import Limits, ValidationError, decode_json, validate_request

ASSETS = Path(__file__).with_name('static')
LIMITS = Limits(max_body_bytes=65536, max_questions=3, max_text_chars=8192,
                max_key_chars=64, max_depth=16)
QUESTION_TYPES = {'routing': 'choice', 'urgent': 'noul', 'priority': 'score'}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
       "img-src 'self'; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")


class DemoServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port=8766, *, api_url='http://127.0.0.1:8765', api_timeout=35.):
        # Validate the upstream origin with the existing SDK, without contacting it.
        with Client(api_url, timeout=api_timeout):
            pass
        if not math.isfinite(api_timeout) or not 0 < api_timeout <= 60:
            raise ValueError('API timeout must be between 0 and 60 seconds')
        self.api_url, self.api_timeout = api_url.rstrip('/'), api_timeout
        self.inference_lock = threading.Lock()
        self.connection_slots = threading.BoundedSemaphore(8)
        super().__init__(('127.0.0.1', port), Handler)

    def process_request(self, request, client_address):
        if not self.connection_slots.acquire(blocking=False):
            # Bound the number of idle connections before starting another thread.
            try:
                request.settimeout(.2)
                request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n')
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.connection_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.connection_slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = 'MiniJevDemo/1'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(5.)
        # Also bound a connection whose header/body bytes arrive very slowly.
        self.deadline_timer = threading.Timer(self.server.api_timeout + 12., self._expire)
        self.deadline_timer.daemon = True
        self.deadline_timer.start()

    def _expire(self):
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def finish(self):
        self.deadline_timer.cancel()
        try:
            super().finish()
        except OSError:
            pass

    def log_message(self, *_):
        # Do not log prompt text, request bodies, or URL query strings.
        pass

    def _send(self, status, body, content_type='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.close_connection = True
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', CSP)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            pass

    def _error(self, status, code, message):
        self._send(status, {'error': {'code': code, 'message': message}})

    def send_error(self, code, message=None, explain=None):
        self._error(code, 'http_error', 'Unsupported or malformed HTTP request.')

    def _trusted(self, *, api=False, mutation=False):
        hosts = self.headers.get_all('Host', [])
        expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        if len(hosts) != 1 or hosts[0].lower() not in expected:
            self._error(403, 'invalid_host', 'Use this demo through its local URL and port.')
            return False
        origins = self.headers.get_all('Origin', [])
        if len(origins) > 1 or (origins and origins != ['http://' + hosts[0].lower()]):
            self._error(403, 'invalid_origin', 'Only this demo page may access this endpoint.')
            return False
        if mutation and not origins:
            self._error(403, 'missing_origin', 'A same-origin browser request is required.')
            return False
        if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
            self._error(403, 'cross_site', 'Cross-site requests are not allowed.')
            return False
        if api and self.headers.get_all('X-Mini-Jev-Demo', []) != ['1']:
            self._error(403, 'missing_demo_header', 'Use the controls on the demo page.')
            return False
        return True

    def do_GET(self):
        is_health = self.path == '/api/health'
        if not self._trusted(api=is_health):
            return
        if is_health:
            try:
                with Client(self.server.api_url, timeout=min(3., self.server.api_timeout)) as client:
                    health = client.health()
                self._send(200, {'ready': health['ready'], 'model': health['model'],
                                 'max_input_tokens': health.get('max_input_tokens'),
                                 'request_timeout_ms': int((self.server.api_timeout + 8.) * 1000),
                                 'api_url': self.server.api_url})
            except (APIError, ValidationError, OSError, urllib.error.URLError, ValueError):
                self._send(503, {'ready': False, 'error': {'code': 'api_unavailable',
                    'message': 'Model API is unavailable. Start ./run.sh --without-calibration in another terminal, then check again.'}})
            return
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path not in files:
            self._error(404, 'not_found', 'Unknown demo route.')
            return
        name, mime = files[self.path]
        self._send(200, (ASSETS / name).read_bytes(), mime)

    def _body(self):
        if self.headers.get_all('Transfer-Encoding') or self.headers.get_all('Content-Encoding'):
            self._error(400, 'unsupported_encoding', 'Send a plain JSON request with Content-Length.')
            return None
        lengths = self.headers.get_all('Content-Length', [])
        if not lengths:
            self._error(411, 'length_required', 'Content-Length is required.')
            return None
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            self._error(400, 'invalid_length', 'Content-Length must be one nonnegative integer.')
            return None
        if len(lengths[0]) > 8 or int(lengths[0]) > LIMITS.max_body_bytes:
            self._error(413, 'body_too_large', 'Keep the JSON request under 64 KiB.')
            return None
        if (len(self.headers.get_all('Content-Type', [])) != 1
                or self.headers.get_content_type() != 'application/json'):
            self._error(415, 'json_required', 'Content-Type must be application/json.')
            return None
        remaining, chunks, deadline = int(lengths[0]), [], time.monotonic() + 5.
        try:
            while remaining:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise TimeoutError()
                self.connection.settimeout(left)
                chunk = self.rfile.read1(min(remaining, 16384))
                if not chunk:
                    self._error(400, 'incomplete_body', 'Request body ended before Content-Length.')
                    return None
                chunks.append(chunk)
                remaining -= len(chunk)
        except OSError:
            self._error(408, 'body_timeout', 'Request body did not arrive within five seconds.')
            return None
        self.connection.settimeout(5.)
        return b''.join(chunks)

    def do_POST(self):
        if not self._trusted(api=True, mutation=True):
            return
        if self.path != '/api/decide':
            self._error(404, 'not_found', 'Unknown demo route.')
            return
        raw = self._body()
        if raw is None:
            return
        try:
            payload = decode_json(raw)
            validate_request(payload, LIMITS)
            if {key: question['type'] for key, question in payload['questions'].items()} != QUESTION_TYPES:
                raise ValidationError('Provide routing (Choice), urgent (Noul), and priority (Score) questions.')
        except ValidationError as error:
            self._error(422, 'invalid_input', str(error))
            return
        if not self.server.inference_lock.acquire(blocking=False):
            self._error(429, 'demo_busy', 'Another demo request is running. Wait for it to finish, then try again.')
            return
        try:
            started = time.perf_counter()
            with Client(self.server.api_url, timeout=self.server.api_timeout, limits=LIMITS) as client:
                result = client.system_one(payload['state'], payload['questions'], model=payload.get('model'))
            elapsed_ms = (time.perf_counter() - started) * 1000
            response = asdict(result)
            # Dataclass defaults are not fields supplied by the API. Preserve
            # the validated API schema when optional metadata was absent.
            response['answers'] = {key: {field: value for field, value in answer.items() if value is not None}
                                   for key, answer in response['answers'].items()}
            self._send(200, {'response': response, 'elapsed_ms': elapsed_ms, 'source': 'live_api'})
        except APIError as error:
            self._error(error.status if 400 <= error.status <= 599 else 502, 'model_api_' + error.code, str(error))
        except ValidationError:
            self._error(502, 'invalid_api_response', 'The model API returned a response that failed SDK validation.')
        except (TimeoutError, socket.timeout):
            self._error(504, 'api_timeout', 'The model API timed out. It may still be finishing its request; wait before trying again.')
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                self._error(504, 'api_timeout', 'The model API timed out. Wait before trying again.')
            else:
                self._error(503, 'api_unavailable', 'Cannot reach the model API. Start it in another terminal and check the connection.')
        except OSError:
            self._error(503, 'api_unavailable', 'Cannot reach the model API. Start it in another terminal and check the connection.')
        finally:
            self.server.inference_lock.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--api-url', default='http://127.0.0.1:8765')
    parser.add_argument('--api-timeout', type=float, default=35.)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('port must be between 1 and 65535')
    try:
        server = DemoServer(args.port, api_url=args.api_url, api_timeout=args.api_timeout)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f'Mini Jev demo: http://127.0.0.1:{server.server_port}/', flush=True)
    print('Live API only. Start the model service separately; Ctrl+C stops this UI.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()

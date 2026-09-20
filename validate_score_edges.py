#!/usr/bin/env python3
"""Four public Score boundary checks; run real inference only after the main test.

--self-test exercises the production Python adapter with an in-memory helper mock.
Normal mode loads final configuration/calibration with run_native_service.load_config
and performs exactly four single requests, without warmup or generation. This is a
narrow branch audit, not an accuracy benchmark. No acceptance dataset is read.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import string
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

PACKAGE = Path(__file__).resolve().parent
OUTPUTS = PACKAGE.parent
WORKSPACE = OUTPUTS.parent
sys.path.insert(0, str(PACKAGE))

from native_engine import NativeEngine, options_for
from run_native_service import load_config


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def file_record(path):
    if path is None:
        return None
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def fixtures():
    """Literal stage extraction; targets deliberately cover 9, 10, and 25."""
    return [
        {
            'id': f'public.score_{size}', 'expected_label': str(size - 1),
            'question': {
                'type': 'score',
                'state': f'登録済みの評価段階は {size - 1} です。',
                'instructions': '登録済みの評価段階を、そのまま対応する段階として選んでください。',
                'criteria': [f'評価段階 {i}' for i in range(size)],
            },
        }
        for size in (2, 10, 11, 26)
    ]


class Audit:
    def __init__(self, stream):
        self.stream = stream
        self.checks = []
        self.cases = []

    def event(self, event_type, **data):
        self.stream.write(json.dumps({'event': event_type, **data}, ensure_ascii=False, allow_nan=False) + '\n')
        self.stream.flush()

    def check(self, name, passed, **details):
        value = {'name': name, 'passed': bool(passed), **details}
        self.checks.append(value)
        self.event('check', **value)

    def summary(self):
        failures = [item for item in self.checks if not item['passed']]
        return {
            'passed': not failures,
            'checks_passed': len(self.checks) - len(failures),
            'checks_failed': len(failures),
            'checks': self.checks,
            'cases': self.cases,
        }


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def run_cases(engine, audit):
    """Observe real requests without changing their content or number of writes."""
    audit.check('selected_prompt_style', engine.prompt_style == 'repeat_typed_score',
                actual=engine.prompt_style)
    if engine.prompt_style != 'repeat_typed_score':
        return
    before_all = engine.total_decode_count
    audit.check('fresh_engine_counter', before_all == 0, actual=before_all)
    original_write = engine._write
    written = []

    def observed_write(request, deadline):
        # JSON-copy for immutable evidence; forward the original request unchanged.
        written.append(json.loads(json.dumps(request, ensure_ascii=False, allow_nan=False)))
        audit.event('native_request', request=written[-1])
        return original_write(request, deadline)

    engine._write = observed_write
    try:
        for fixture in fixtures():
            name, q = fixture['id'], fixture['question']
            size = len(q['criteria'])
            keys = [str(i) for i in range(size)]
            expected_candidates = keys if size <= 10 else list(string.ascii_uppercase[:size])
            expected_prefix = '{"answer":' if size <= 10 else ''
            expected_kind = 'number' if size <= 10 else 'string'
            spec = engine._candidate_spec(q, options_for(q))
            audit.check(name + '.candidate_spec', spec == (expected_candidates, expected_prefix, expected_kind),
                        candidates=spec[0], assistant_prefix=spec[1], value_kind=spec[2])
            before_count, before_writes = engine.total_decode_count, len(written)
            audit.event('public_fixture', **fixture)
            result = engine.decide(q)
            audit.event('decision', id=name, result=result)
            writes = written[before_writes:]
            audit.check(name + '.one_request', len(writes) == 1, actual=len(writes))
            request = writes[0] if len(writes) == 1 else {}
            audit.check(name + '.wire_candidates', request.get('candidates') == expected_candidates)
            audit.check(name + '.wire_prefix', request.get('assistant_prefix', '') == expected_prefix)
            audit.check(name + '.wire_messages', request.get('messages') == engine._messages(q, options_for(q)))
            audit.check(name + '.wire_limit', request.get('max_input_tokens') == engine.max_input_tokens)
            audit.check(name + '.type', result.get('type') == 'score')
            audit.check(name + '.gold', result.get('label') == fixture['expected_label'],
                        expected=fixture['expected_label'], actual=result.get('label'))
            audit.check(name + '.candidate_keys', result.get('candidate_keys') == keys)
            probabilities = result.get('probabilities', {})
            audit.check(name + '.probability_keys', isinstance(probabilities, dict) and list(probabilities) == keys)
            values = [probabilities.get(k) for k in keys] if isinstance(probabilities, dict) else []
            valid_probabilities = len(values) == size and all(finite_number(p) and 0 <= p <= 1 for p in values)
            audit.check(name + '.finite_probabilities', valid_probabilities)
            probability_sum = math.fsum(values) if valid_probabilities else None
            audit.check(name + '.probability_sum', probability_sum is not None and abs(probability_sum - 1.0) <= 1e-12,
                        actual=probability_sum)
            expected_score = math.fsum(i * p for i, p in enumerate(values)) if valid_probabilities else None
            score = result.get('score')
            score_valid = finite_number(score) and 0 <= score <= size - 1
            audit.check(name + '.score_range', score_valid)
            audit.check(name + '.score_expectation', score_valid and expected_score is not None
                        and math.isclose(score, expected_score, rel_tol=1e-12, abs_tol=1e-12),
                        expected=expected_score, actual=score)
            audit.check(name + '.legend', result.get('legend') == dict(zip(keys, q['criteria'])))
            ids = result.get('candidate_ids')
            audit.check(name + '.candidate_ids', isinstance(ids, list) and len(ids) == size
                        and all(type(i) is int and 0 <= i < engine.info['vocab_size'] for i in ids)
                        and len(set(ids)) == size)
            logits = result.get('candidate_logits')
            audit.check(name + '.finite_logits', isinstance(logits, list) and len(logits) == size
                        and all(finite_number(v) for v in logits))
            audit.check(name + '.one_decode', type(result.get('native_decode_count')) is int
                        and result['native_decode_count'] == 1)
            audit.check(name + '.total_decode_counter', result.get('native_total_decode_count') == before_count + 1
                        and engine.total_decode_count == before_count + 1)
            audit.check(name + '.zero_generation', type(result.get('output_tokens')) is int
                        and result['output_tokens'] == 0)
            audit.check(name + '.single_sequential', result.get('batch_size') == 1
                        and result.get('batch_strategy') == 'sequential_independent_requests')
            audit.check(name + '.probability_semantics',
                        result.get('probability_semantics') == 'conditional_on_allowed_label_tokens')
            audit.cases.append({
                'id': name, 'candidate_count': size, 'expected_label': fixture['expected_label'],
                'label': result.get('label'), 'candidate_tokens': expected_candidates,
                'assistant_prefix': expected_prefix, 'value_kind': expected_kind,
                'candidate_ids': ids, 'score': score, 'expected_score_from_probabilities': expected_score,
                'probability_sum': probability_sum, 'input_tokens': result.get('input_tokens'),
                'native_decode_count': result.get('native_decode_count'), 'output_tokens': result.get('output_tokens'),
            })
    finally:
        engine._write = original_write
    audit.check('exactly_four_requests', len(written) == 4, actual=len(written))
    audit.check('exactly_four_decodes', engine.total_decode_count - before_all == 4,
                actual=engine.total_decode_count - before_all)
    audit.check('score_10_to_11_fallback', len(written) == 4
                and written[1]['candidates'] == [str(i) for i in range(10)]
                and written[1].get('assistant_prefix') == '{"answer":'
                and written[2]['candidates'] == list(string.ascii_uppercase[:11])
                and 'assistant_prefix' not in written[2])


def mock_engine(*, wrong_label=False):
    """Use actual Python validation/projection; never construct/load a model."""
    engine = NativeEngine.__new__(NativeEngine)
    engine.prompt_style = 'repeat_typed_score'
    engine.max_input_tokens = 2048
    engine._ready = True
    engine.process = SimpleNamespace(poll=lambda: None)
    engine._lock = threading.RLock()
    engine._assert_artifacts_unchanged = lambda: None
    engine.sequence = 0
    engine.total_decode_count = 0
    engine.temperature = 1.0
    engine.temperature_calibration_applied = False
    engine.info = {'vocab_size': 248320}
    request_box = {}

    def write(request, deadline):
        request_box['value'] = request

    def read(timeout):
        request = request_box['value']
        count = len(request['candidates'])
        target = 0 if wrong_label else count - 1
        return {
            'id': request['id'], 'candidate_ids': list(range(100, 100 + count)),
            'logits': [5.0 if i == target else -1.0 for i in range(count)],
            'input_tokens': 200, 'output_tokens': 0, 'decode_count': 1,
            'total_decode_count': engine.total_decode_count + 1,
            'decode_count_semantics': 'llama_decode_API_calls', 'model_ms': 1.0, 'latency_ms': 2.0,
            'projection': 'full_vocab_then_candidate_gather', 'state_cleared': True,
            'template_applied': True, 'thinking_enabled': False,
        }

    engine._write, engine._read = write, read
    return engine


def self_test():
    success = Audit(io.StringIO())
    run_cases(mock_engine(), success)
    assert success.summary()['passed'], success.summary()
    failure = Audit(io.StringIO())
    run_cases(mock_engine(wrong_label=True), failure)
    failed = [c['name'] for c in failure.checks if not c['passed']]
    assert failed == [f'public.score_{n}.gold' for n in (2, 10, 11, 26)], failed
    return {'passed': True, 'mode': 'CPU mock only; no model constructor or helper process',
            'fixtures': 4, 'positive_checks': len(success.checks), 'wrong_label_checks_detected': len(failed)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=PACKAGE / 'native_config.json')
    parser.add_argument('--out-dir', type=Path, help='Required new directory; existing directories are never overwritten')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return 0
    if args.out_dir is None:
        parser.error('--out-dir is required for a real-model run')
    out_dir = args.out_dir.expanduser().resolve()
    try:
        out_dir.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        parser.error(str(exc))

    report = {
        'schema_version': 1, 'started_at_utc': utc_now(), 'mode': 'real_model',
        'fixture_source': 'four public literals for Score 2/10/11/26 boundaries; no acceptance data',
        'scope': 'single stage extraction and API/branch consistency; not a benchmark',
        'planned_requests': 4, 'planned_decode_calls': 4, 'batch_strategy': 'sequential_independent_requests',
        'script': file_record(__file__),
    }
    engine = None
    with (out_dir / 'raw.jsonl').open('w', encoding='utf-8') as stream:
        audit = Audit(stream)
        try:
            report['config'] = file_record(args.config)
            kwargs = load_config(args.config)
            report['resolved_kwargs'] = dict(kwargs)
            report['calibration_file'] = file_record(kwargs.get('temperature_config'))
            report['model_manifest'] = file_record(kwargs.get('model_manifest'))
            report['native_manifest'] = file_record(kwargs.get('native_manifest'))
            # Change diagnostics destination only; all inference settings are final config.
            kwargs['log_file'] = str(out_dir / 'native.stderr.log')
            report['diagnostics_log_override'] = kwargs['log_file']
            engine = NativeEngine(**kwargs)
            report.update(runtime_fingerprint=engine.runtime_fingerprint,
                          engine_info=engine.info, temperature=engine.temperature,
                          temperature_calibration_applied=engine.temperature_calibration_applied)
            run_cases(engine, audit)
            report['observed_total_decode_count'] = engine.total_decode_count
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
            audit.check('unhandled_runtime_error', False, error=report['error'])
            (out_dir / 'error.txt').write_text(traceback.format_exc(), encoding='utf-8')
        finally:
            if engine is not None:
                try:
                    engine.close()
                except Exception as exc:
                    audit.check('engine_close', False, error=f'{type(exc).__name__}: {exc}')
        report.update(audit.summary())
        report['finished_at_utc'] = utc_now()
    (out_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'checks_passed': report['checks_passed'],
                      'checks_failed': report['checks_failed'], 'out_dir': str(out_dir)}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

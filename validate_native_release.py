#!/usr/bin/env python3
"""Audit a native release with public fixtures; run --self-test without a model."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import select
import selectors
import string
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent


def public_fixtures():
    def choice(name, size, target, long=False):
        criteria = {f'item_{i:02d}': f'項目{i:02d}' for i in reversed(range(size))}
        state = f'指定された項目名は「項目{target:02d}」です。'
        if long:
            state = '\n'.join(f'参考記録{i:02d}: この記録の確認は完了しています。' for i in range(20)) + '\n' + state
        return {'name': name, 'expected_label': f'item_{target:02d}', 'question': {
            'type': 'choice', 'state': state, 'instructions': '指定された項目名と完全に一致する選択肢を選んでください。',
            'criteria': criteria}}
    fixtures = [choice('choice_2', 2, 1), choice('choice_8', 8, 4),
                choice('choice_26', 26, 17), choice('choice_long_8', 8, 5, True)]
    for enabled in (False, True):
        fixtures.append({'name': 'noul_' + str(enabled).lower(), 'expected_label': str(enabled).lower(),
            'question': {'type': 'noul', 'state': {'有効フラグ': enabled},
                'instructions': '有効フラグはtrueですか。', 'criteria': {'false': 'いいえ', 'true': 'はい'}}})
    for size, target in ((2, 1), (8, 6)):
        fixtures.append({'name': f'score_{size}', 'expected_label': str(target), 'question': {
            'type': 'score', 'state': {'確定した段階番号': target},
            'instructions': '記載された確定段階番号に一致する段階を選んでください。',
            'criteria': [f'段階{i}' for i in range(size)]}})
    return fixtures


def options_reference(question):
    if question['type'] == 'choice':
        return sorted(question['criteria'].items())
    if question['type'] == 'noul':
        return [(key, question.get('criteria', {'false': 'いいえ', 'true': 'はい'})[key]) for key in ('false', 'true')]
    return [(str(i), value) for i, value in enumerate(question['criteria'])]


def helper_request(engine, question, options_for, request_id):
    """Share candidate/prefix selection with the engine under audit."""
    options = options_for(question)
    style = engine.prompt_style
    known = {'compact', 'with_keys', 'structured', 'json', 'json_keys', 'json_strict',
             'repeat', 'state_last', 'reread', 'native_labels', 'repeat_labels', 'repeat_typed_score'}
    if style not in known:
        raise ValueError(f'audit needs an explicit request mapping for style {style!r}')
    candidates, prefix, _ = engine._candidate_spec(question, options)
    request = {'id': request_id, 'messages': engine._messages(question, options),
               'candidates': candidates, 'max_input_tokens': engine.max_input_tokens}
    if prefix:
        request['assistant_prefix'] = prefix
    return request


class Audit:
    def __init__(self, folder):
        self.folder = folder
        self.checks = []
        self.raw = (folder / 'raw.jsonl').open('x', encoding='utf-8')

    def event(self, kind, **data):
        self.raw.write(json.dumps({'event': kind, **data}, ensure_ascii=False, allow_nan=False, default=str) + '\n')
        self.raw.flush()

    def check(self, name, passed, **details):
        item = {'name': name, 'passed': bool(passed), **details}
        self.checks.append(item)
        return bool(passed)

    def require(self, name, passed, **details):
        if not self.check(name, passed, **details):
            raise AssertionError(name)


def check_answer(audit, name, question, answer, expected_label):
    keys = [key for key, _ in options_reference(question)]
    probabilities = answer.get('probabilities', {})
    audit.check(name + '.gold', answer.get('label') == expected_label,
                expected=expected_label, actual=answer.get('label'))
    audit.check(name + '.keys', answer.get('candidate_keys') == keys and list(probabilities) == keys)
    valid_probs = (list(probabilities) == keys and
                   all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in probabilities.values()))
    audit.check(name + '.probabilities', valid_probs and abs(math.fsum(probabilities.values()) - 1) <= 1e-12)
    audit.check(name + '.zero_generation', answer.get('output_tokens') == 0)
    audit.check(name + '.one_decode', answer.get('native_decode_count') == 1)
    audit.check(name + '.sequential_batch', answer.get('batch_strategy') == 'sequential_independent_requests')
    if question['type'] == 'score':
        score = answer.get('score')
        audit.check(name + '.score_range', type(score) in (int, float) and math.isfinite(score) and 0 <= score <= len(keys) - 1)
        if valid_probs and type(score) in (int, float):
            expected = math.fsum(i * probabilities[str(i)] for i in range(len(keys)))
            audit.check(name + '.score_expectation', abs(score - expected) <= 1e-12)
    if question['type'] == 'noul':
        audit.check(name + '.noul_probability', answer.get('noul') == probabilities.get('true'))


def same_decision(audit, name, left, right):
    fields = ('label', 'candidate_keys', 'candidate_ids', 'candidate_logits', 'probabilities', 'input_tokens')
    mismatched = [key for key in fields if left.get(key) != right.get(key)]
    audit.check(name, not mismatched, mismatched_fields=mismatched)


def engine_audit(engine, options_for, fixtures, audit):
    audit.require('configured_limit_at_most_2048', 1 <= engine.max_input_tokens <= 2048,
                  max_input_tokens=engine.max_input_tokens)
    audit.require('engine_initial_counter_zero', engine.total_decode_count == 0)
    expected_counter = 0
    singles = []
    requests = []

    def one(fixture, name):
        nonlocal expected_counter
        answer = engine.decide(fixture['question'])
        expected_counter += 1
        audit.event('engine_response', name=name, response=answer)
        check_answer(audit, name, fixture['question'], answer, fixture['expected_label'])
        audit.check(name + '.total_counter', engine.total_decode_count == expected_counter == answer['native_total_decode_count'])
        return answer

    def batch(items, name):
        nonlocal expected_counter
        before = expected_counter
        answers = engine.decide_many([f['question'] for f in items])
        expected_counter += len(items)
        audit.require(name + '.response_count', len(answers) == len(items))
        audit.check(name + '.total_counter', engine.total_decode_count == expected_counter)
        for i, (fixture, answer) in enumerate(zip(items, answers)):
            audit.event('engine_response', name=f'{name}.{i}', response=answer)
            check_answer(audit, f'{name}.{i}', fixture['question'], answer, fixture['expected_label'])
            audit.check(f'{name}.{i}.counter_sequence', answer['native_total_decode_count'] == before + i + 1)
        return answers

    for fixture in fixtures:
        singles.append(one(fixture, 'single.' + fixture['name']))
        requests.append(helper_request(engine, fixture['question'], options_for, 'full.' + fixture['name']))
    for i, answer in enumerate(batch(fixtures, 'mixed_batch_8')):
        same_decision(audit, f'single_vs_batch.{i}', singles[i], answer)
    one(fixtures[4], 'interposed_noul')
    repeated = one(fixtures[0], 'repeat_after_other_type')
    same_decision(audit, 'state_reset_repeat', singles[0], repeated)
    permuted = {**fixtures[1], 'question': {**fixtures[1]['question'],
        'criteria': dict(reversed(list(fixtures[1]['question']['criteria'].items())))}}
    reordered = one(permuted, 'choice_dictionary_reordered')
    same_decision(audit, 'choice_dictionary_normalization', singles[1], reordered)
    for i, answer in enumerate(batch(fixtures * 2, 'maximum_batch_16')):
        same_decision(audit, f'maximum_batch_consistency.{i}', singles[i % len(fixtures)], answer)

    def rejected(name, call):
        before = engine.total_decode_count
        exception = None
        try:
            call()
        except (ValueError, TypeError) as error:
            exception = {'type': type(error).__name__, 'message': str(error)}
        audit.event('engine_rejection', name=name, exception=exception,
                    counter_before=before, counter_after=engine.total_decode_count)
        audit.check(name + '.rejected', exception is not None)
        audit.require(name + '.no_decode', engine.total_decode_count == before == expected_counter)
        same_decision(audit, name + '.recovery', singles[0], one(fixtures[0], name + '.valid_after'))

    rejected('batch_17', lambda: engine.decide_many([fixtures[0]['question']] * 17))
    too_many = {**fixtures[0]['question'], 'criteria': {str(i): f'候補{i}' for i in range(27)}}
    rejected('candidate_27', lambda: engine.decide(too_many))
    rejected('invalid_later_batch_prevalidation', lambda: engine.decide_many([fixtures[0]['question'], too_many]))
    # Thousands of distinct numbered words exceed 2048 tokenizer tokens, with
    # ample margin. The actual runtime must reject, never truncate and decide.
    oversized = {**fixtures[0]['question'], 'state': ' '.join(f'audit_item_{i:04d}' for i in range(4096))}
    rejected('input_over_2048_without_truncation', lambda: engine.decide(oversized))
    audit.check('engine_final_total_counter', engine.total_decode_count == expected_counter,
                observed=engine.total_decode_count, expected=expected_counter)
    return {'single_answers': singles, 'helper_requests': requests,
            'expected_engine_decode_calls': expected_counter, 'oversized_question': oversized}


class IndependentHelper:
    """Separate bounded JSONL transport, independent of NativeEngine's parser."""
    def __init__(self, kwargs, audit, timeout):
        self.audit, self.timeout = audit, timeout
        self.stderr = (audit.folder / 'independent-helper.stderr.log').open('x', encoding='utf-8')
        self.stdout_log = (audit.folder / 'independent-helper.stdout.jsonl').open('xb')
        self.buffer = bytearray()
        self.process = subprocess.Popen([str(kwargs['native_binary']), '--model', str(kwargs['model_file']),
            '--ctx', str(kwargs.get('max_input_tokens', 2048)), '--threads', str(kwargs.get('threads', 6)),
            '--gpu-layers', '0' if kwargs.get('device', 'metal') == 'cpu' else '99'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, bufsize=0)
        os.set_blocking(self.process.stdout.fileno(), False)
        os.set_blocking(self.process.stdin.fileno(), False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)

    def read(self):
        deadline = time.monotonic() + self.timeout
        while True:
            newline = self.buffer.find(b'\n')
            if newline >= 0:
                line = bytes(self.buffer[:newline])
                del self.buffer[:newline + 1]
                if len(line) > 64 * 1024 * 1024:
                    raise ValueError('independent response exceeds 64 MiB')
                self.stdout_log.write(line + b'\n')
                self.stdout_log.flush()
                def no_duplicate(pairs):
                    value = {}
                    for key, item in pairs:
                        if key in value:
                            raise ValueError('duplicate JSON key')
                        value[key] = item
                    return value
                def no_constant(value):
                    raise ValueError('nonfinite JSON number: ' + value)
                result = json.loads(line, object_pairs_hook=no_duplicate, parse_constant=no_constant)
                if not isinstance(result, dict):
                    raise ValueError('independent helper response is not an object')
                self.audit.event('independent_response', response=result)
                return result
            if len(self.buffer) > 64 * 1024 * 1024:
                raise ValueError('independent response exceeds 64 MiB')
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not self.selector.select(remaining):
                raise TimeoutError('independent helper response deadline exceeded')
            try:
                chunk = os.read(self.process.stdout.fileno(), 65536)
            except BlockingIOError:
                continue
            if not chunk:
                raise RuntimeError('independent helper exited before a complete response')
            self.buffer.extend(chunk)

    def request(self, request):
        self.audit.event('independent_request', request=request)
        data = (json.dumps(request, ensure_ascii=False, allow_nan=False) + '\n').encode()
        deadline, offset = time.monotonic() + self.timeout, 0
        while offset < len(data):
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [self.process.stdin], [], remaining)[1]:
                raise TimeoutError('independent helper write deadline exceeded')
            try:
                n = os.write(self.process.stdin.fileno(), data[offset:])
            except BlockingIOError:
                continue
            if n <= 0:
                raise RuntimeError('independent helper input closed')
            offset += n
        return self.read()

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        if self.process.poll() is None:
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
        self.process.stdout.close()
        self.selector.close()
        self.stderr.close()
        self.stdout_log.close()


def full_vocab_reference(response, vocab_size):
    full = response['full_logits']
    if len(full) != vocab_size or any(type(x) not in (int, float) or not math.isfinite(x) for x in full):
        raise ValueError('full vocabulary logits have invalid length or values')
    ids = response['candidate_ids']
    if len(ids) != len(set(ids)) or any(type(i) is not int or not 0 <= i < vocab_size for i in ids):
        raise ValueError('candidate IDs invalid')
    reference = [full[i] for i in ids]
    peak = max(full)
    normalizer = math.fsum(math.exp(x - peak) for x in full)
    mass = math.fsum(math.exp(x - peak) for x in reference) / normalizer
    return reference, mass, max(range(vocab_size), key=full.__getitem__)


def independent_audit(kwargs, data, audit, timeout):
    helper = IndependentHelper(kwargs, audit, timeout)
    counter, measurements = 0, []
    try:
        ready = helper.read()
        audit.require('independent_ready', ready.get('ready') is True and ready.get('mode') == 'direct_logits')
        audit.require('independent_initial_counter', ready.get('total_decode_count') == 0)
        vocab_size = ready['vocab_size']
        audit.require('independent_vocab_size', type(vocab_size) is int and vocab_size >= 26)
        for index, original in enumerate(data['helper_requests']):
            request = {**original, 'debug_full_logits': True}
            response = helper.request(request)
            counter += 1
            audit.require(request['id'] + '.no_error', 'error' not in response, error=response.get('error'))
            audit.check(request['id'] + '.response_id', response.get('id') == request['id'])
            reference, mass, top_id = full_vocab_reference(response, vocab_size)
            audit.check(request['id'] + '.candidate_count', len(reference) == len(request['candidates']))
            audit.check(request['id'] + '.exact_gather', reference == response['logits'])
            audit.check(request['id'] + '.matches_engine_ids', response['candidate_ids'] == data['single_answers'][index]['candidate_ids'])
            audit.check(request['id'] + '.matches_engine_logits', response['logits'] == data['single_answers'][index]['candidate_logits'])
            audit.check(request['id'] + '.counter', response['decode_count'] == 1 and response['total_decode_count'] == counter)
            audit.check(request['id'] + '.counter_semantics', response.get('decode_count_semantics') == 'llama_decode_API_calls')
            audit.check(request['id'] + '.state_and_generation', response['output_tokens'] == 0 and
                        response['state_cleared'] is True and response['thinking_enabled'] is False and response['template_applied'] is True)
            measurements.append({'id': request['id'], 'candidate_count': len(reference), 'candidate_ids': response['candidate_ids'],
                'candidate_probability_mass_in_full_vocabulary': mass, 'unrestricted_top_token_id': top_id,
                'input_tokens': response['input_tokens'], 'decode_count': response['decode_count']})
        valid = data['helper_requests'][0]
        for name, changes in [('token_limit_zero', {'max_input_tokens': 0}),
                              ('token_limit_above_context', {'max_input_tokens': ready['ctx'] + 1}),
                              ('helper_candidate_27', {'candidates': list(string.ascii_uppercase) + ['extra']}),
                              ('helper_multitoken_candidate', {'candidates': ['A', 'not a single token']})]:
            response = helper.request({**valid, **changes, 'id': name})
            audit.require(name + '.predecode_reject', isinstance(response.get('error'), str) and
                          response.get('id') == name and response.get('decode_count') == 0 and response.get('total_decode_count') == counter)
            recovered = helper.request({**valid, 'id': name + '.recovery'})
            counter += 1
            audit.require(name + '.recovery_counter', 'error' not in recovered and
                          recovered.get('id') == name + '.recovery' and recovered.get('decode_count') == 1 and recovered.get('total_decode_count') == counter)
            audit.check(name + '.recovery_logits', recovered['logits'] == data['single_answers'][0]['candidate_logits'])
            audit.check(name + '.recovery_state_and_generation', recovered.get('output_tokens') == 0 and
                        recovered.get('state_cleared') is True and recovered.get('thinking_enabled') is False)
        return {'startup': ready, 'full_vocab_measurements': measurements, 'expected_helper_decode_calls': counter,
                'generation_tokens': 0, 'batch_strategy': 'sequential_independent_requests'}
    finally:
        helper.close()


def file_record(path):
    if path is None:
        return None
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def self_test():
    fixtures = public_fixtures()
    assert len(fixtures) == 8
    assert {len(options_reference(f['question'])) for f in fixtures} == {2, 8, 26}
    assert all(f['expected_label'] in dict(options_reference(f['question'])) for f in fixtures)
    assert all('label' not in f['question'] and 'expected_label' not in f['question'] for f in fixtures)
    from native_engine import NativeEngine, options_for
    # __new__ exposes the pure formatter without invoking verification/loading.
    formatter = NativeEngine.__new__(NativeEngine)
    formatter.max_input_tokens = 2048
    boundary_fixtures = fixtures + [{'name': f'score_boundary_{size}', 'question': {
        'type': 'score', 'state': '公開の描画検証用入力', 'instructions': '記載された段階を選ぶ。',
        'criteria': [f'段階{i}' for i in range(size)]}} for size in (10, 11, 26)]
    for style in ('repeat', 'json_keys', 'repeat_typed_score'):
        formatter.prompt_style = style
        for fixture in boundary_fixtures:
            question = fixture['question']
            count = len(options_reference(question))
            request = helper_request(formatter, question, options_for, fixture['name'])
            numeric = style == 'repeat_typed_score' and question['type'] == 'score' and count <= 10
            assert request['candidates'] == ([str(i) for i in range(count)] if numeric else list(string.ascii_uppercase[:count]))
            if numeric:
                assert request['assistant_prefix'] == '{"answer":'
            elif style == 'json_keys':
                assert request['assistant_prefix'] == '{"answer":"'
            else:
                assert 'assistant_prefix' not in request
    ref, mass, top = full_vocab_reference({'full_logits': [0., 1., 2., 3.], 'candidate_ids': [3, 1]}, 4)
    assert ref == [3., 1.] and top == 3 and 0 < mass < 1
    assert ref != [1., 3.]
    return {'self_test': 'passed', 'fixture_count': len(fixtures), 'request_styles_checked': 3,
            'formatter_cases_checked': 3 * len(boundary_fixtures), 'score_candidate_boundaries': [2, 10, 11, 26],
            'model_loads': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'native_config.json')
    parser.add_argument('--out-dir', type=Path)
    parser.add_argument('--timeout', type=float, default=180)
    parser.add_argument('--self-test', action='store_true', help='pure CPU fixture/reference checks, no config or model required')
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False))
        return 0
    if args.out_dir is None or not 0 < args.timeout <= 300:
        parser.error('--out-dir and a timeout within (0, 300] are required')
    folder = args.out_dir.resolve()
    try:
        folder.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error('out-dir already exists; choose a new directory')
    audit = Audit(folder)
    report = {'schema_version': 1, 'started_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'fixture_source': 'public literals created for runtime auditing; no acceptance datasets',
              'batch_strategy': 'sequential_independent_requests', 'checks': audit.checks,
              'validator': file_record(__file__)}
    status = 1
    try:
        from run_native_service import load_config
        from native_engine import NativeEngine, options_for
        kwargs = load_config(args.config)
        report['config'] = file_record(args.config)
        report['resolved_kwargs'] = kwargs
        report['calibration_file'] = file_record(kwargs.get('temperature_config'))
        report['model_manifest'] = file_record(kwargs.get('model_manifest'))
        report['native_manifest'] = file_record(kwargs.get('native_manifest'))
        if kwargs.get('temperature_config'):
            report['calibration'] = json.loads(Path(kwargs['temperature_config']).read_text())
        fixtures = public_fixtures()
        (folder / 'public_fixtures.json').write_text(json.dumps(fixtures, ensure_ascii=False, indent=2) + '\n')
        actual_kwargs = {**kwargs, 'log_file': str(folder / 'engine.stderr.log')}
        with NativeEngine(**actual_kwargs) as engine:
            report['runtime_fingerprint'] = engine.runtime_fingerprint
            report['engine_info'] = engine.info
            report['temperature'] = engine.temperature
            report['temperature_calibration_applied'] = engine.temperature_calibration_applied
            data = engine_audit(engine, options_for, fixtures, audit)
            report['expected_engine_decode_calls'] = data['expected_engine_decode_calls']
        # The first model process is closed before another is created.
        report['independent_helper'] = independent_audit(kwargs, data, audit, args.timeout)
        status = 0 if all(item['passed'] for item in audit.checks) else 1
    except Exception as error:
        report['fatal_error'] = {'type': type(error).__name__, 'message': str(error)}
        (folder / 'failure.traceback.txt').write_text(traceback.format_exc())
    finally:
        audit.raw.close()
        report['passed'] = status == 0
        report['checks_passed'] = sum(item['passed'] for item in audit.checks)
        report['checks_failed'] = sum(not item['passed'] for item in audit.checks)
        report['finished_at_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        (folder / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + '\n')
    print(json.dumps({'passed': report['passed'], 'checks_passed': report['checks_passed'],
                      'checks_failed': report['checks_failed'], 'report': str(folder / 'report.json'),
                      'fatal_error': report.get('fatal_error')}, ensure_ascii=False))
    return status


if __name__ == '__main__':
    raise SystemExit(main())

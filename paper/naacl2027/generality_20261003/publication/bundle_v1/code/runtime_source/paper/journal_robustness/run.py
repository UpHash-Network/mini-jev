#!/usr/bin/env python3
"""Frozen, text-free audit of prompt perturbations through a verified native model.

prepare never calls a model. run reconstructs and verifies every frozen request
before inference. Source benchmark text remains in the external questions cache.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from native_engine import NativeEngine, MODEL_PIN
from paper.journal_robustness.conditions import variants, verify_source, SEED, EXPECTED_REQUEST_COUNT


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def source_hashes(questions):
    files = {'runner': Path(__file__), 'conditions': HERE/'conditions.py',
             'protocol': HERE/'PROTOCOL.json', 'analyzer': HERE/'analyze.py',
             'native_engine': ROOT/'native_engine.py',
             'model_pin': ROOT/'native_model.json',
             'source_selection': ROOT/'paper/external_expanded/SELECTION.json',
             'source_protocol': ROOT/'paper/external_expanded/PROTOCOL.json',
             'questions': questions}
    return {key: sha(path.read_bytes()) for key, path in files.items()}


def build_schedule(questions):
    if questions.resolve().is_relative_to(ROOT):
        raise ValueError('External dataset text must remain outside the source repository')
    rows = verify_source(questions)
    rows = sorted(rows, key=lambda row: row['id'])
    rng = random.Random(SEED)
    rng.shuffle(rows)
    schedule, requests = [], []
    for row in rows:
        conditions = variants(row)
        rng.shuffle(conditions)
        for condition in conditions:
            request = condition['request']
            keys = condition['candidate_keys']
            if len(keys) != len(set(keys)) or len(keys) != len(request['candidates']):
                raise ValueError('Invalid canonical candidate mapping')
            meta = {'request_index': len(schedule), 'item_id': row['id'],
                    'dataset': row['dataset'], 'type': row['type'], 'group': row['group'],
                    'split': row['split'], 'condition': condition['condition'],
                    'candidate_keys': keys, 'candidate_tokens': request['candidates'],
                    'request_sha256': sha(canonical(request).encode()),
                    'source_question_sha256': sha(canonical({key: row[key] for key in
                        ('type', 'state', 'instructions', 'criteria')}).encode())}
            if row['type'] == 'score':
                meta.update(gold_score=row['gold_score'], score_values={key: float(key) for key in keys})
            else:
                meta['gold_label'] = row['label']
            schedule.append(meta)
            requests.append(request)
    if len(schedule) != EXPECTED_REQUEST_COUNT:
        raise ValueError('Unexpected total number of requests')
    return schedule, requests


def prepare(args):
    schedule, _ = build_schedule(args.questions)
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {'schema_version': 1, 'stage': 'before_model_inference', 'created_at': now(),
                'study': 'Mini Jev journal extension: fixed prompt robustness panel',
                'seed': SEED, 'n_items': len({row['item_id'] for row in schedule}),
                'n_measured_requests': len(schedule),
                'condition_counts': dict(Counter(row['condition'] for row in schedule)),
                'dataset_counts': dict(Counter(row['dataset'] for row in schedule)),
                'schedule_sha256': sha(canonical(schedule).encode()),
                'source_sha256': source_hashes(args.questions), 'model_pin': MODEL_PIN,
                'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'registration': 'Locally frozen and timestamped; not independent public preregistration.',
                'source_text_in_public_records': False,
                'warmup': 'Three synthetic non-benchmark requests, one per type, recorded and excluded.'}
    write_new(args.output/'SCHEDULE.json', schedule)
    write_new(args.output/'FREEZE.json', manifest)
    print(canonical({'prepared': len(schedule), 'items': manifest['n_items'],
                     'freeze_sha256': sha((args.output/'FREEZE.json').read_bytes())}), flush=True)


class ResearchEngine(NativeEngine):
    """Send prebuilt research prompts, retaining the production integrity checks."""
    def evaluate_request(self, template, keys, kind):
        self._assert_artifacts_unchanged()
        if not self.ready:
            raise RuntimeError('Native engine unavailable')
        self.sequence += 1
        request = dict(template, id=self.sequence)
        before = self.total_decode_count
        start = time.perf_counter()
        deadline = time.monotonic() + self.RESPONSE_TIMEOUT
        self._write(request, deadline)
        answer = self._read(timeout=deadline-time.monotonic())
        self._assert_artifacts_unchanged()
        logits = self._validate_answer(answer, before, len(keys))
        peak = max(logits)
        weights = [math.exp(value-peak) for value in logits]
        total = math.fsum(weights)
        values = [value/total for value in weights]
        probabilities = dict(zip(keys, values))
        # Tie breaking follows the candidate vector order, explicitly retained.
        label = keys[max(range(len(keys)), key=values.__getitem__)]
        typed_value = (label if kind == 'choice' else probabilities['true'] if kind == 'noul'
                       else math.fsum(float(key)*value for key, value in probabilities.items()))
        return {'logits': logits, 'probabilities': probabilities, 'label': label,
                'exact_top_logit_tie_keys': [key for key, value in zip(keys, logits) if value == peak],
                'typed_value': typed_value, 'temperature': 1.0,
                'concentration': 1+math.fsum(p*math.log(p) for p in values if p > 0)/math.log(len(keys)),
                'candidate_ids': answer['candidate_ids'], 'input_tokens': answer['input_tokens'],
                'output_tokens': answer['output_tokens'], 'native_decode_count': answer['decode_count'],
                'native_total_decode_count': answer['total_decode_count'],
                'model_ms': answer['model_ms'], 'latency_ms': (time.perf_counter()-start)*1000,
                'state_cleared': answer['state_cleared'], 'thinking_enabled': answer['thinking_enabled'],
                'projection': answer['projection'], 'error': None}


WARMUPS = [
    {'type': 'choice', 'state': 'これは事務用品の分類を確認する動作試験です。鉛筆を選びます。',
     'instructions': '本文に書かれた品物を選んでください。',
     'criteria': {'pencil': '鉛筆', 'ruler': '定規'}},
    {'type': 'noul', 'state': 'この文章には三つの単語があります。',
     'instructions': '文章に「単語」という表現は含まれていますか。',
     'criteria': {'false': '含まれていない。', 'true': '含まれている。'}},
    {'type': 'score', 'state': '明示された優先段階は1です。',
     'instructions': '本文に明示された優先段階を選んでください。',
     'criteria': ['段階0', '段階1', '段階2']},
]


def run(args):
    freeze = json.loads((args.output/'FREEZE.json').read_text())
    if freeze['source_sha256'] != source_hashes(args.questions):
        raise ValueError('Source changed after freeze; create a new documented preparation')
    schedule, requests = build_schedule(args.questions)
    if freeze['schedule_sha256'] != sha(canonical(schedule).encode()):
        raise ValueError('Reconstructed schedule differs from freeze')
    if schedule != json.loads((args.output/'SCHEDULE.json').read_text()):
        raise ValueError('Stored schedule differs from reconstructed requests')
    results = args.output/'results'
    results.mkdir(exist_ok=False)
    started = now()
    write_new(results/'ATTEMPT.json', {'started_at': started, 'expected_requests': len(schedule),
              'status': 'started_not_completed', 'freeze_sha256': sha((args.output/'FREEZE.json').read_bytes())})
    completed, errors, fatal = 0, 0, None
    engine = None
    try:
        print(canonical({'status': 'verifying_model_and_loading_native_runtime'}), flush=True)
        engine = ResearchEngine(args.model, args.native_binary, log_file=args.log,
                                prompt_style='repeat_typed_score', temperature=1.0, threads=6)
        write_new(results/'RUNTIME.json', {'verified_at': now(), 'fingerprint': engine.runtime_fingerprint,
                  'fingerprint_data': engine.fingerprint_data, 'native_ready': engine.info,
                  'interpretation': 'One verified model and device. Runtime latency is descriptive, not the primary estimand.'})
        if source_hashes(args.questions) != freeze['source_sha256']:
            raise ValueError('Study source changed during model startup')
        with (results/'warmup.jsonl').open('x') as out:
            for index, q in enumerate(WARMUPS):
                answer = engine.decide(q)
                out.write(canonical({'index': index, 'synthetic_question': q, 'answer': answer})+'\n')
                out.flush()
        began = time.perf_counter()
        with (results/'predictions.jsonl').open('x') as out:
            for meta, request in zip(schedule, requests):
                if sha(canonical(request).encode()) != meta['request_sha256']:
                    raise ValueError('Request mutated in memory')
                row = dict(meta)
                try:
                    row.update(engine.evaluate_request(request, meta['candidate_keys'], meta['type']))
                except Exception as error:
                    row.update(error=type(error).__name__+': '+str(error))
                    errors += 1
                out.write(canonical(row)+'\n')
                out.flush()
                completed += 1
                if completed % 100 == 0 or completed == len(schedule):
                    print(canonical({'completed': completed, 'total': len(schedule), 'errors': errors,
                        'elapsed_s': round(time.perf_counter()-began, 1)}), flush=True)
                    if source_hashes(args.questions) != freeze['source_sha256']:
                        raise ValueError('Frozen source changed during measurement')
                if row.get('error') and not engine.ready:
                    raise RuntimeError('Native protocol failure; preserving partial attempt without retries')
    except BaseException as error:
        fatal = type(error).__name__+': '+str(error)
        raise
    finally:
        if engine is not None:
            total_decodes = engine.total_decode_count
            engine.close()
        else:
            total_decodes = None
        files = {p.name: sha(p.read_bytes()) for p in results.glob('*.json*') if p.is_file()}
        write_new(results/'COMPLETION.json', {'status': 'completed' if completed == len(schedule) and not fatal else 'incomplete',
                  'started_at': started, 'finished_at': now(), 'expected_requests': len(schedule),
                  'recorded_requests': completed, 'failed_requests': errors, 'fatal_error': fatal,
                  'native_total_decode_count_including_warmup': total_decodes,
                  'file_sha256': files, 'source_unchanged': source_hashes(args.questions) == freeze['source_sha256'],
                  'failure_policy': 'All attempted requests retained; no replacements or automatic retries.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('--questions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--native-binary', type=Path)
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    if args.action == 'run' and not all([args.model, args.native_binary, args.log]):
        parser.error('run requires --model, --native-binary, and --log outside the repository')
    if args.log and args.log.resolve().is_relative_to(ROOT):
        parser.error('Native log must stay outside the source repository')
    (prepare if args.action == 'prepare' else run)(args)


if __name__ == '__main__':
    main()

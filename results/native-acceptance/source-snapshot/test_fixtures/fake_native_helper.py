#!/usr/bin/env python3
"""Protocol fixture only: never imports a model library or runs GPU work."""
import argparse
import json
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True)
parser.add_argument('--ctx', type=int, default=2048)
parser.add_argument('--gpu-layers', type=int, default=0)
parser.add_argument('--threads', type=int, default=1)
args = parser.parse_args()
config = json.loads(Path(args.model).read_text())
mode = config.get('mode', 'normal')

def emit(value):
    print(json.dumps(value), flush=True)

if mode == 'partial_startup':
    sys.stdout.write('{"ready":'); sys.stdout.flush(); time.sleep(5); sys.exit()
startup = {'ready': True, 'mode': 'direct_logits', 'ctx': args.ctx, 'vocab_size': 1024,
           'gpu_layers': args.gpu_layers, 'batch_strategy': 'sequential_independent_requests',
           'total_decode_count': 0}
startup.update(config.get('startup_overrides', {}))
emit(startup)
total = 0
requests = 0
for line in sys.stdin:
    request = json.loads(line)
    requests += 1
    with open(args.model + '.requests', 'a') as out:
        out.write(json.dumps(request) + '\n')
    if mode == 'partial_response':
        sys.stdout.write('{"id":'); sys.stdout.flush(); time.sleep(5); continue
    if mode == 'oversize':
        sys.stdout.write('x' * (2 * 1024 * 1024)); sys.stdout.flush(); continue
    if mode == 'invalid_json':
        print('{malformed', flush=True); continue
    if mode == 'duplicate_json':
        print('{"id":1,"id":1}', flush=True); continue
    if mode == 'eof':
        sys.exit()
    if mode in ('input_error_once', 'decode_error_once') and requests == 1:
        decodes = int(mode == 'decode_error_once')
        total += decodes
        emit({'id': request['id'], 'error': 'deliberate fixture error',
              'decode_count': decodes, 'total_decode_count': total})
        continue
    if mode == 'bad_error_counter':
        emit({'id': request['id'], 'error': 'bad fixture counter', 'decode_count': 0,
              'total_decode_count': 77})
        continue
    count = len(request['candidates'])
    total += 1
    answer = {'id': request['id'], 'candidate_ids': list(range(65, 65 + count)),
              'logits': [float(i) for i in range(count)], 'input_tokens': 50, 'output_tokens': 0,
              'decode_count': 1, 'total_decode_count': total,
              'decode_count_semantics': 'llama_decode_API_calls', 'model_ms': 1.0, 'latency_ms': 2.0,
              'projection': 'full_vocab_then_candidate_gather', 'state_cleared': True,
              'template_applied': True, 'thinking_enabled': False}
    answer.update(config.get('response_overrides', {}))
    emit(answer)

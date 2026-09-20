"""Export the frozen question bank without changing questions or answer keys."""
import collections
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUTS = [
    ('manual', 'private/acceptance_test.jsonl', '58f5d36e278462d2e48d5ff38c3f97b7df6370ea865389e7f3e016eb6ac7aff6'),
    ('generated', 'private/generated_2220.jsonl', '791bd3f43c1f6e01b960ff961c50aacf83da64a23fa7b8292378c529c76a04d9'),
]


def main():
    cases = []
    for source, name, expected in INPUTS:
        data = (ROOT / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected, 'frozen source changed'
        for line in data.splitlines():
            if line:
                question = {**json.loads(line), 'source': source}
                question.setdefault('family', question.get('tag', question['type']))
                cases.append(question)
    assert len(cases) == len({q['id'] for q in cases}) == 2400
    assert collections.Counter(q['type'] for q in cases) == {'choice': 800, 'noul': 800, 'score': 800}
    jsonl = ''.join(json.dumps(q, ensure_ascii=False, allow_nan=False) + '\n' for q in cases).encode('utf-8')
    stream = io.StringIO(newline='')
    columns = ['id', 'type', 'source', 'family', 'state', 'instructions', 'criteria', 'label']
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for q in cases:
        writer.writerow({k: json.dumps(q[k], ensure_ascii=False, allow_nan=False)
                         if k in {'state', 'criteria', 'label'} else q.get(k, '') for k in columns})
    csv_data = stream.getvalue().encode('utf-8-sig')
    decoded = list(csv.DictReader(io.StringIO(csv_data.decode('utf-8-sig'))))
    for actual, expected in zip(decoded, cases):
        assert all(json.loads(actual[k]) == expected[k] for k in ('state', 'criteria', 'label'))
    hashes = {}
    for name, content in [('questions_2400.jsonl', jsonl), ('questions_2400.csv', csv_data)]:
        path = ROOT / name
        if path.exists() and path.read_bytes() != content:
            raise ValueError('refuse to overwrite a different export')
        path.write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    manifest = {'count': len(cases), 'by_type': dict(collections.Counter(q['type'] for q in cases)),
                'by_source': dict(collections.Counter(q['source'] for q in cases)), 'sha256': hashes,
                'calibration_excluded': True, 'csv_roundtrip_verified': True}
    (ROOT / 'EXPORT_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()

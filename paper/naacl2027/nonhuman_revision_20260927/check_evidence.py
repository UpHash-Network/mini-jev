#!/usr/bin/env python3
"""Read-only, standard-library checks of the NAACL evidence entry points.

No download, extraction, inference, pip installation, or human-study analysis.
For full numerical replay, use the separate frozen bundle's reanalyze.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ARCHIVE_SHA256 = 'a15e0699a54be15d56bd99ed8181429b71fdfc7ace756d6e065a75538786c053'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(root):
    paper = root / 'paper' / 'naacl2027'
    archive = paper / 'reproducibility' / 'naacl-repro-v1-20260925.zip'
    require(digest(archive.read_bytes()) == ARCHIVE_SHA256, 'Frozen ZIP hash differs')
    receipt = json.loads((paper / 'reproducibility' / 'VALIDATION.20260925.json').read_text())
    counts = {}
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        require(len(names) == len(set(names)), 'Duplicate ZIP members')
        require(bundle.testzip() is None, 'ZIP CRC failure')
        manifest = json.loads(bundle.read('mini-jev/BUNDLE_MANIFEST.json'))
        expected_names = {'mini-jev/' + record['path'] for record in manifest['files']}
        expected_names.add('mini-jev/BUNDLE_MANIFEST.json')
        require(set(names) == expected_names, 'Unexpected or missing ZIP member')
        for record in manifest['files']:
            data = bundle.read('mini-jev/' + record['path'])
            require(len(data) == record['bytes'] and digest(data) == record['sha256'],
                    'Manifest mismatch: ' + record['path'])
        for record in receipt['prediction_files']:
            data = bundle.read('mini-jev/' + record['path'])
            require(digest(data) == record['sha256'], 'Prediction hash differs: ' + record['path'])
            rows = [json.loads(line) for line in data.decode().splitlines() if line.strip()]
            require(len(rows) == record['measured_rows'], 'Prediction row count differs')
            counts[record['path']] = {'rows': len(rows), 'role': record['role']}
    measured = sum(v['rows'] for v in counts.values() if v['role'] == 'naacl_study')
    background = sum(v['rows'] for v in counts.values() if v['role'] != 'naacl_study')
    require(measured == 26050 and background == 300, 'Study/background accounting differs')

    lmql_path = paper / 'comparator_study' / 'run_v1' / 'results.jsonl'
    lmql = [json.loads(line) for line in lmql_path.read_text().splitlines() if line.strip()]
    require(len(lmql) == 12 and len({r['case_id'] for r in lmql}) == 12, 'LMQL case set differs')
    failed = [r['case_id'] for r in lmql if not r['within_prespecified_tolerance']]
    require(set(failed) == {'score-01', 'score-03', 'score-04'}, 'LMQL failure set differs')
    require(all(r['argmax_matches'] for r in lmql), 'LMQL recorded argmax mismatch')

    cf_path = paper / 'chainforge_integration' / 'results.json'
    cf = json.loads(cf_path.read_text())
    cf_answer_count = 0
    for row in cf['records']:
        direct, integrated = row['direct_sdk']['answers'], row['chainforge']['answers']
        require(direct == integrated, 'ChainForge typed answers differ: ' + row['id'])
        require(row['direct_sdk']['usage'] == row['chainforge']['usage'], 'ChainForge usage differs')
        require(row['direct_sdk']['model'] == row['chainforge']['model'], 'ChainForge model differs')
        cf_answer_count += len(direct)
    require(len(cf['records']) == 4 and cf_answer_count == 8, 'ChainForge pair accounting differs')
    require(len(cf['negative_checks']) == 3 and all(r['rejected'] for r in cf['negative_checks']),
            'ChainForge negative-control receipt differs')
    return {
        'status': 'pass', 'scope': 'archived evidence integrity and accounting; no new inference',
        'archive_sha256': ARCHIVE_SHA256, 'verified_manifest_files': len(manifest['files']),
        'archive_members': len(names), 'main_measured_request_rows': measured,
        'background_rows_excluded': background, 'prediction_files': counts,
        'lmql': {'cases': len(lmql), 'recorded_argmax_matches': sum(r['argmax_matches'] for r in lmql),
                 'retained_prespecified_tolerance_failures': failed, 'raw_log_sha256': digest(lmql_path.read_bytes()),
                 'note': 'Case-level recalculation is in lmql_diagnostic/analyze.py; parity failures remain failures.'},
        'chainforge': {'request_pairs': len(cf['records']), 'rechecked_exact_typed_answer_pairs': cf_answer_count,
                      'recorded_invalid_input_rejections': len(cf['negative_checks']),
                      'raw_log_sha256': digest(cf_path.read_bytes())},
        'model_calls': 0, 'human_participants': 0, 'reanalysis_reexecuted': False,
        'limitations': ['Integrity checks do not prove the validity of original measurements.',
                        'Historical numerical replay and same-Mac installation are separate receipts.',
                        'No human usability, external replication, or competing GUI performance is measured.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=HERE.parents[2], help='Repository root')
    parser.add_argument('--output', type=Path, help='Optional new JSON report path')
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('Output exists; choose a new file to preserve earlier checks.')
    try:
        result = check(args.root.resolve())
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        result = {'status': 'fail', 'error': str(error), 'model_calls': 0}
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end='')
    return int(result['status'] != 'pass')


if __name__ == '__main__':
    sys.exit(main())

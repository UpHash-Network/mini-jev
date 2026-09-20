#!/usr/bin/env python3
"""Static public-release checks. Reports metadata only, never matched secrets.

This is a release hygiene check, not a security audit or model evaluation. Run
from any directory: python scripts/check_public_release.py --root PATH.
It never loads a model, invokes a native executable, or accesses the network.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

IGNORED_DIRECTORIES = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', '.build', '.runs', '.cache', 'models'}
SECRET_PATTERNS = (
    re.compile(rb'\bsk-[A-Za-z0-9_-]{20,}'),
    re.compile(rb'\bgh[pousr]_[A-Za-z0-9_]{20,}'),
    re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{20,}'),
    re.compile(rb'\bAKIA[A-Z0-9]{16}\b'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    re.compile(rb'(?i)(?:auth_token|api_secret|client_secret)\s*[=:]\s*[\x22\x27]?[A-Za-z0-9_/-]{32,}'),
)
PRIVATE_PATH = re.compile(rb'/(?:Users|home)/[A-Za-z0-9_.-]+(?:/|\\)')
PRIVATE_WINDOWS_PATH = re.compile(rb'[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+[\\/]')
WORK_DEPENDENCY = re.compile(r'(?:\.\./){2,}work(?:/|["\x27])')


def scan_tree(root: Path, *, require_project: bool = True) -> dict:
    """Return JSON-serializable metadata. Never include matched input content."""
    root = root.resolve()
    findings = []
    scanned = 0
    scanned_bytes = 0

    def add(code, relative, severity='error', **metadata):
        findings.append({'code': code, 'path': relative, 'severity': severity, **metadata})

    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRECTORIES for part in relative.parts):
            continue
        name = relative.as_posix()
        if path.is_symlink():
            resolved = path.resolve()
            if not resolved.is_relative_to(root) or not resolved.exists():
                add('unsafe_symlink', name)
            continue
        if not path.is_file():
            continue
        scanned += 1
        size = path.stat().st_size
        scanned_bytes += size
        if size > 50 * 1024 * 1024:
            add('large_file', name, bytes=size)
        if path.suffix.lower() == '.gguf':
            add('model_weights_in_source_release', name)
        if path.name == '.env' or path.name.startswith('.env.') and path.name not in {'.env.example', '.env.sample', '.env.template'}:
            add('environment_file', name)
        # Read every byte, including binary strings; never print matching values.
        data = path.read_bytes()
        for index, pattern in enumerate(SECRET_PATTERNS):
            count = len(pattern.findall(data))
            if count:
                add('credential_pattern', name, rule=index, matches=count)
        private_count = len(PRIVATE_PATH.findall(data)) + len(PRIVATE_WINDOWS_PATH.findall(data))
        if private_count:
            add('private_user_path', name, matches=private_count, binary=b'\0' in data[:8192])
        if path.suffix in {'.py', '.sh', '.json'} and 'results' not in relative.parts:
            # Historical snapshots can retain relative paths; active entrypoints cannot
            # rely on the development workspace outside the repository.
            try:
                content = data.decode('utf-8')
            except UnicodeDecodeError:
                content = ''
            if WORK_DEPENDENCY.search(content):
                add('external_development_workspace', name)

    if require_project:
        for filename in ('README.md', 'LICENSE', 'native_model.json'):
            if not (root / filename).is_file():
                add('missing_release_file', filename)
        if not any((root / name).is_file() for name in ('THIRD_PARTY_NOTICES.md', 'NOTICE', 'NOTICE.md')):
            add('missing_release_file', 'THIRD_PARTY_NOTICES.md or NOTICE')
        config_path = root / 'native_config.json'
        try:
            config = json.loads(config_path.read_text(encoding='utf-8'))
            for key in ('model_file', 'model_manifest', 'native_binary', 'native_manifest', 'log_file'):
                value = config.get(key)
                if not isinstance(value, str) or not value:
                    add('invalid_config_path', 'native_config.json', field=key)
                elif Path(value).is_absolute() or '..' in Path(value).parts:
                    add('nonportable_config_path', 'native_config.json', field=key)
        except (OSError, ValueError, TypeError):
            add('invalid_native_config', 'native_config.json')
        jsonl = root / 'acceptance-v2/questions_2400.jsonl'
        csv_path = root / 'acceptance-v2/questions_2400.csv'
        try:
            records = [json.loads(line) for line in jsonl.read_text(encoding='utf-8').splitlines() if line.strip()]
            counts = Counter(row['type'] for row in records)
            if len(records) < 2000 or set(counts) != {'choice', 'noul', 'score'}:
                add('incomplete_question_bank', jsonl.relative_to(root).as_posix(), records=len(records), types=dict(counts))
            ids = [row['id'] for row in records]
            if len(ids) != len(set(ids)):
                add('duplicate_question_ids', jsonl.relative_to(root).as_posix())
            with csv_path.open(encoding='utf-8-sig', newline='') as stream:
                exported = list(csv.DictReader(stream))
            if len(exported) != len(records) or [row['id'] for row in exported] != ids:
                add('csv_jsonl_question_mismatch', csv_path.relative_to(root).as_posix())
        except (OSError, ValueError, KeyError, TypeError):
            add('invalid_question_bank', 'acceptance-v2')
        # Source-only distributions deliberately omit native/bin and rebuild it.
        # Attribution/source files must still be present in either layout.
        for filename in ('LICENSE-helper.txt', 'LICENSE-llama-cpp.txt', 'licenses/LICENSE-jsonhpp',
                         'licenses/cpp-httplib-LICENSE', 'licenses/sha256-LICENSE',
                         'licenses/xxhash-LICENSE', 'licenses/rotate-bits-LICENSE.md',
                         'licenses/LICENSE-Qwen3.6-Apache-2.0.txt'):
            if not (root / 'native' / filename).is_file():
                add('missing_native_attribution', 'native/' + filename)

    return {
        'schema_version': 1,
        'passed': not any(item['severity'] == 'error' for item in findings),
        'files_scanned': scanned,
        'bytes_scanned': scanned_bytes,
        'findings': findings,
        'scope': 'Static release hygiene only. Not a comprehensive secret detector, legal review, or model-quality test.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--files-only', action='store_true', help='Do not require the MiniJev project structure')
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error('root must be an existing directory')
    report = scan_tree(args.root, require_project=not args.files_only)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Reconstruct external question text from the already frozen public index."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import prepare


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    cache = args.cache_dir.expanduser().resolve()
    command = ['verify', '--cache-dir', str(cache)]
    try:
        # Verifies source bytes, frozen protocol/script identity, and derived
        # selection/audit before checking the optional local question file.
        prepare.main(command)
        return
    except FileNotFoundError as error:
        if Path(error.filename).resolve() != cache / 'questions.jsonl':
            raise
    protocol = json.loads((prepare.HERE / 'PROTOCOL.json').read_text())
    questions, selection, audit = prepare.derive(protocol, cache)
    if selection != json.loads((prepare.HERE / 'SELECTION.json').read_text()):
        raise ValueError('derived selection differs from frozen public index')
    if audit != json.loads((prepare.HERE / 'AUDIT.json').read_text()):
        raise ValueError('derived audit differs from frozen record')
    with (cache / 'questions.jsonl').open('xb') as stream:
        stream.write(questions)
    prepare.main(command)


if __name__ == '__main__':
    main()

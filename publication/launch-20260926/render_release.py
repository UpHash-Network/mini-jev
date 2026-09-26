#!/usr/bin/env python3
"""Render reviewed launch copy offline; this program never posts anything."""
import argparse
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
PLACEHOLDER = '{{ARXIV_URL}}'
PUBLIC_PATH = re.compile(r'/abs/\d{2}(?:0[1-9]|1[0-2])\.\d{5}(?:v[1-9]\d*)?\Z')
URL = re.compile(r'https://[^\s]+')


def validate_arxiv_url(value):
    """Validate public-abstract URL shape; cannot verify publication offline."""
    parts = urlsplit(value)
    if (parts.scheme != 'https' or parts.netloc != 'arxiv.org'
            or parts.query or parts.fragment or not PUBLIC_PATH.fullmatch(parts.path)):
        raise ValueError('Use the public https://arxiv.org/abs/YYMM.NNNNN URL; submission IDs, preview URLs, credentials, and query strings are rejected.')
    return value


def weighted_length(value):
    """X v3 weights for this emoji-free copy, with each HTTPS URL costing 23.

    This intentionally is not a general twitter-text replacement. No emojis,
    bare-domain links, or punctuation adjoining URLs occur in this package.
    Draft weights were independently checked with official twitter-text 3.1.0.
    """
    value = unicodedata.normalize('NFC', value)
    value = URL.sub('x' * 23, value)
    return sum(1 if (0 <= ord(c) <= 4351 or 8192 <= ord(c) <= 8205
                         or 8208 <= ord(c) <= 8223 or 8242 <= ord(c) <= 8247)
               else 2 for c in value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('now', 'announced'), required=True)
    parser.add_argument('--arxiv-url')
    parser.add_argument('--public-page-checked', action='store_true',
                        help='Operator confirms the public abstract page opens and matches the title/author. No network check is performed by this program.')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.stage == 'announced':
        if not args.arxiv_url or not args.public_page_checked:
            parser.error('announced requires --arxiv-url and --public-page-checked after checking the public page.')
        try:
            validate_arxiv_url(args.arxiv_url)
        except ValueError as error:
            parser.error(str(error))
    elif args.arxiv_url or args.public_page_checked:
        parser.error('The now stage does not use an arXiv publication URL.')
    if args.output_dir.exists():
        parser.error('Output directory already exists; choose a new directory to preserve the previous release copy.')
    posts = json.loads((HERE / 'x-posts.json').read_text())[args.stage]
    prepared = {}
    counts = []
    for language, package in posts.items():
        texts = [('single', package['single'])] + [(f'thread-{i:02}', item) for i, item in enumerate(package['thread'], 1)]
        for label, text in texts:
            if args.arxiv_url:
                text = text.replace(PLACEHOLDER, args.arxiv_url)
            if '{{' in text or '}}' in text:
                parser.error(f'Unresolved placeholder: {language}/{label}')
            count = weighted_length(text)
            if count > 280:
                parser.error(f'{language}/{label} exceeds 280 weighted characters ({count}).')
            path = f'x-{language}-{label}.txt'
            prepared[path] = text + '\n'
            counts.append({'file': path, 'weighted_length': count})
    reddit = (HERE / 'reddit-machinelearning-update.md').read_text()
    if args.stage == 'announced':
        reddit += f'\nPreprint (not peer reviewed): {args.arxiv_url}\n'
    prepared['reddit-machinelearning-update.md'] = reddit
    prepared['manifest.json'] = json.dumps({
        'stage': args.stage,
        'arxiv_url': args.arxiv_url,
        'network_requests_performed': False,
        'public_page_check': 'operator-attested' if args.public_page_checked else 'not_applicable',
        'external_posting_performed': False,
        'reddit_prepared_for': 'Single substantive update replying to the existing comment in the official Self-Promotion Thread; check current thread/account state before posting.',
        'reddit_parent_comment': 'https://www.reddit.com/r/MachineLearning/comments/1w4xaes/comment/pawz0ha/',
        'reddit_rule_check': 'REDDIT_RULES.ja.md (2026-09-26)',
        'reddit_moderator_acceptance_guaranteed': False,
        'x_posts': counts,
        'note': 'Single post and thread are alternatives; do not publish both versions as duplicate announcements.'
    }, ensure_ascii=False, indent=2) + '\n'
    args.output_dir.mkdir(parents=True)
    for name, text in prepared.items():
        (args.output_dir / name).write_text(text)
    print(json.dumps({'output_dir': str(args.output_dir), 'x_posts': len(counts), 'max_weighted_length': max(item['weighted_length'] for item in counts), 'reddit_draft': 'reddit-machinelearning-update.md'}))


if __name__ == '__main__':
    main()

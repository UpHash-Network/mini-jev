#!/usr/bin/env python3
"""Prepare fixed external pilot questions without inference; raw text stays outside Git."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def sha_object(value):
    return sha(canonical(value).encode())


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('invalid text field: ' + name)
    value.encode('utf-8')


def source_id(row, specification):
    return str(row[specification['id_field']])


def rank(row, specification, salt):
    identity = specification['dataset'] + ':' + specification['split'] + ':' + source_id(row, specification)
    return sha((salt + identity).encode())


def select(rows, specification, salt):
    ids = [source_id(row, specification) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate official IDs in source')
    if len(rows) < specification['sample_n']:
        raise ValueError('insufficient rows for fixed sample')
    return sorted(rows, key=lambda row: (rank(row, specification, salt), source_id(row, specification)))[:specification['sample_n']]


def caption_images(caption):
    pieces = caption.split('-')
    if len(pieces) != 3 or not all(pieces):
        raise ValueError('unexpected yjcaptions_id format')
    images = pieces[0].split('_')
    if any(not image.isdigit() for image in images):
        raise ValueError('unexpected image identifier')
    return images


def convert(row, specification, prompt):
    dataset = specification['dataset']
    identifier = dataset.lower() + ':' + specification['split'] + ':' + source_id(row, specification)
    result = {'id': identifier, 'source': 'external', 'dataset': dataset, 'split': specification['split'],
              'type': prompt['type'], 'instructions': prompt['instructions']}
    if dataset == 'JCoLA':
        text(row['sentence'], 'sentence'); text(row['source'], 'source')
        if type(row['label']) is not int or row['label'] not in (0, 1):
            raise ValueError('invalid binary gold')
        result.update(state=prompt['state_template'].format(sentence=row['sentence']),
                      criteria=prompt['criteria'], label='true' if row['label'] else 'false',
                      group='jcola-source:' + sha(row['source'].encode()))
    elif dataset == 'JSTS':
        for key in ('sentence1', 'sentence2'): text(row[key], key)
        gold = row['label']
        if type(gold) not in (int, float) or not math.isfinite(gold) or not 0 <= gold <= 5:
            raise ValueError('invalid continuous similarity gold')
        result.update(state=prompt['state_template'].format(**row), criteria=prompt['criteria'],
                      gold_score=float(gold), group=None)
    elif dataset == 'JCommonsenseQA':
        text(row['question'], 'question')
        if type(row['label']) is not int or row['label'] not in range(5):
            raise ValueError('invalid QA gold')
        for index in range(5): text(row['choice' + str(index)], 'choice')
        result.update(state=prompt['state_template'].format(**row),
                      criteria={'option_' + str(index): row['choice' + str(index)] for index in range(5)},
                      label='option_' + str(row['label']), group='jcqa-question:' + sha(row['question'].encode()))
    else:
        raise ValueError('unsupported dataset')
    return result


def source_texts(row, dataset):
    if dataset in ('JSTS', 'JNLI'):
        return [row['sentence1'], row['sentence2']]
    if dataset == 'JCoLA':
        return [row['sentence']]
    return [row['question']]


def reference(row, specification, question, salt):
    dataset = specification['dataset']
    record = {'id': question['id'], 'dataset': dataset, 'split': specification['split'],
              'original_id': source_id(row, specification), 'type': question['type'],
              'row_sha256': sha_object(row), 'question_sha256': sha_object(question),
              'sampling_rank_sha256': rank(row, specification, salt), 'group': question['group'],
              'text_sha256': [sha(value.encode()) for value in source_texts(row, dataset)]}
    if dataset == 'JSTS':
        record.update(gold_score=question['gold_score'], yjcaptions_id=row['yjcaptions_id'],
                      image_ids=caption_images(row['yjcaptions_id']), sentence_pair_sha256=sha_object([row['sentence1'], row['sentence2']]))
    else:
        record['label'] = question['label']
        if dataset == 'JCoLA':
            record['bibliographic_source_sha256'] = sha(row['source'].encode())
    return record


def overlap(rows, dataset):
    occurrences = Counter()
    owners = defaultdict(set)
    for index, row in enumerate(rows):
        values = source_texts(row, dataset)
        occurrences.update(sha(value.encode()) for value in values)
        for value in values:
            owners[sha(value.encode())].add(index)
    report = {'rows': len(rows), 'distinct_exact_texts': len(occurrences),
              'repeated_text_values_across_rows': sum(len(ids) > 1 for ids in owners.values()),
              'rows_sharing_text_with_another_row': len(set().union(*(ids for ids in owners.values() if len(ids) > 1))) if owners else 0,
              'text_occurrences_beyond_first': sum(n - 1 for n in occurrences.values())}
    if dataset in ('JSTS', 'JNLI'):
        captions = Counter(row['yjcaptions_id'] for row in rows)
        images = Counter(image for row in rows for image in set(caption_images(row['yjcaptions_id'])))
        report.update(distinct_ordered_sentence_pairs=len({sha_object([row['sentence1'], row['sentence2']]) for row in rows}),
                      distinct_caption_pair_ids=len(captions), distinct_source_images=len(images),
                      rows_sharing_source_image=sum(any(images[image] > 1 for image in caption_images(row['yjcaptions_id'])) for row in rows))
    if dataset == 'JCoLA':
        report['bibliographic_source_groups'] = dict(sorted(Counter(sha(row['source'].encode()) for row in rows).items()))
    return report


def caption_components(jsts, jnli):
    entries = [('JSTS:' + str(row['sentence_pair_id']), row) for row in jsts]
    entries += [('JNLI:' + str(row['sentence_pair_id']), row) for row in jnli]
    parents = {key: key for key, _ in entries}
    def find(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key
    def join(a, b):
        ra, rb = find(a), find(b)
        parents[max(ra, rb)] = min(ra, rb)
    owners = {}
    for key, row in entries:
        tokens = ['text:' + sha(value.encode()) for value in source_texts(row, 'JSTS')]
        tokens += ['image:' + image for image in caption_images(row['yjcaptions_id'])]
        for token in tokens:
            if token in owners: join(key, owners[token])
            else: owners[token] = key
    groups = {key: 'caption-component:' + sha(find(key).encode()) for key, _ in entries}
    counts = Counter(groups.values())
    return groups, {'components': len(counts), 'max_component_rows': max(counts.values()),
                    'rows_in_non_singleton_components': sum(n for n in counts.values() if n > 1)}


def cross_overlap(jsts, jnli):
    target_texts = {sha(value.encode()) for row in jnli for value in source_texts(row, 'JNLI')}
    target_pairs = {sha_object([row['sentence1'], row['sentence2']]) for row in jnli}
    target_captions = {row['yjcaptions_id'] for row in jnli}
    target_images = {image for row in jnli for image in caption_images(row['yjcaptions_id'])}
    return {'jsts_rows': len(jsts), 'prior_jnli_rows': len(jnli),
            'jsts_rows_with_any_exact_sentence_in_prior_jnli': sum(any(sha(value.encode()) in target_texts for value in source_texts(row, 'JSTS')) for row in jsts),
            'jsts_rows_with_same_ordered_sentence_pair': sum(sha_object([row['sentence1'], row['sentence2']]) in target_pairs for row in jsts),
            'jsts_rows_with_same_caption_pair_id': sum(row['yjcaptions_id'] in target_captions for row in jsts),
            'jsts_rows_sharing_any_source_image': sum(any(image in target_images for image in caption_images(row['yjcaptions_id'])) for row in jsts),
            'note': 'Overlaps are reported without exclusion or reselection. The two tasks are not independent external data sources.'}


def fetch_verified(cache, specification):
    path = cache / 'raw' / specification['file']
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(path.suffix + '.partial')
        subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', specification['url'], '-o', str(temporary)], check=True)
        if len(temporary.read_bytes()) != specification['bytes'] or sha(temporary.read_bytes()) != specification['sha256']:
            raise ValueError('download integrity failure: ' + specification['file'])
        temporary.replace(path)
    if path.is_symlink() or len(path.read_bytes()) != specification['bytes'] or sha(path.read_bytes()) != specification['sha256']:
        raise ValueError('source integrity mismatch: ' + specification['file'])
    return path


def derive(protocol, cache):
    salt = protocol['sampling']['salt']
    source_summaries, chosen, source_rows = {}, [], {}
    for specification in protocol['sources']:
        raw = (cache / 'raw' / specification['file']).read_bytes()
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        selected = select(rows, specification, salt)
        source_rows[specification['file']] = selected
        summary = {'available_count': len(rows), 'selected_count': len(selected),
                   'selected_overlap': overlap(selected, specification['dataset'])}
        if specification['dataset'] == 'JSTS':
            scores = [float(row['label']) for row in selected]
            summary['selected_continuous_gold'] = {'min': min(scores), 'max': max(scores), 'mean': math.fsum(scores) / len(scores),
                                                   'noninteger_count': sum(not score.is_integer() for score in scores)}
        else:
            summary.update(available_label_counts=dict(sorted(Counter(str(row['label']) for row in rows).items())),
                           selected_label_counts=dict(sorted(Counter(str(row['label']) for row in selected).items())))
        source_summaries[specification['file']] = summary
        for row in selected:
            chosen.append((specification, row, convert(row, specification, protocol['prompts'][specification['dataset']])))
    pilot = json.loads((ROOT / protocol['overlap_reference']['selection']).read_text())
    pilot_ids = {row['sentence_pair_id']: row for row in pilot['items']}
    full_jnli = [json.loads(line) for line in (cache / 'raw' / protocol['overlap_reference']['file']).read_bytes().splitlines() if line.strip()]
    jnli = [row for row in full_jnli if str(row['sentence_pair_id']) in pilot_ids]
    if len(jnli) != len(pilot_ids): raise ValueError('prior JNLI IDs missing')
    for row in jnli:
        if sha_object(row) != pilot_ids[str(row['sentence_pair_id'])]['row_sha256']:
            raise ValueError('prior JNLI row hash mismatch')
    jsts = source_rows['jsts-valid.json']
    components, component_summary = caption_components(jsts, jnli)
    for specification, row, question in chosen:
        if specification['dataset'] == 'JSTS':
            question['group'] = components['JSTS:' + str(row['sentence_pair_id'])]
    chosen.sort(key=lambda item: (rank(item[1], item[0], salt), item[2]['id']))
    questions = [question for _, _, question in chosen]
    references = [reference(row, specification, question, salt) for specification, row, question in chosen]
    question_bytes = ''.join(canonical(question) + '\n' for question in questions).encode()
    audit = {'source_summaries': source_summaries, 'JSTS_vs_prior_JNLI': cross_overlap(jsts, jnli),
             'JSTS_plus_JNLI_components': component_summary,
             'JCoLA_combined': overlap(source_rows['jcola-in-valid.json'] + source_rows['jcola-out-valid.json'], 'JCoLA'),
             'question_count': len(questions), 'by_dataset': dict(Counter(q['dataset'] for q in questions)),
             'by_type': dict(Counter(q['type'] for q in questions)),
             'group_counts': {dataset: len({q['group'] for q in questions if q['dataset'] == dataset}) for dataset in protocol['prompts']},
             'raw_text_publication': 'No raw source or transformed question text is written to public metadata',
             'source_gold_to_score_preserved': True, 'JSTS_class_labels_created': False,
             'inference_calls': 0, 'selection_uses_labels': False,
             'pretraining_contamination': 'unknown', 'semantic_paraphrase_overlap': 'not fully measured'}
    selection = {'schema_version': 1, 'questions_sha256': sha(question_bytes), 'questions_bytes': len(question_bytes),
                 'count': len(questions), 'items': references}
    return question_bytes, selection, audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'verify'))
    parser.add_argument('--cache-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    cache = args.cache_dir.expanduser().resolve()
    if cache.is_relative_to(ROOT) or ROOT.is_relative_to(cache):
        parser.error('cache must be outside and must not contain the repository')
    cache.mkdir(parents=True, exist_ok=True)
    protocol_path = HERE / 'PROTOCOL.json'
    protocol = json.loads(protocol_path.read_text())
    for specification in protocol['sources'] + [protocol['overlap_reference']] + protocol['license_sources']:
        fetch_verified(cache, specification)
    freeze = {'schema_version': 1, 'protocol_sha256': sha(protocol_path.read_bytes()),
              'preparation_script_sha256': sha(Path(__file__).read_bytes()),
              'prior_JNLI_selection_sha256': sha((ROOT / protocol['overlap_reference']['selection']).read_bytes()),
              'source_sha256': {row['file']: row['sha256'] for row in protocol['sources'] + [protocol['overlap_reference']] + protocol['license_sources']},
              'selection_frozen_before_inference': True, 'inference_calls': 0,
              'note': 'Local preparation freeze after source-schema inspection but before selected-row construction and all inference; not an independently registered protocol.'}
    if args.mode == 'prepare':
        if (HERE / 'SELECTION.json').exists() or (HERE / 'AUDIT.json').exists() or (cache / 'questions.jsonl').exists():
            parser.error('preparation outputs already exist; use verify instead of overwriting')
        write_new(HERE / 'PREPARATION.json', {**freeze, 'created_at_utc': datetime.now(timezone.utc).isoformat()})
    else:
        previous = json.loads((HERE / 'PREPARATION.json').read_text())
        if any(previous.get(key) != value for key, value in freeze.items()):
            raise ValueError('preparation protocol/script/source identity changed')
    question_bytes, selection, audit = derive(protocol, cache)
    if args.mode == 'prepare':
        with (cache / 'questions.jsonl').open('xb') as stream: stream.write(question_bytes)
        write_new(HERE / 'SELECTION.json', selection)
        write_new(HERE / 'AUDIT.json', audit)
    else:
        if selection != json.loads((HERE / 'SELECTION.json').read_text()) or audit != json.loads((HERE / 'AUDIT.json').read_text()):
            raise ValueError('selection or audit mismatch')
        if (cache / 'questions.jsonl').read_bytes() != question_bytes:
            raise ValueError('transformed question file mismatch')
    print(json.dumps({'verified': True, 'count': selection['count'], 'questions_sha256': selection['questions_sha256'],
                      'questions_filename': 'questions.jsonl', 'inference_calls': 0,
                      'overlap': audit['JSTS_vs_prior_JNLI']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

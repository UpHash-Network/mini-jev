"""Synthetic CPU fixtures only; source text and model calls are not needed."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('expanded_prepare', Path(__file__).with_name('prepare.py'))
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)
PROTOCOL = json.loads(Path(__file__).with_name('PROTOCOL.json').read_text())


class PreparationTests(unittest.TestCase):
    def test_sample_is_id_hash_only_and_order_independent(self):
        specification = {'dataset': 'fixture', 'split': 'dev', 'id_field': 'uid', 'sample_n': 3}
        rows = [{'uid': index, 'label': index % 2, 'text': 'unused'} for index in range(10)]
        one = prepare.select(rows, specification, 'fixed:')
        changed = [{**row, 'label': 1 - row['label'], 'text': 'different'} for row in reversed(rows)]
        two = prepare.select(changed, specification, 'fixed:')
        self.assertEqual([row['uid'] for row in one], [row['uid'] for row in two])

    def test_duplicate_source_id_rejected(self):
        specification = {'dataset': 'fixture', 'split': 'dev', 'id_field': 'uid', 'sample_n': 1}
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            prepare.select([{'uid': 1}, {'uid': 1}], specification, 'fixed:')

    def test_score_gold_remains_continuous_without_label(self):
        specification = next(row for row in PROTOCOL['sources'] if row['dataset'] == 'JSTS')
        row = {'sentence_pair_id': 'fixture', 'sentence1': '試験文甲。', 'sentence2': '試験文乙。', 'label': 2.7}
        result = prepare.convert(row, specification, PROTOCOL['prompts']['JSTS'])
        self.assertEqual(result['gold_score'], 2.7)
        self.assertNotIn('label', result)
        self.assertEqual(len(result['criteria']), 6)
        self.assertEqual(result['type'], 'score')

    def test_noul_uses_sentence_and_excludes_annotation_markers(self):
        specification = next(row for row in PROTOCOL['sources'] if row['dataset'] == 'JCoLA')
        row = {'uid': 1, 'sentence': '合成の試験文。', 'source': 'synthetic-reference',
               'label': 0, 'diacritic': 'SECRET-ANNOTATION', 'original': 'SECRET-ORIGINAL'}
        result = prepare.convert(row, specification, PROTOCOL['prompts']['JCoLA'])
        self.assertEqual(result['label'], 'false')
        inputs = {key: result[key] for key in ('type', 'state', 'instructions', 'criteria')}
        self.assertNotIn('SECRET', json.dumps(inputs))
        self.assertNotIn('synthetic-reference', json.dumps(inputs))

    def test_qa_preserves_original_options_and_maps_index(self):
        specification = next(row for row in PROTOCOL['sources'] if row['dataset'] == 'JCommonsenseQA')
        row = {'q_id': 9, 'question': 'これは合成テストです。', 'label': 3,
               **{'choice' + str(i): '候補' + str(i) for i in range(5)}}
        result = prepare.convert(row, specification, PROTOCOL['prompts']['JCommonsenseQA'])
        self.assertEqual(result['label'], 'option_3')
        self.assertEqual(list(result['criteria']), ['option_' + str(i) for i in range(5)])
        self.assertEqual(list(result['criteria'].values()), ['候補' + str(i) for i in range(5)])

    def test_caption_image_parser(self):
        self.assertEqual(prepare.caption_images('12_34-56-78'), ['12', '34'])
        self.assertEqual(prepare.caption_images('12-56-g78'), ['12'])
        with self.assertRaises(ValueError): prepare.caption_images('invalid')

    def test_sentence_count_excludes_within_row_only_repetition(self):
        row = {'sentence1': 'A', 'sentence2': 'A', 'yjcaptions_id': '1-2-3'}
        report = prepare.overlap([row], 'JSTS')
        self.assertEqual(report['text_occurrences_beyond_first'], 1)
        self.assertEqual(report['rows_sharing_text_with_another_row'], 0)

    def test_shared_images_or_sentences_link_cross_task_components(self):
        one = {'sentence_pair_id': 'a', 'sentence1': 'A', 'sentence2': 'B', 'yjcaptions_id': '1-2-3'}
        two = {'sentence_pair_id': 'b', 'sentence1': 'C', 'sentence2': 'D', 'yjcaptions_id': '1-4-5'}
        three = {'sentence_pair_id': 'c', 'sentence1': 'D', 'sentence2': 'E', 'yjcaptions_id': '8-9-10'}
        groups, summary = prepare.caption_components([one], [two, three])
        self.assertEqual(groups['JSTS:a'], groups['JNLI:b'])
        self.assertEqual(groups['JNLI:b'], groups['JNLI:c'])
        self.assertEqual(summary['components'], 1)
        self.assertEqual(summary['max_component_rows'], 3)

    def test_invalid_source_hash_is_not_redownloaded_or_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)
            (cache / 'raw').mkdir()
            file = cache / 'raw' / 'fixture.json'
            file.write_bytes(b'wrong')
            specification = {'file': file.name, 'bytes': 5, 'sha256': '0' * 64, 'url': 'https://invalid.example/data'}
            with self.assertRaisesRegex(ValueError, 'integrity'):
                prepare.fetch_verified(cache, specification)
            self.assertEqual(file.read_bytes(), b'wrong')

    def test_public_index_has_600_ids_and_no_source_text_fields(self):
        selection = json.loads(Path(__file__).with_name('SELECTION.json').read_text())
        self.assertEqual(selection['count'], 600)
        self.assertEqual(len({row['id'] for row in selection['items']}), 600)
        for row in selection['items']:
            self.assertFalse(set(row) & {'state', 'sentence', 'sentence1', 'sentence2', 'question', 'criteria', 'original'})
            self.assertEqual(len(row['row_sha256']), 64)
            self.assertEqual(len(row['question_sha256']), 64)
            if row['dataset'] == 'JSTS':
                self.assertIn('gold_score', row)
                self.assertNotIn('label', row)


if __name__ == '__main__':
    unittest.main()

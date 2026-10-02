"""No model imports/inference: privacy transforms and portable verification controls."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import build_bundle as b
import replay as r

HERE=Path(__file__).resolve().parent

class UnitControls(unittest.TestCase):
    def test_paths_replace_nested_keys_and_values(self):
        clean=b.sanitizer(Path('/private-user/work/repo'),Path('/private-user/work'),Path('/private-user'))
        value={'/private-user/work/repo/code.py':{'v':'/private-user/work/cache','h':'/private-user/cache','s':'/system/python'}}
        public=clean(value)
        self.assertIn('{REPOSITORY}/code.py',public)
        self.assertEqual(public['{REPOSITORY}/code.py']['v'],'{WORKSPACE}/cache')
        self.assertEqual(public['{REPOSITORY}/code.py']['h'],'{HOME}/cache')
        self.assertTrue(public['{REPOSITORY}/code.py']['s'].startswith('{ABSOLUTE_PATH_SHA256}/'))
        self.assertNotIn('/private-user',json.dumps(public))

    def test_allowlist_cannot_publish_question_or_original_token_ids(self):
        private={'logits':[1.,2.],'probabilities':{'option_0':.2},'question':'PRIVATE','input_ids':[1,2],'candidate_ids':[32,33],'token_ids':[4],'api_key':'secret'}
        public={k:v for k,v in private.items() if k in b.PREDICTION_FIELDS}
        self.assertEqual(set(public),{'logits','probabilities'})

    def test_exact_structure_counts_and_labels(self):
        base={'correct':3,'selected':True,'label':'option_1','score':.25,'undefined':None,'curve':[1,2]}
        self.assertEqual(r.numeric_compare(base,base),0)
        for key,value in [('correct',3.0),('selected',1),('label','option_2'),('curve',[1,2,3]),('undefined',0)]:
            other=copy.deepcopy(base);other[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):r.numeric_compare(other,base)

    def test_float_tolerance_is_bounded_and_nan_rejected(self):
        self.assertLess(r.numeric_compare({'x':.2+1e-13},{'x':.2}),1e-12)
        for value in (.2+1e-9,float('nan'),float('inf')):
            with self.assertRaises(ValueError):r.numeric_compare({'x':value},{'x':.2})

class RealPendingBundleControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=HERE/'bundle_pending_v1'
        if not cls.bundle.exists():raise unittest.SkipTest('Build pending snapshot first for real-frozen-data integration controls')

    def test_real_bundle_integrity(self):
        manifest,protocol,schedule,pools=r.verify_bundle(self.bundle)
        self.assertEqual(protocol['n_items'],240)
        self.assertEqual(len(schedule),1200)
        self.assertEqual(manifest['original_results_sha256'],None)
        self.assertNotEqual(manifest['status'],'complete_reference_available')
        for rows in pools.values():
            self.assertEqual(len(rows),1200)
            self.assertTrue(all(set(row)<=b.PREDICTION_FIELDS for row in rows))
            self.assertFalse(any('candidate_ids' in row for row in rows))

    def test_pending_replay_refuses_to_invent_results(self):
        with self.assertRaisesRegex(ValueError,'pending'):r.replay(self.bundle)

    def test_changed_published_bytes_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='test-private-') as temp:
            destination=Path(temp)/'copy';shutil.copytree(self.bundle,destination)
            with (destination/'data/SCHEDULE.json').open('a') as stream:stream.write(' ')
            with self.assertRaisesRegex(ValueError,'Published bytes differ'):r.verify_bundle(destination)

    def test_receipt_model_closure_enforced_beyond_manifest_hash(self):
        with tempfile.TemporaryDirectory(dir=HERE,prefix='test-private-') as temp:
            destination=Path(temp)/'copy';shutil.copytree(self.bundle,destination)
            manifest=r.load(destination/'MANIFEST.json')
            complete=[key for key,state in manifest['models'].items() if state['status']=='completed']
            if not complete:self.skipTest('No completed model in pending snapshot')
            name='models/'+complete[0]+'/COMPLETION.public.json'
            receipt=r.load(destination/name);receipt['model_closed_before_receipt']=False
            (destination/name).write_text(json.dumps(receipt))
            manifest['files_sha256'][name]=r.sha((destination/name).read_bytes())
            (destination/'MANIFEST.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Unfinished/unclosed'):r.verify_bundle(destination)

if __name__=='__main__':unittest.main()

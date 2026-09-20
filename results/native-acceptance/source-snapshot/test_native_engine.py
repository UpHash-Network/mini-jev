"""Production identity/freeze tests with a small fake helper; no model/GPU."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import native_engine as native

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / 'test_fixtures'
NOUL = {'type':'noul','state':'local fixture','instructions':'is this true?'}


def bundle(folder, config=None):
    folder.mkdir(parents=True, exist_ok=True)
    model = folder/'model.gguf'
    model.write_text(json.dumps(config or {}))
    package = folder/'native'
    (package/'bin').mkdir(parents=True)
    shutil.copy2(FIXTURES/'fake_native_helper.py',package/'bin/llama-decision-helper')
    (package/'llama_decision_helper.cpp').write_text('test fixture only')
    aliases = {}
    for i in range(7):
        path=package/f'bin/libfixture{i}.1.dylib'
        path.write_bytes(f'CPU fixture {i}'.encode())
        alias=package/f'bin/libfixture{i}.dylib'
        alias.symlink_to(path.name)
        aliases[str(alias.relative_to(package))]=path.name
    files={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in package.rglob('*') if p.is_file() and not p.is_symlink()}
    manifest={'schema_version':1,'llama_cpp_commit':native.LLAMA_COMMIT,
              'files_sha256':files,'symlinks':aliases,
              'sha256':{Path(k).name:v for k,v in files.items() if k.startswith('bin/')}}
    native_manifest=package/'BUILD.json'
    native_manifest.write_text(json.dumps(manifest))
    pin={**native.MODEL_PIN,'bytes':model.stat().st_size,'sha256':hashlib.sha256(model.read_bytes()).hexdigest()}
    model_manifest=folder/'native_model.json'
    model_manifest.write_text(json.dumps({**pin,'schema_version':1,'path':None}))
    return {'model_file':model,'native_binary':package/'bin/llama-decision-helper',
            'model_manifest':model_manifest,'native_manifest':native_manifest,
            'log_file':folder/'helper.log','device':'cpu'},pin


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.folder=Path(self.temp.name)
        self.kwargs,self.pin=bundle(self.folder/'original')
        self.pin_patch=patch.dict(native.MODEL_PIN,self.pin)
        self.pin_patch.start()
        self.engines=[]

    def tearDown(self):
        for engine in self.engines:engine.close()
        self.pin_patch.stop()
        self.temp.cleanup()

    def engine(self,kwargs=None,**overrides):
        instance=native.NativeEngine(**{**(kwargs or self.kwargs),**overrides})
        self.engines.append(instance)
        return instance

    def test_real_package_inventory_without_model_load(self):
        _,files,_,aliases=native._verify_native(ROOT/'native/BUILD.json',ROOT/'native/bin/llama-decision-helper')
        self.assertGreaterEqual(len(files),21)
        self.assertEqual(len(aliases),14)

    def test_constructor_context_manager_and_repeat_prompt(self):
        with self.engine() as engine:
            result=engine.decide(NOUL)
            self.assertTrue(engine.ready)
            self.assertEqual(result['native_decode_count'],1)
            content=engine._messages(NOUL,native.options_for(NOUL))[1]['content']
            self.assertEqual(content.count('状態:\nlocal fixture'),2)
            self.assertEqual(engine.model_sha256,self.pin['sha256'])
        self.assertFalse(engine.ready)

    def test_gguf_and_library_changes_reject_before_process_launch(self):
        self.kwargs['model_file'].write_text('same wrong bytes')
        with patch.object(native.subprocess,'Popen') as spawn,self.assertRaises(ValueError):self.engine()
        spawn.assert_not_called()
        self.kwargs['model_file'].write_text('{}')
        (self.kwargs['native_manifest'].parent/'bin/libfixture0.1.dylib').write_text('changed')
        with patch.object(native.subprocess,'Popen') as spawn,self.assertRaises(ValueError):self.engine()
        spawn.assert_not_called()

    def test_fixed_model_revision_and_dtype(self):
        for overrides in ({'model':'wrong'},{'revision':'wrong'},{'dtype':'Q8_0'}):
            with self.subTest(overrides=overrides),patch.object(native.subprocess,'Popen') as spawn,self.assertRaises(ValueError):
                self.engine(**overrides)
            spawn.assert_not_called()

    def test_alias_escape_or_extra_library_rejected(self):
        package=self.kwargs['native_manifest'].parent
        alias=package/'bin/libfixture0.dylib'
        alias.unlink();alias.symlink_to('/etc/hosts')
        with self.assertRaises(ValueError):self.engine()
        alias.unlink();alias.symlink_to('libfixture0.1.dylib')
        (package/'bin/unlisted.dylib').write_bytes(b'extra')
        with self.assertRaises(ValueError):self.engine()

    def test_model_mutation_during_hash_rejected(self):
        model=self.kwargs['model_file'].resolve()
        stat=native._stat_identity
        count=0
        def changing(path):
            nonlocal count
            result=stat(path)
            if path==model:
                count+=1
                if count==2:return (*result[:-1],result[-1]+1)
            return result
        with patch.object(native,'_stat_identity',side_effect=changing),self.assertRaisesRegex(ValueError,'changed during'):
            self.engine()

    def test_running_model_library_alias_changes_fail_closed(self):
        engine=self.engine()
        self.kwargs['model_file'].write_text('altered')
        with self.assertRaisesRegex(RuntimeError,'artifact changed'):engine.decide(NOUL)
        self.assertFalse(engine.ready)
        self.assertEqual(engine.total_decode_count,0)

    def test_running_alias_changes_fail_closed(self):
        engine=self.engine()
        alias=self.kwargs['native_manifest'].parent/'bin/libfixture0.dylib'
        alias.unlink();alias.symlink_to('libfixture1.1.dylib')
        with self.assertRaisesRegex(RuntimeError,'artifact changed'):engine.decide(NOUL)
        self.assertFalse(engine.ready)

    def test_full_model_hash_runs_once_and_runtime_only_stats(self):
        original=native._sha_file
        with patch.object(native,'_sha_file',wraps=original) as hashed:
            engine=self.engine()
            engine.decide_many([NOUL,NOUL])
        model=self.kwargs['model_file'].resolve()
        self.assertEqual(sum(call.args[0]==model for call in hashed.call_args_list),1)

    def test_running_library_change_fails_closed(self):
        engine=self.engine()
        library=self.kwargs['native_manifest'].parent/'bin/libfixture0.1.dylib'
        library.write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'artifact changed'):engine.decide(NOUL)
        self.assertFalse(engine.ready)

    def test_dyld_environment_removed(self):
        spawn=subprocess.Popen
        with patch.dict(os.environ,{'DYLD_LIBRARY_PATH':'/wrong','DYLD_INSERT_LIBRARIES':'/wrong','_DYLD_TEST':'bad'}):
            with patch.object(native.subprocess,'Popen',wraps=spawn) as capture:
                engine=self.engine()
        environment=capture.call_args.kwargs['env']
        self.assertFalse(any(key.startswith(('DYLD_','_DYLD_')) for key in environment))
        self.assertTrue(engine.ready)

    def test_fingerprint_is_portable_and_temperature_independent(self):
        first=self.engine(temperature=1.0)
        first.close()
        moved=self.folder/'relocated'
        shutil.copytree(self.folder/'original',moved,symlinks=True)
        kwargs={key:(moved/value.relative_to(self.folder/'original') if isinstance(value,Path) else value)
                for key,value in self.kwargs.items()}
        second=self.engine(kwargs,temperature=2.0)
        self.assertEqual(first.runtime_fingerprint,second.runtime_fingerprint)
        serialized=json.dumps(second.fingerprint_data)
        self.assertNotIn(str(self.folder),serialized)
        self.assertNotIn('temperature',second.fingerprint_data)

    def test_runtime_settings_and_native_bytes_change_fingerprint(self):
        first=self.engine();first.close()
        for overrides in ({'threads':2},{'max_input_tokens':1024},{'prompt_style':'compact'}):
            changed=self.engine(**overrides)
            self.assertNotEqual(first.runtime_fingerprint,changed.runtime_fingerprint)
            changed.close()
        package=self.kwargs['native_manifest'].parent
        target=package/'bin/libfixture0.1.dylib';target.write_bytes(b'new valid fixture build')
        manifest=json.loads(self.kwargs['native_manifest'].read_text())
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        manifest['files_sha256']['bin/'+target.name]=digest;manifest['sha256'][target.name]=digest
        self.kwargs['native_manifest'].write_text(json.dumps(manifest))
        self.assertNotEqual(first.runtime_fingerprint,self.engine().runtime_fingerprint)

    def test_calibration_requires_fingerprint_and_preserves_it(self):
        first=self.engine();first.close()
        path=self.folder/'temperature.json'
        path.write_text(json.dumps({'runtime_fingerprint':first.runtime_fingerprint,'temperature':1.4}))
        second=self.engine(temperature_config=path)
        self.assertEqual(first.runtime_fingerprint,second.runtime_fingerprint)
        self.assertTrue(second.temperature_calibration_applied)
        self.assertEqual(second.temperature,1.4)
        second.close()
        path.write_text(json.dumps({'runtime_fingerprint':'wrong','temperature':1.4}))
        with self.assertRaisesRegex(ValueError,'fingerprint'):self.engine(temperature_config=path)


if __name__=='__main__':unittest.main(verbosity=2)

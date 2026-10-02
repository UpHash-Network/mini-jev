#!/usr/bin/env python3
"""Portable offline handoff preflight: pinned source, stdlib integrity and scorer.

No download, GPU, model service, package installation, or six-analysis replay.
Source can be a clean git archive; a new no-pip venv is created under --output.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(source,output):
    if output.exists():raise ValueError('Output exists; choose a new directory')
    output.mkdir(parents=True)
    pin=json.loads((HERE/'SOURCE_PIN.json').read_text(encoding='utf-8'))
    before={rel:digest(source/rel) for rel in pin['files_sha256']}
    if before!=pin['files_sha256']:raise ValueError('Pinned selected source files differ from commit '+pin['source_commit'])
    models=list(source.rglob('*.gguf'))
    if models:raise ValueError('This source-only preflight expects no GGUF inside the clean snapshot')
    env=dict(os.environ)
    for key in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV'):env.pop(key,None)
    env.update(PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
    commands=[]
    substitutions=[(str(output),'{OUTPUT}'),(str(source),'{SOURCE}'),(str(HERE),'{PACKET}')]
    def clean(text):
        for old,new in substitutions:text=text.replace(old,new)
        return text
    def command(name,args,expected=0,contains=None):
        start=time.monotonic()
        cp=subprocess.run([str(x) for x in args],cwd=source,env=env,text=True,encoding='utf-8',capture_output=True,timeout=120)
        text=cp.stdout+cp.stderr
        (output/(name+'.log.txt')).write_text(clean(text),encoding='utf-8')
        record={'name':name,'argv':[clean(str(x)) for x in args],'cwd':'{SOURCE}','returncode':cp.returncode,'expected_returncode':expected,'wall_seconds':time.monotonic()-start,'log':name+'.log.txt','expected_text':contains}
        record['pass']=cp.returncode==expected and (contains is None or contains in text)
        commands.append(record)
        if not record['pass']:raise ValueError(name+' failed; inspect '+name+'.log.txt')
        return cp
    result={'status':'running','scope':'Automated pinned-source and fresh-venv preflight; machine/operator relationship is unverified by this script','started_utc':datetime.now(timezone.utc).isoformat(),'source_commit':pin['source_commit'],'selected_source_sha256':before,'source_gguf_count':len(models),'commands':commands,'new_model_calls':0,'network_operations_requested':0,'network_isolation':'No network operation is invoked by the checked commands; this is not an OS-enforced network sandbox.','six_analysis_replay_executed':False,'machine_operator_relationship':'unverified; complete OPERATOR_LOG.blank.json', 'human_operator_validation':None,'environment':{'system':platform.system(),'release':platform.release(),'machine':platform.machine(),'python_launcher':sys.version,'scope':'Only the current operating system is observed in this run; other runs are not inferred'}}
    try:
        command('create_no_pip_venv',[sys.executable,'-X','utf8','-I','-B','-m','venv','--without-pip',output/'venv'])
        py=output/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        probe=command('stdlib_environment',[py,'-X','utf8','-I','-B','-c','import json,importlib.metadata,importlib.util,sys; print(json.dumps({"python":sys.version,"isolated":sys.flags.isolated,"third_party_distributions":[d.metadata["Name"] for d in importlib.metadata.distributions()],"pip_available":importlib.util.find_spec("pip") is not None}))'])
        ep=json.loads(probe.stdout)
        if ep['third_party_distributions'] or ep['pip_available']:raise ValueError('Expected no third-party packages/pip')
        result['environment']['venv']=ep
        checker=source/'paper/naacl2027/nonhuman_revision_20260927/check_evidence.py'
        command('integrity_accounting',[py,'-X','utf8','-I','-B',checker,'--output',output/'EVIDENCE_CHECKS.json'])
        ev=json.loads((output/'EVIDENCE_CHECKS.json').read_text(encoding='utf-8'))
        if ev['verified_manifest_files']!=353 or ev['main_measured_request_rows']!=26050 or ev['background_rows_excluded']!=300:raise ValueError('Unexpected evidence inventory')
        old=digest(output/'EVIDENCE_CHECKS.json')
        command('existing_receipt_rejected',[py,'-X','utf8','-I','-B',checker,'--output',output/'EVIDENCE_CHECKS.json'],expected=2,contains='Output exists')
        if digest(output/'EVIDENCE_CHECKS.json')!=old:raise ValueError('Existing receipt changed')
        info=command('model_metadata_only',[py,'-X','utf8','-I','-B',source/'fetch_native_model.py','--info'])
        meta=json.loads(info.stdout)
        if meta['bytes']!=20419565568 or meta['sha256']!='671e47e0ec53c665d048b98c3ecbfd5236b5ca9c3e02ed19fc8f81f7b85140c7':raise ValueError('Model identity differs')
        command('missing_model_rejected',[py,'-X','utf8','-I','-B',source/'fetch_native_model.py','--verify-only','--output',output/'absent.gguf'],expected=1,contains='completed model file is missing')
        bogus=output/'invalid-test-file.gguf';bogus.write_bytes(b'not-a-model')
        bh=digest(bogus)
        command('wrong_size_model_rejected',[py,'-X','utf8','-I','-B',source/'fetch_native_model.py','--verify-only','--output',bogus],expected=1,contains='size mismatch')
        if digest(bogus)!=bh or bogus.with_name(bogus.name+'.verified.json').exists():raise ValueError('Invalid model altered/accepted')
        command('native_config_no_load',[py,'-X','utf8','-B',source/'run_native_service.py','--without-calibration','--print-config'])
        config=json.loads((output/'native_config_no_load.log.txt').read_text(encoding='utf-8'))
        if config['temperature']!=1 or config['temperature_config'] is not None:raise ValueError('Expected uncalibrated T=1 configuration')
        command('independent_smoke_scorer',[py,'-X','utf8','-I','-B',HERE/'smoke_contract.py','--self-check',source,'--output',output/'SCORER_CHECK.json'])
        smoke=json.loads((output/'SCORER_CHECK.json').read_text(encoding='utf-8'))
        if len(smoke['negative_controls'])!=9 or not all(x['rejected'] for x in smoke['negative_controls']):raise ValueError('Scorer controls failed')
        after={rel:digest(source/rel) for rel in before}
        if after!=before:raise ValueError('Pinned source input changed')
        result.update(status='pass',completed_utc=datetime.now(timezone.utc).isoformat(),selected_source_files_unchanged=True,verified_manifest_files=353,main_measured_request_rows=26050,background_rows_excluded=300,negative_controls_rejected=9,model_downloaded=False,native_build_executed=False,native_inference_executed=False)
    except Exception as error:
        result.update(status='fail',error=type(error).__name__+': '+clean(str(error)),completed_utc=datetime.now(timezone.utc).isoformat())
    (output/'PREFLIGHT_RECEIPT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'receipt':str(output/'PREFLIGHT_RECEIPT.json')}))
    return result['status']=='pass'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    try:passed=run(args.source.resolve(),args.output.resolve())
    except Exception as e:print(str(e),file=sys.stderr);return 1
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())

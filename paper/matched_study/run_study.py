#!/usr/bin/env python3
"""Before-inference frozen, paired local HTTP comparison of three readouts.

This research-only runner never edits the production engine or service.
Original external dataset text stays in a supplied cache outside the repository.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import http.client
import json
import math
import os
from pathlib import Path
import platform
import random
import selectors
import socket
import subprocess
import sys
import threading
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from native_engine import NativeEngine, MODEL_PIN, options_for, _sha_file

MODES=['direct','one_token','json']
SEED=2026092053


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path,value):
    with Path(path).open('x',encoding='utf-8') as handle:
        handle.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def verify_build(binary):
    folder=binary.resolve().parent.parent
    build=json.loads((folder/'BUILD.json').read_text())
    if build.get('llama_cpp_commit')!='f072b103714dfa1eee531f80b24512faf38e3dd2':
        raise ValueError('Wrong research llama.cpp revision')
    if build['source_sha256']!=digest((ROOT/'paper/matched_native/llama_matched_helper.cpp').read_bytes()):
        raise ValueError('Compiled helper source differs from current source')
    if build['build_script_sha256']!=digest((ROOT/'paper/matched_native/build.py').read_bytes()):
        raise ValueError('Build script changed after compile')
    for relative,expected in build['files_sha256'].items():
        path=folder/relative
        if not path.resolve().is_relative_to(folder) or path.is_symlink() or digest(path.read_bytes())!=expected:
            raise ValueError('Research runtime file differs from build manifest')
    for relative,target in build['symlinks'].items():
        path=folder/relative
        if not path.is_symlink() or os.readlink(path)!=target or not path.resolve().is_relative_to(folder):
            raise ValueError('Research runtime alias mismatch')
    if binary.resolve()!=folder/'bin/llama-matched-helper':raise ValueError('Unexpected research binary location')
    return build


def question(row):
    return {key:row[key] for key in ('type','state','instructions','criteria')}


def native_request(q,mode,request_id):
    formatter=object.__new__(NativeEngine)
    formatter.prompt_style='repeat_typed_score'
    opts=options_for(q)
    labels,prefix,kind=formatter._candidate_spec(q,opts)
    messages=formatter._messages(q,opts)
    if mode=='json':
        old='答えは選択肢の英大文字1文字だけを出力してください。説明は不要です。'
        new='回答はJSON形式 {"answer":"選んだ英大文字1文字"} だけを出力してください。説明は不要です。'
        messages=[dict(m,content=m['content'].replace(old,new)) for m in messages]
        prefix=''
    request={'id':request_id,'mode':mode,'messages':messages,'candidates':labels,
             'max_input_tokens':2048,'json_value_kind':kind,'max_output_tokens':32}
    if prefix:request['assistant_prefix']=prefix
    return request,[key for key,_ in opts]


def local_sample():
    path=ROOT/'acceptance-v2/questions_2400.jsonl'
    rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    groups=defaultdict(list)
    for row in rows:
        group=('generated',row['family']) if row['source']=='generated' else ('manual',row['type'])
        groups[group].append(row)
    result=[]
    for (source,family),members in sorted(groups.items()):
        ordered=sorted(members,key=lambda r:(digest(('mini-jev-matched-v1:'+r['id']).encode()),r['id']))
        for r in ordered[:3 if source=='generated' else 5]:
            r=dict(r,dataset='local_v2',group=source+':'+str(r.get('family',r.get('tag'))))
            if isinstance(r['label'],bool):r['label']=str(r['label']).lower()
            else:r['label']=str(r['label'])
            result.append(r)
    assert len(result)==150 and Counter(r['type'] for r in result)=={'choice':50,'noul':50,'score':50}
    return result


def load_rows(expanded):
    if expanded.resolve().is_relative_to(ROOT):
        raise ValueError('External question text must stay outside the repository')
    index=json.loads((ROOT/'paper/external_expanded/SELECTION.json').read_text())
    if digest(expanded.read_bytes())!=index['questions_sha256']:
        raise ValueError('External question bytes differ from the frozen source preparation')
    external=[json.loads(line) for line in expanded.read_text().splitlines() if line.strip()]
    if len(external)!=600 or Counter(r['dataset'] for r in external)!={'JCoLA':200,'JSTS':200,'JCommonsenseQA':200}:
        raise ValueError('Expected three frozen external datasets, 200 items each')
    rows=local_sample()+external
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate study ID')
    for r in rows:options_for(question(r))
    return rows


def reference(row):
    value={k:row[k] for k in ('id','dataset','type','group')}
    value['question_sha256']=digest(canonical(question(row)).encode())
    value['gold_score' if 'gold_score' in row else 'label']=row.get('gold_score',row.get('label'))
    if 'split' in row:value['split']=row['split']
    return value


def schedule(rows):
    rng=random.Random(SEED)
    batches=[]
    local=[r for r in rows if r['dataset']=='local_v2']
    external=[r for r in rows if r['dataset']!='local_v2']
    for repetition in range(5):
        subset=list(local)
        if repetition==0:subset+=external
        rng.shuffle(subset)
        for row in subset:
            modes=list(MODES);rng.shuffle(modes)
            for mode in modes:batches.append({'id':row['id'],'mode':mode,'repetition':repetition})
    assert len(batches)==4050
    return batches


def prepare(args):
    verify_build(args.native_binary)
    rows=load_rows(args.expanded_questions)
    protocol=json.loads((HERE/'PROTOCOL.json').read_text())
    args.output.mkdir(parents=True,exist_ok=False)
    index=[reference(r) for r in rows]
    ordering=schedule(rows)
    paths={'runner':Path(__file__),'protocol':HERE/'PROTOCOL.json','native_engine':ROOT/'native_engine.py',
           'helper_source':ROOT/'paper/matched_native/llama_matched_helper.cpp',
           'helper_build_manifest':args.native_binary.resolve().parent.parent/'BUILD.json',
           'helper_binary':args.native_binary,'expanded_questions':args.expanded_questions,
           'expanded_protocol':ROOT/'paper/external_expanded/PROTOCOL.json',
           'expanded_selection':ROOT/'paper/external_expanded/SELECTION.json',
           'expanded_preparation':ROOT/'paper/external_expanded/PREPARATION.json',
           'local_questions':ROOT/'acceptance-v2/questions_2400.jsonl'}
    artifacts={key:digest(path.read_bytes()) for key,path in paths.items()}
    manifest={'created_utc':now(),'stage':'before_study_model_inference','protocol':protocol,
              'sha256':artifacts,'selection_sha256':digest(canonical(index).encode()),
              'schedule_sha256':digest(canonical(ordering).encode()),'n_items':len(rows),'n_measured_calls':len(ordering),
              'note':'Locally timestamped protocol freeze; not independent public preregistration.'}
    write_new(args.output/'FREEZE.json',manifest)
    write_new(args.output/'SELECTION.json',index)
    write_new(args.output/'SCHEDULE.json',ordering)
    print(json.dumps({'prepared':len(rows),'measured_calls':len(ordering),'freeze_sha256':digest((args.output/'FREEZE.json').read_bytes())}),flush=True)


class Resident:
    def __init__(self,binary,model,log):
        self.log=log.open('w')
        self.process=subprocess.Popen([str(binary),'--model',str(model),'--ctx','2048','--gpu-layers','99','--threads','6'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,bufsize=0)
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)
        self.buffer=bytearray()
        self.ready=self.read()
        if self.ready.get('ready') is not True:raise RuntimeError('research helper failed to load')

    def read(self):
        import os
        until=time.monotonic()+120
        while b'\n' not in self.buffer:
            remaining=until-time.monotonic()
            if remaining<=0 or not self.selector.select(remaining):raise TimeoutError('research helper timeout')
            data=os.read(self.process.stdout.fileno(),65536)
            if not data:raise RuntimeError('research helper closed stdout')
            self.buffer.extend(data)
            if len(self.buffer)>1024*1024:raise RuntimeError('research helper response too large')
        line,_,rest=self.buffer.partition(b'\n');self.buffer=bytearray(rest)
        return json.loads(line)

    def call(self,request):
        self.process.stdin.write((canonical(request)+'\n').encode())
        self.process.stdin.flush()
        response=self.read()
        if response.get('id')!=request['id']:raise RuntimeError('research helper response ID mismatch')
        return response

    def close(self):
        if self.process.stdin:self.process.stdin.close()
        try:self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=10)
        self.selector.close();self.log.close()


def serve(resident,audits):
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def setup(self):
            super().setup()
            self.connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        def log_message(self,*unused):pass
        def do_POST(self):
            request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            started=time.perf_counter()
            native,keys=native_request(request['question'],request['mode'],request['request_id'])
            response=resident.call(native)
            # Keep numerical/generation audit data off the measured HTTP response.
            # The client receives an identical typed semantic-label schema in all modes.
            if 'error' in response:
                audits[request['request_id']]={'native':response,'server_ms':(time.perf_counter()-started)*1000}
                payload={'type':request['question']['type'],'error':'native_inference_failed'}
                status=500
            else:
                index=response['label_index']
                if type(index) is not int or not 0<=index<len(keys):raise ValueError('Invalid native label index')
                payload={'type':request['question']['type'],'label':keys[index]}
                audits[request['request_id']]={'native':response,'keys':keys,'server_ms':(time.perf_counter()-started)*1000}
                status=200
            body=canonical(payload).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);self.wfile.flush()
    server=HTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    return server,worker


def invoke(connection,q,mode,identifier):
    start=time.perf_counter()
    body=canonical({'question':q,'mode':mode,'request_id':identifier}).encode()
    connection.request('POST','/decide',body=body,headers={'Content-Type':'application/json'})
    response=connection.getresponse();parsed=json.loads(response.read())
    elapsed=(time.perf_counter()-start)*1000
    return parsed,response.status,elapsed,len(body)


def run(args):
    build=verify_build(args.native_binary)
    rows=load_rows(args.expanded_questions)
    manifest=json.loads((args.preparation/'FREEZE.json').read_text())
    paths={'runner':Path(__file__),'protocol':HERE/'PROTOCOL.json','native_engine':ROOT/'native_engine.py',
           'helper_source':ROOT/'paper/matched_native/llama_matched_helper.cpp','helper_binary':args.native_binary,
           'helper_build_manifest':args.native_binary.resolve().parent.parent/'BUILD.json',
           'expanded_questions':args.expanded_questions,'expanded_protocol':ROOT/'paper/external_expanded/PROTOCOL.json',
           'expanded_selection':ROOT/'paper/external_expanded/SELECTION.json',
           'expanded_preparation':ROOT/'paper/external_expanded/PREPARATION.json',
           'local_questions':ROOT/'acceptance-v2/questions_2400.jsonl'}
    for key,path in paths.items():
        if digest(path.read_bytes())!=manifest['sha256'][key]:raise ValueError('Frozen artifact changed: '+key)
    ordering=schedule(rows);refs=[reference(r) for r in rows]
    if digest(canonical(ordering).encode())!=manifest['schedule_sha256'] or digest(canonical(refs).encode())!=manifest['selection_sha256']:
        raise ValueError('Selection or schedule differs from freeze')
    args.output.mkdir(parents=True,exist_ok=False)
    digest_model,_=_sha_file(args.model_file)
    if digest_model!=MODEL_PIN['sha256']:raise ValueError('Model hash mismatch')
    by_id={r['id']:r for r in rows};audits={}
    startup=time.perf_counter()
    resident=Resident(args.native_binary.resolve(),args.model_file.resolve(),args.log_file)
    startup_ms=(time.perf_counter()-startup)*1000
    libraries={p.name:digest(p.read_bytes()) for p in args.native_binary.parent.glob('*.dylib') if not p.is_symlink()}
    write_new(args.output/'RUN_MANIFEST.json',{'created_utc':now(),'stage':'before_warmup_and_measured_inference',
        'freeze_sha256':digest((args.preparation/'FREEZE.json').read_bytes()),'helper_ready':resident.ready,
        'build_manifest':build,
        'model_sha256':digest_model,'library_sha256':libraries,'startup_after_model_hash_ms':startup_ms,
        'python':platform.python_version(),'os':platform.platform(),'machine':platform.machine(),
        'hardware':'Apple M5 Pro, 64 GB','timing':'client serialization through loopback HTTP response read/parse; resident model; single request at a time'})
    server,worker=serve(resident,audits)
    connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=120)
    counts=Counter();failed=0;index=0
    try:
        warm={'type':'choice','state':'箱は赤色です。','instructions':'箱の色を選んでください。',
              'criteria':{'blue':'青色','red':'赤色'}}
        with (args.output/'warmup.jsonl').open('x') as stream:
            for repetition in range(7):
                for mode in MODES:
                    index+=1;answer,status,elapsed,_=invoke(connection,warm,mode,index)
                    audit=audits.pop(index)
                    if status!=200:raise RuntimeError('Warmup failed')
                    stream.write(canonical({'mode':mode,'repetition':repetition,'elapsed_ms':elapsed,'answer':answer,'audit':audit})+'\n')
        with (args.output/'predictions.jsonl').open('x') as stream:
            for entry in ordering:
                row=by_id[entry['id']];index+=1
                answer,status,elapsed,request_bytes=invoke(connection,question(row),entry['mode'],index)
                audit=audits.pop(index)
                # No prompt, messages, full input IDs, or dataset source sentences are published.
                for key in ('prompt','messages','input_token_ids'):
                    if key in audit['native']:raise RuntimeError('Native audit unexpectedly exposes source text')
                record={**reference(row),**entry,'request_id':index,'http_status':status,
                        'http_ms':elapsed,'request_bytes':request_bytes,'answer':answer,**audit}
                stream.write(canonical(record)+'\n');stream.flush()
                counts[entry['mode']]+=1
                failed+=status!=200
                if sum(counts.values())%75==0:
                    print(json.dumps({'completed':sum(counts.values()),'total':len(ordering),'failures':failed,'counts':dict(counts)}),flush=True)
        write_new(args.output/'COMPLETION.json',{'completed_utc':now(),'measured_calls':sum(counts.values()),
                  'counts':dict(counts),'failures':failed,'warmup_calls':21,
                  'predictions_sha256':digest((args.output/'predictions.jsonl').read_bytes())})
        verify_build(args.native_binary)
    finally:
        connection.close();server.shutdown();server.server_close();worker.join(timeout=5);resident.close()
    print(json.dumps({'completed':sum(counts.values()),'failures':failed}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for action in ('prepare','run'):
        p=sub.add_parser(action)
        p.add_argument('--expanded-questions',type=Path,required=True)
        p.add_argument('--native-binary',type=Path,required=True)
        p.add_argument('--output',type=Path,required=True)
        if action=='run':
            p.add_argument('--preparation',type=Path,required=True)
            p.add_argument('--model-file',type=Path,required=True)
            p.add_argument('--log-file',type=Path,required=True)
    args=parser.parse_args()
    prepare(args) if args.command=='prepare' else run(args)


if __name__=='__main__':main()

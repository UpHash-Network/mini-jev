#!/usr/bin/env python3
"""Independent standard-library scorer; live mode is explicit and loopback only.

A passing historical-file score is NOT new inference. Live mode issues one
three-question request plus three invalid requests expected to be rejected
before inference. No statistical accuracy or latency conclusion is supported.
"""
from __future__ import annotations
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, ProxyHandler, build_opener

HERE=Path(__file__).resolve().parent
MODEL='ggml-org/Qwen3.6-35B-A3B-GGUF'
REVISION='baec3ebee244827cda0f4557eafa8b28f7545fa6'
EXPECTED_LABELS={'next_action':'heal','need_healing':'true','danger_level':'2'}
MAX_RESPONSE_BYTES=1024*1024


def require(condition,message):
    if not condition: raise ValueError(message)


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def close(a,b,tolerance=1e-9):
    return finite(a) and finite(b) and math.isclose(a,b,rel_tol=tolerance,abs_tol=tolerance)


def score(health,response,request):
    require(health.get('ready') is True,'health.ready must be true')
    require(health.get('model')==MODEL,'health model differs')
    require(health.get('model_revision')==REVISION,'health revision differs')
    require(response.get('model')==MODEL,'response model differs')
    answers=response.get('answers',{})
    require(set(answers)==set(request['questions']),'question IDs differ')
    checks=[]
    for qid,q in request['questions'].items():
        a=answers[qid];kind=q['type']
        require(a.get('type')==kind,qid+': wrong type')
        keys=set(q['criteria']) if kind=='choice' else ({'false','true'} if kind=='noul' else {str(i) for i in range(len(q['criteria']))})
        probs=a.get('probabilities',{})
        require(set(probs)==keys,qid+': missing or extra candidates')
        require(all(finite(x) and 0<=x<=1 for x in probs.values()),qid+': invalid probability')
        require(close(math.fsum(probs.values()),1),qid+': probabilities do not sum to one')
        require(a.get('label') in keys,qid+': label outside candidates')
        require(close(probs[a['label']],max(probs.values())),qid+': label is not a maximum-probability candidate')
        require(a.get('probability_semantics')=='conditional_on_allowed_label_tokens',qid+': probability semantics differs')
        require(a.get('calibrated') is False,qid+': calibrated flag must be false for this T=1 smoke')
        require(a.get('temperature_calibration_applied') is False,qid+': calibration unexpectedly applied')
        require(a.get('calibration_generalization_validated') is False,qid+': unsupported calibration claim')
        entropy=-math.fsum(v*math.log(v) for v in probs.values() if v>0)
        require(close(a.get('confidence'),1-entropy/math.log(len(probs))),qid+': concentration inconsistent')
        require(a.get('confidence_definition')=='one_minus_normalized_entropy_not_probability_of_correctness',qid+': concentration definition differs')
        if kind=='choice':require(a.get('choice')==a['label'],qid+': choice/label mismatch')
        elif kind=='noul':require(close(a.get('noul'),probs['true']),qid+': Noul is not P(true)')
        else:
            expected=math.fsum(int(k)*v for k,v in probs.items())
            require(close(a.get('score'),expected),qid+': Score is not the candidate expectation')
            require(a.get('legend')=={str(i):text for i,text in enumerate(q['criteria'])},qid+': legend differs')
        checks.append({'question_id':qid,'contract_pass':True,'label':a['label'],'historical_smoke_label':EXPECTED_LABELS[qid],'historical_label_match':a['label']==EXPECTED_LABELS[qid]})
    usage=response.get('usage',{})
    require(type(usage.get('questions')) is int and usage['questions']==3,'usage.questions must be 3')
    require(type(usage.get('output_tokens')) is int and usage['output_tokens']==0,'output token count must be zero')
    require(type(usage.get('input_tokens')) is int and usage['input_tokens']>0,'input token count invalid')
    require(finite(response.get('latency_ms')) and response['latency_ms']>=0,'latency metadata invalid')
    require(isinstance(response.get('request_id'),str) and response['request_id'],'missing request ID')
    return {'contract_status':'pass','question_checks':checks,'historical_labels_all_match':all(x['historical_label_match'] for x in checks),'exact_probability_match_required':False,'input_token_count_expected_only_as_historical_reference':813,'scope':'One synthetic three-type interface smoke. No accuracy rate, cross-machine numerical parity or timing equivalence is established.'}


def check_historical(source):
    receipt=json.loads((source/'paper/naacl2027/reproducibility/LIVE_SMOKE.json').read_text(encoding='utf-8'))
    request=json.loads((HERE/'request.json').read_text(encoding='utf-8'))
    require(receipt['request']==request,'historical request differs')
    positive=score(receipt['health'],receipt['response'],request)
    mutations=[
      ('false_readiness',lambda h,r:h.update(ready=False)),
      ('wrong_revision',lambda h,r:h.update(model_revision='wrong')),
      ('missing_candidate',lambda h,r:r['answers']['next_action']['probabilities'].pop('attack')),
      ('nonnormalized_probabilities',lambda h,r:r['answers']['next_action']['probabilities'].update(heal=0.5)),
      ('noul_not_true_probability',lambda h,r:r['answers']['need_healing'].update(noul=0.1)),
      ('score_not_expectation',lambda h,r:r['answers']['danger_level'].update(score=0.5)),
      ('false_correctness_probability_claim',lambda h,r:r['answers']['need_healing'].update(probability_semantics='probability_of_correctness')),
      ('generated_tokens',lambda h,r:r['usage'].update(output_tokens=1)),
      ('nonfinite_probability',lambda h,r:r['answers']['need_healing']['probabilities'].update(true=float('nan'))),
    ]
    rejected=[]
    for name,mutate in mutations:
        health,response=copy.deepcopy(receipt['health']),copy.deepcopy(receipt['response'])
        mutate(health,response)
        try:score(health,response,request)
        except ValueError as error:rejected.append({'mutation':name,'rejected':True,'reason':str(error)})
        else:raise ValueError('Scorer accepted mutation '+name)
    return {'status':'pass','mode':'historical_receipt_and_in_memory_negative_controls','scored_historical_receipt':positive,'negative_controls':rejected,'new_model_calls':0,'new_http_requests':0,'not_new_inference':True}


def live(base_url):
    parsed=urlparse(base_url)
    require(parsed.scheme=='http' and parsed.hostname in {'127.0.0.1','localhost'} and parsed.username is None and parsed.password is None and parsed.path in {'','/'} and not parsed.query and not parsed.fragment,'Use http://127.0.0.1:PORT only; remote/proxy routes are unsupported')
    base_url=base_url.rstrip('/')
    opener=build_opener(ProxyHandler({}))
    observed=[]
    def call(path,payload=None):
        request=Request(base_url+path,data=None if payload is None else json.dumps(payload,ensure_ascii=False,allow_nan=False).encode(),headers={} if payload is None else {'Content-Type':'application/json'})
        exchange={'method':request.get_method(),'path':path,'payload':payload,'status':None,'capture_limit_bytes':MAX_RESPONSE_BYTES}
        observed.append(exchange)  # Includes connection failures before a response exists.
        try:
            try:stream=opener.open(request,timeout=120)
            except HTTPError as error:stream=error  # Error response bodies are evidence too.
            with stream:
                exchange['status']=stream.status
                exchange['content_type']=stream.headers.get('Content-Type')
                data=stream.read(MAX_RESPONSE_BYTES+1)
        except Exception as error:
            exchange['transport_error']=type(error).__name__+': '+str(error)
            raise
        raw=data[:MAX_RESPONSE_BYTES]
        exchange.update(raw_body_base64=base64.b64encode(raw).decode('ascii'),
                        raw_body_sha256=hashlib.sha256(raw).hexdigest(),
                        captured_bytes=len(raw),body_truncated=len(data)>MAX_RESPONSE_BYTES,
                        raw_body_utf8=raw.decode('utf-8',errors='replace'))
        if exchange['body_truncated']:
            exchange['decode_error']='Response exceeded capture limit; retained prefix was not parsed'
            raise ValueError(exchange['decode_error'])
        try:
            text=raw.decode('utf-8')
            def reject_constant(value):raise ValueError('Non-finite JSON constant: '+value)
            body=json.loads(text,parse_constant=reject_constant)
        except (UnicodeError,ValueError) as error:
            exchange['decode_error']=type(error).__name__+': '+str(error)
            raise ValueError('Response JSON decode failed; raw bytes retained') from error
        exchange['body']=body
        return exchange['status'],body
    try:
        hs,health=call('/health');require(hs==200 and health.get('ready') is True,'Service not ready; no inference sent')
        require(health.get('model')==MODEL and health.get('model_revision')==REVISION,'Health model/revision differs; no inference sent')
        request=json.loads((HERE/'request.json').read_text(encoding='utf-8'))
        invalid=[('unknown_type',{'state':'smoke','questions':{'bad':{'type':'unknown','instructions':'invalid'}}}),('one_choice',{'state':'smoke','questions':{'bad':{'type':'choice','instructions':'invalid','criteria':{'one':'only'}}}}),('model_mismatch',{**request,'model':'wrong-model'})]
        negative=[]
        for name,payload in invalid:
            status,body=call('/v1/systemone',payload)
            negative.append({'name':name,'status':status,'error':body.get('error'),'expected_http_status':422})
            require(status==422 and isinstance(body.get('error'),dict),name+': expected HTTP422 rejection; stop before valid smoke')
        status,response=call('/v1/systemone',request);require(status==200,'Valid smoke returned HTTP'+str(status))
        scored=score(health,response,request)
        return {'status':'pass' if scored['historical_labels_all_match'] else 'contract_pass_historical_labels_differ','mode':'actual_loopback_http_three_type_smoke','checked_at_utc':datetime.now(timezone.utc).isoformat(),'environment':{'platform':platform.platform(),'machine':platform.machine(),'python':sys.version},'request':request,'health':health,'response':response,'negative_http_checks':negative,'checks':scored,'valid_inference_http_requests':1,'typed_questions':3,'invalid_http_requests':3,'invalid_requests_expected_rejected_before_inference':True,'human_participants':0,'operator_independence':'Not inferred by script; fill operator log','limitations':['A synthetic smoke is not an accuracy benchmark.','Native build fingerprints and probabilities may differ across valid environments; exact historical probabilities and wall time are not acceptance criteria.']}
    except Exception as error:
        return {'status':'fail','mode':'actual_loopback_http_three_type_smoke','checked_at_utc':datetime.now(timezone.utc).isoformat(),'error':type(error).__name__+': '+str(error),'observed_http_exchanges':observed,'no_success_claim':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-check',type=Path,metavar='SOURCE',help='Score old public receipt and in-memory mutants only; no network')
    group.add_argument('--live',metavar='BASE_URL',help='Explicitly send to an already-running loopback native service')
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output exists; preserve receipts and choose a new path')
    try:result=check_historical(args.self_check.resolve()) if args.self_check else live(args.live)
    except Exception as error:
        result={'status':'fail','mode':'historical_only' if args.self_check else 'live_requested','error':type(error).__name__+': '+str(error),'no_success_claim':True}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'output':str(args.output)}))
    return 0 if result['status']=='pass' else 1

if __name__=='__main__':raise SystemExit(main())

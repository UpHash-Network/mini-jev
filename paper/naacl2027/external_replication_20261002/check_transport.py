#!/usr/bin/env python3
"""Targeted stdlib loopback transport checks; fake HTTP data, no native model."""
from __future__ import annotations
import argparse
import base64
from datetime import datetime,timezone
import hashlib
from http.server import HTTPServer,BaseHTTPRequestHandler
import importlib.util
import json
from pathlib import Path
import socket
import threading

HERE=Path(__file__).resolve().parent


def run(output):
    if output.exists():raise ValueError('Choose a new output directory')
    output.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('logittrail_smoke_contract',HERE/'smoke_contract.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    checks=[]
    fixtures=[('malformed_json',200,b'{"ready": tru','application/json'),
              ('http_500',500,b'{"error":{"code":"fixture_failure","message":"synthetic server error"}}','application/json'),
              ('invalid_utf8',200,b'{"ready":"\xff"}','application/json'),
              ('oversized_response',200,b'x'*(module.MAX_RESPONSE_BYTES+20),'text/plain')]
    for name,status,body,mime in fixtures:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(status);self.send_header('Content-Type',mime)
                self.send_header('Content-Length',str(len(body)));self.end_headers()
                try:self.wfile.write(body)
                except (BrokenPipeError,ConnectionResetError):pass
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:result=module.live('http://127.0.0.1:'+str(server.server_port))
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
        assert result['status']=='fail' and result['no_success_claim'] is True
        assert len(result['observed_http_exchanges'])==1
        exchange=result['observed_http_exchanges'][0]
        assert exchange['method']=='GET' and exchange['path']=='/health' and exchange['status']==status
        expected=body[:module.MAX_RESPONSE_BYTES]
        assert base64.b64decode(exchange['raw_body_base64'])==expected
        assert exchange['raw_body_sha256']==hashlib.sha256(expected).hexdigest()
        assert exchange['captured_bytes']==len(expected)
        assert exchange['body_truncated']==(len(body)>module.MAX_RESPONSE_BYTES)
        if name=='http_500':assert exchange['body']['error']['code']=='fixture_failure'
        else:assert exchange.get('decode_error')
        result['test_context']='Synthetic loopback HTTP fixture; no native service, model inference or human participant.'
        if name=='oversized_response':
            # Do not duplicate a 1MiB synthetic prefix in the public receipt.
            exchange.pop('raw_body_base64');exchange.pop('raw_body_utf8')
            exchange['receipt_note']='The full prefix was compared in memory; only hash, length and truncation proof retained here.'
        (output/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        checks.append({'fixture':name,'status':'pass','method':'GET','path':'/health','http_status':status,'raw_prefix_exact':True,'captured_bytes':len(expected),'body_truncated':len(body)>module.MAX_RESPONSE_BYTES,'valid_inference_requests':0})
    # Bound but non-listening socket deterministically rejects a connect without
    # releasing the ephemeral port for another process to occupy.
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as reserved:
        reserved.bind(('127.0.0.1',0))
        result=module.live('http://127.0.0.1:'+str(reserved.getsockname()[1]))
    assert result['status']=='fail' and len(result['observed_http_exchanges'])==1
    ex=result['observed_http_exchanges'][0]
    assert ex['method']=='GET' and ex['path']=='/health' and ex['status'] is None and ex.get('transport_error')
    assert 'raw_body_base64' not in ex
    result['test_context']='Reserved non-listening loopback port; no service, model inference or human participant.'
    (output/'connection_refused.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    checks.append({'fixture':'connection_refused','status':'pass','http_status':None,'method':'GET','path':'/health','transport_error_retained':True,'response_body_received':False,'valid_inference_requests':0})
    report={'status':'pass','checked_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Five targeted transport failure checks with ephemeral stdlib HTTP fixtures; not live native inference','smoke_contract_sha256':hashlib.sha256((HERE/'smoke_contract.py').read_bytes()).hexdigest(),'check_transport_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':checks,'new_model_calls':0,'full_analysis_replayed':False,'preflight_rerun':False,'human_participants':0}
    (output/'TRANSPORT_CHECK.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'pass','targeted_checks':len(checks),'new_model_calls':0,'receipt':str(output/'TRANSPORT_CHECK.json')}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args().output.resolve())

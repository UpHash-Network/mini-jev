"""Integration test: reload the actual model twice and exercise HTTP and SDK."""
import argparse
import dataclasses
import json
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from service import Client

ROOT = Path(__file__).resolve().parent


def run(output):
    output.mkdir(parents=True,exist_ok=False)
    payload=json.loads((ROOT/'request.json').read_text())
    config=json.loads((ROOT/'release_config.json').read_text())
    if not (ROOT/'temperature.json').is_file():
        raise ValueError('the release temperature.json must be installed before integration verification')
    runs=[]
    for iteration in range(2):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        with (output/f'server-{iteration+1}.log').open('w') as log:
            process=subprocess.Popen([sys.executable,str(ROOT/'run_service.py'),'--port',str(port)],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            started=time.monotonic()
            try:
                client=Client(f'http://127.0.0.1:{port}')
                deadline=time.monotonic()+120
                while time.monotonic()<deadline:
                    if process.poll() is not None: raise RuntimeError('server exited while loading model')
                    try:
                        health=client.health()
                        if health['ready']: break
                    except (OSError,urllib.error.URLError): pass
                    time.sleep(.2)
                else: raise TimeoutError('server did not become ready')
                load_seconds=time.monotonic()-started
                assert health['model_revision']==config['revision']
                assert health['model']==config['model']
                response=client.system_one(**payload)
                answers={key:dataclasses.asdict(a) for key,a in response.answers.items()}
                assert all(a['temperature_calibration_applied'] is True for a in answers.values())
                assert answers['next_action']['choice']=='heal'
                assert answers['need_healing']['label']=='true'
                assert answers['danger_level']['label']=='2'
                assert response.usage['output_tokens']==0
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                request=urllib.request.Request(client.base_url+'/v1/systemone',
                    data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
                with opener.open(request,timeout=35) as raw:
                    http_response=json.load(raw)
                assert answers==http_response['answers']
                all_questions={f'question_{i}':list(payload['questions'].values())[i%3] for i in range(8)}
                eight=client.system_one(state=payload['state'],questions=all_questions)
                assert len(eight.answers)==8 and eight.usage['questions']==8
                for i,a in enumerate(eight.answers.values()):
                    reference=list(answers.values())[i%3]
                    assert a.label==reference['label']
                    assert max(abs(a.probabilities[k]-reference['probabilities'][k]) for k in a.probabilities)<1e-3
                # The real endpoint must reject malformed input without revealing internals.
                malformed=urllib.request.Request(client.base_url+'/v1/systemone',
                    data=b'{"state":"a","state":"b","questions":{}}',headers={'Content-Type':'application/json'})
                try:
                    opener.open(malformed,timeout=10)
                    raise AssertionError('duplicate JSON keys accepted')
                except urllib.error.HTTPError as e:
                    body=json.load(e)
                    assert e.code==422 and 'error' in body and 'Traceback' not in str(body)
                runs.append(dict(load_seconds=load_seconds,health=health,answers=answers,
                    sdk_http_exact_match=True,eight_questions_valid=True,duplicate_json_rejected=True,
                    request_latency_ms=response.latency_ms,usage=response.usage))
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    try: process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        process.terminate();process.wait(timeout=10)
    assert runs[0]['answers']==runs[1]['answers'], 'model reload changed probabilities'
    report=dict(passed=True,model_reload_exact_match=True,runs=runs)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    run(parser.parse_args().output_dir)

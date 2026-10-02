#!/usr/bin/env python3
"""Compose an actual Explorer screencast, a labeled archival live excerpt, and captions."""
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
p=argparse.ArgumentParser();p.add_argument('--capture-dir',type=Path,required=True);args=p.parse_args()
r=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent;c=args.capture_dir.resolve();w=c/'compose';w.mkdir(exist_ok=True)
meta=json.loads((c/'capture.json').read_text());assert not meta['errors'];src=c/meta['video'];assets=r/'docs/assets';ff=shutil.which('ffmpeg');probe=shutil.which('ffprobe');assert ff and probe
font_path='/System/Library/Fonts/Supplemental/Arial.ttf';bold_path='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def text(d,xy,s,size=38,bold=False,fill='white'):
 f=ImageFont.truetype(bold_path if bold else font_path,size);box=d.textbbox(xy,s,font=f);assert box[2]<1880 and box[3]<1050,(s,box);d.text(xy,s,font=f,fill=fill)
def strip(name,title,caption):
 im=Image.new('RGB',(1920,120),'#11263B');d=ImageDraw.Draw(im);text(d,(44,12),title,27,True,'#B8D9DD');text(d,(44,56),caption,36);dest=w/(name+'.png');im.save(dest);return dest
captions={
 'overview':('SAVED EVIDENCE EXPLORER  |  No model or API key','Choose a recorded observation. All eligible panel items remain available.'),
 'order-comparison':('1 / FOLLOW A DECISION CHANGE  |  Illustrative saved example','Reversing the displayed options changes the selected semantic answer.'),
 'order-probabilities':('COMPARE THE SAME CANDIDATES','A and B use one probability scale. Compare the answer with its reference.'),
 'averaging-comparison':('2 / ACCOUNT FOR SHARED EXECUTIONS','One call versus five calls; one is shared. The union is five, not six.'),
 'averaging-reference':('MORE CALLS DO NOT GUARANTEE A BETTER ANSWER','This selected example changes from correct to incorrect after averaging.'),
 'source-trace':('3 / TRACE THE EVIDENCE','Expand original members, one-based JSONL lines, mappings, and hashes.'),
 'export':('EXPORT EXACT COMPARISON JSON','Download preserves probabilities and source definitions; no new inference.'),
 'score':('4 / SEPARATE EXPECTATION FROM THE MODE','The expected stage differs from the most likely stage in both conditions.'),
 'collapse-comparison':('5 / CHECK THE FULL PANEL','A single item cannot establish collapse. Inspect every retained item.'),
 'full-panel':('FULL-PANEL FREQUENCIES AND SCORE RANGE','These 200-item counts remain independent of the selected source item.'),
 'next-item-same-panel':('MOVE TO ANOTHER ITEM','The selected item changes; full-panel frequencies retain the same scope.'),
 'scope':('KNOW WHAT THE RECORDS SUPPORT','Examples are outcome-selected; interface checks are not a user study.')}
common=['-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-r','25','-an','-threads','2']
segments=[];scenes=[];elapsed=0

def card(name,title,lines,duration):
 global elapsed
 im=Image.new('RGB',(1920,1080),'#F2F5F2');d=ImageDraw.Draw(im)
 text(d,(90,90),'LOGITTRAIL  /  Yuki Oshio  /  UPHASH Inc.',35,True,'#16856C');text(d,(90,220),title,76,True,'#163328')
 for i,line in enumerate(lines):text(d,(90,400+90*i),line,39,False,'#163328')
 text(d,(90,995),'Research manuscript • Not peer reviewed • No new model run in this video',27,False,'#536B60')
 png=w/(name+'.png');im.save(png);dest=w/(name+'.mp4')
 subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-loop','1','-i',str(png),'-t',str(duration),*common,str(dest)],check=True)
 segments.append(dest);scenes.append({'start':elapsed,'end':elapsed+duration,'kind':'title_card','title':title});elapsed+=duration
 if name=='intro':im.save(assets/'LogitTrail_Demo_20261002.jpg',quality=94)
card('intro','Inspect the decision. Trace the evidence.', ['A real browser walkthrough of saved experiment records.', 'Then: an archival excerpt of the separate local inference UI.', 'Code and evidence: uphash-network.github.io/mini-jev/'],6)
for a,b in zip(meta['events'],meta['events'][1:]):
 name=a['name'];duration=b['seconds']-a['seconds'];title,caption=captions[name];cap=strip(name,title,caption);dest=w/(name+'.mp4')
 subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-ss',str(a['seconds']),'-t',str(duration),'-i',str(src),'-loop','1','-i',str(cap),'-filter_complex','[0:v]scale=1920:960,pad=1920:1080:0:0:black[v];[v][1:v]overlay=0:960:shortest=1[o]','-map','[o]','-t',str(duration),*common,str(dest)],check=True)
 segments.append(dest);scenes.append({'start':elapsed,'end':elapsed+duration,'kind':'actual_explorer_interaction','name':name,'title':title,'caption':caption,'source_start':a['seconds'],'source_end':b['seconds']});elapsed+=duration
arch=assets/'Mini_Jev_Demonstration.mp4';cap=strip('archive','ARCHIVAL LIVE UI  |  Former name Mini Jev  |  Separate Qwen3.6 run','Edit questions, run Choice / Noul / Score, and inspect the response.');dest=w/'archive.mp4'
subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-ss','34.5','-t','16','-i',str(arch),'-loop','1','-i',str(cap),'-filter_complex','[0:v][1:v]overlay=0:960:shortest=1[o]','-map','[o]','-t','16',*common,str(dest)],check=True)
segments.append(dest);scenes.append({'start':elapsed,'end':elapsed+16,'kind':'archival_live_ui','source_start':34.5,'source_end':50.5,'caption_replaced_only':True});elapsed+=16
card('outro','Try it without downloading a model.', ['1. Open the saved-evidence Explorer.', '2. Verify the archive and rerun the frozen analyses.', '3. Optionally install the local model (20.4 GB file).','uphash-network.github.io/mini-jev/'],8)
listing=w/'concat.txt';listing.write_text(''.join("file '"+x.as_posix()+"'\n" for x in segments));dest=assets/'LogitTrail_Demo_20261002.mp4'
subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart','-metadata','title=LogitTrail: inspect and trace typed decisions','-metadata','artist=Yuki Oshio, UPHASH Inc.','-metadata','comment=Actual saved-evidence browser interaction plus labeled archival local inference excerpt; no new inference. Silent with embedded English captions.',str(dest)],check=True)
info=json.loads(subprocess.check_output([probe,'-v','error','-show_format','-show_streams','-of','json',str(dest)],text=True));dur=float(info['format']['duration']);assert dur<=150 and dur>100
prov={'artifact':str(dest.relative_to(r)),'duration_seconds':dur,'dimensions':[1920,1080],'fps':25,'audio':False,'captions':'Embedded English text; transcript supplied separately.','sha256':sha(dest),'bytes':dest.stat().st_size,'raw_capture_sha256':sha(src),'archival_source_sha256':sha(arch),'evidence_index_sha256':sha(r/'docs/explorer/data/index.json'),'scenes':scenes,'scope':'Recorded interactions with frozen data, plus 16 seconds of previously recorded local inference. Neither human evaluation nor a fresh model run. Actual UI pixels are scaled uniformly; caption strip is outside the Explorer viewport. Archival excerpt only replaces its original caption strip.','selection':'Four pre-existing deterministic outcome-selected illustrations; not representative sampling. See docs/explorer/DATA.md.','license':'CC BY-SA 4.0 for composed video and data-derived visuals; software remains MIT.','data_attribution':'JGLUE (Kurihara et al., 2022; https://github.com/yahoojapan/JGLUE); JCoLA (Someya et al., 2024; https://github.com/osekilab/JCoLA). See NOTICE.md.'}
(here/'PROVENANCE.json').write_text(json.dumps(prov,indent=2)+'\n');(here/'capture.json').write_text(json.dumps(meta,indent=2)+'\n')
trans=['# LogitTrail demonstration transcript','',prov['scope'],'']
for s in scenes:trans.append(f"- {s['start']:.1f}–{s['end']:.1f}s: {s.get('title',s.get('kind')).rstrip('.')}. {s.get('caption','')}".rstrip())
(here/'TRANSCRIPT.en.md').write_text('\n'.join(trans)+'\n');print(json.dumps({'duration':dur,'sha256':prov['sha256'],'bytes':prov['bytes']},indent=2))

#!/usr/bin/env python3
"""Build the captioned 60-second evidence walkthrough from frozen records.
Requires Pillow and ffmpeg/ffprobe. No model calls or network requests.
"""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from zipfile import ZipFile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--font', default='/System/Library/Fonts/Supplemental/Arial.ttf')
parser.add_argument('--bold-font', default='/System/Library/Fonts/Supplemental/Arial Bold.ttf')
args = parser.parse_args()
work = args.work_dir.resolve(); work.mkdir(parents=True, exist_ok=True)
assets = ROOT/'docs/assets'; out = assets/'Mini_Jev_60s.mp4'
archive = ROOT/'paper/naacl2027/reproducibility/naacl-repro-v1-20260925.zip'
member = 'mini-jev/paper/journal_robustness/cross_model/study_v1/results/qwen2.5-1.5b/predictions.jsonl'
with ZipFile(archive) as z:
    raw = z.read(member)
    rows = [json.loads(s) for s in raw.decode().splitlines()]
base = sorted([r for r in rows if r['dataset']=='JCoLA' and r['condition']=='baseline'], key=lambda r:r['item_id'])
reverse = {r['item_id']:r for r in rows if r['dataset']=='JCoLA' and r['condition']=='display_reverse'}
wrong = [r for r in base if r['label'] != r['gold_label']]
flips = sum(r['label'] != reverse[r['item_id']]['label'] for r in base)
assert len(base)==200 and len(wrong)==42 and flips==0
assert all(r['label']=='true' for r in base)
case = max(wrong, key=lambda r:r['probabilities']['true'])
case_rows = [{k:r[k] for k in ['condition','item_id','label','gold_label','probabilities','concentration','request_index']} for r in rows if r['item_id']==case['item_id']]
case_rows.sort(key=lambda r:['baseline','baseline_repeat','display_reverse'].index(r['condition']))
evidence = {'dataset':'JCoLA','model':'Qwen2.5-1.5B-Instruct','temperature':1,'unique_items':200,'predicted_acceptable':200,'correct':158,'incorrect':42,'display_reversal_label_flips':0,'illustrative_case_selection':'Highest baseline P(true) among the 42 errors; deliberately illustrative, not a random example.','illustrative_case':case_rows,'source_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'source_member':member,'source_member_sha256':hashlib.sha256(raw).hexdigest(),'no_original_dataset_text_included':True,'not_new_inference':True}
here = Path(__file__).resolve().parent
(here/'EVIDENCE.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
W,H=1920,1080
BG='#F2F5F2';INK='#163328';MUTED='#536B60';GREEN='#16856C';RED='#C6493A';PALE='#FFFFFF';BLUE='#263E9D'
font_cache={}
def font(size,bold=False):
    key=(size,bold)
    if key not in font_cache: font_cache[key]=ImageFont.truetype(args.bold_font if bold else args.font,size)
    return font_cache[key]
def text(d,xy,s,size=44,fill=INK,bold=False,max_width=1770):
    f=font(size,bold); box=d.textbbox(xy,s,font=f)
    assert box[2]<=W-55 and box[3]<=H-32 and box[2]-box[0]<=max_width,(s,box)
    d.text(xy,s,font=f,fill=fill)
def wrap(d,xy,s,size=44,width=1680,fill=INK,bold=False,spacing=14):
    x,y=xy; line=''
    for word in s.split():
        trial=(line+' '+word).strip()
        if d.textlength(trial,font=font(size,bold))>width:
            text(d,(x,y),line,size,fill,bold,max_width=width);y+=size+spacing;line=word
        else: line=trial
    if line:text(d,(x,y),line,size,fill,bold,max_width=width);y+=size+spacing
    return y

def card(section):
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,16),fill=GREEN)
    text(d,(85,61),'MINI JEV',32,GREEN,True)
    text(d,(335,61),section.upper(),30,MUTED)
    d.line((85,970,1835,970),fill='#CDDAD2',width=2)
    text(d,(85,996),'Yuki Oshio  /  UPHASH Inc.     •     Research manuscript, not peer reviewed',25,MUTED)
    return im,d

im,d=card('A 60-second evidence walkthrough')
text(d,(85,207),'Same answer.',115,INK,True)
text(d,(85,344),'Still wrong.',115,RED,True)
wrap(d,(90,555),'Inspect typed decisions, candidate probabilities, and failure cases from frozen local language models.',52,width=1590)
text(d,(90,786),'Recorded interface + visualized study records',35,MUTED)
text(d,(90,842),'No new model run is shown in this walkthrough.',35,MUTED)
im.save(work/'01.png');im.save(assets/'Mini_Jev_60s.jpg',quality=92)

# Replace the earlier video's caption strip only. UI pixels remain uncropped.
im=Image.new('RGB',(W,120),'#11263B');d=ImageDraw.Draw(im)
text(d,(40,9),'ARCHIVAL LIVE RECORDING  •  Qwen3.6-35B-A3B  •  interface example',27,'#B8D9DD',True)
text(d,(40,52),'Run Choice, Noul, and Score; inspect the candidate distributions.',40,'#FFFFFF')
im.save(work/'caption.png')

im,d=card('Archived research panel • Qwen2.5-1.5B • JCoLA • T = 1')
text(d,(85,148),'Stable across option order.',77,INK,True)
text(d,(85,247),'The model called every sentence acceptable.',49,MUTED)
for i in range(200):
    x=90+(i%25)*40;y=389+(i//25)*40
    d.rounded_rectangle((x,y,x+27,y+27),radius=5,fill=GREEN if i<158 else RED)
text(d,(90,737),'Each tile = one evaluated item',31,MUTED)
text(d,(90,796),'158 correct',41,GREEN,True);text(d,(405,796),'42 incorrect',41,RED,True)
text(d,(1210,388),'0 / 200',105,BLUE,True)
text(d,(1210,520),'labels changed',40,INK)
text(d,(1210,576),'after reversal',40,INK)
text(d,(90,881),'Fixed 200-item panel; this is not a claim about all tasks or models.',32,MUTED)
im.save(work/'03.png')

im,d=card('An illustrative error • saved model outputs')
text(d,(85,145),'99.88% on the wrong candidate.',73,RED,True)
text(d,(90,259),'Corpus label: unacceptable     /     Model choice: acceptable',41,INK,True)
text(d,(90,325),'Candidate P(acceptable)',33,MUTED)
for i,r in enumerate(case_rows):
    y=414+i*118; label=['Original order','Exact-input repeat','Reversed order'][i]
    text(d,(90,y),label,40,INK)
    d.rounded_rectangle((575,y+8,1545,y+50),radius=10,fill='#DBE4DF')
    d.rounded_rectangle((575,y+8,575+970*r['probabilities']['true'],y+50),radius=10,fill=RED)
    text(d,(1592,y-1),f"{100*r['probabilities']['true']:.2f}%",43,RED,True)
text(d,(90,802),'Candidate probability does not measure the probability of being correct.',38,INK,True)
text(d,(90,875),'JCoLA item: in_domain_valid:2827 • highest-P error selected for illustration',29,MUTED)
im.save(work/'04.png')

im,d=card('What to inspect')
text(d,(85,177),'Read the evidence together.',83,INK,True)
for n,(a,b) in enumerate([('Typed output','Does the value follow the API contract?'),('Candidate distribution','What alternatives did the model score?'),('Task quality','Does the answer match the reference?')]):
    y=355+n*166
    text(d,(90,y),f'0{n+1}',44,GREEN,True)
    text(d,(230,y),a,46,INK,True)
    text(d,(230,y+65),b,40,MUTED)
text(d,(90,890),'The workbench and reproducible records make these checks inspectable.',32,MUTED)
im.save(work/'05.png')

im,d=card('Try it • inspect it • reproduce it')
text(d,(85,211),'Explore Mini Jev.',100,INK,True)
text(d,(90,416),'uphash-network.github.io/mini-jev/',65,BLUE,True)
text(d,(90,566),'Manuscript  •  full demo  •  code  •  frozen evidence',43,INK)
text(d,(90,680),'Native inference: tested on Apple Silicon, 64 GB',36,MUTED)
text(d,(90,738),'CPU-only analysis replay is available without the model.',36,MUTED)
text(d,(90,854),'JCoLA: Someya, Sugimoto & Oseki (2024) • data-derived visuals: CC BY-SA 4.0',28,MUTED)
im.save(work/'06.png')

ff=shutil.which('ffmpeg'); probe=shutil.which('ffprobe')
assert ff and probe
common=['-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-r','25','-an']
segments=[]
for name,duration in [('01',6),('03',14),('04',16),('05',6),('06',6)]:
    dest=work/f'{name}.mp4'
    subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-loop','1','-framerate','25','-i',str(work/f'{name}.png'),'-t',str(duration),*common,str(dest)],check=True)
    segments.append(dest)
source=assets/'Mini_Jev_Demonstration.mp4'
clip=work/'02.mp4'
subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-ss','34.5','-t','12','-i',str(source),'-loop','1','-i',str(work/'caption.png'),'-filter_complex','[0:v][1:v]overlay=0:960:shortest=1[v]','-map','[v]','-t','12',*common,str(clip)],check=True)
segments.insert(1,clip)
listing=work/'concat.txt';listing.write_text(''.join("file '"+p.as_posix()+"'\n" for p in segments))
subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart','-metadata','title=Mini Jev: Stable answers can still be wrong','-metadata','artist=Yuki Oshio, UPHASH Inc.','-metadata','comment=Archival live UI excerpt and frozen study records. No new inference. Silent with embedded English text.',str(out)],check=True)
meta=json.loads(subprocess.check_output([probe,'-v','error','-show_format','-show_streams','-of','json',str(out)],text=True))
assert abs(float(meta['format']['duration'])-60)<.05
assert meta['streams'][0]['width']==W and meta['streams'][0]['height']==H
provenance={'artifact':'docs/assets/Mini_Jev_60s.mp4','duration_seconds':float(meta['format']['duration']),'dimensions':[W,H],'fps':25,'audio':False,'captions':'Embedded English explanatory text; Japanese and English transcript supplied separately.','sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size,'scenes':[{'start':0,'end':6,'type':'Introduction'},{'start':6,'end':18,'type':'Archival live UI','source':'paper/eacl2027/Mini_Jev_Demonstration.mp4','source_start':34.5,'source_end':46.5,'modification':'Only earlier 120px caption strip replaced; entire 1920x960 UI retained. Real-time speed.'},{'start':18,'end':32,'type':'Rendered aggregate study results'},{'start':32,'end':48,'type':'Rendered illustrative error records'},{'start':48,'end':54,'type':'Interpretation'},{'start':54,'end':60,'type':'Project link and attribution'}],'prior_video_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'evidence':'EVIDENCE.json','selection_limit':evidence['illustrative_case_selection'],'scope':'JCoLA 200-item panel, not a model-wide accuracy claim. UI excerpt uses a different checkpoint and English interface examples, not this JCoLA run.','license':'CC BY-SA 4.0 for this composed evidence video and data-derived visuals. Original software code remains MIT.','attribution':'JCoLA: Taiga Someya, Yushi Sugimoto, Yohei Oseki (2024), https://aclanthology.org/2024.lrec-main.828/ ; https://github.com/osekilab/JCoLA ; https://creativecommons.org/licenses/by-sa/4.0/'}
(here/'PROVENANCE.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(provenance,ensure_ascii=False,indent=2))

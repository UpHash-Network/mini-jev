import {parseJSONL,compareRecords,LIMITS} from './core.mjs';
import {syntheticJSONL} from './synthetic.mjs';
const $=id=>document.getElementById(id);
let parsed=null,current=null,generation=0;
const node=(tag,text,className)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(className)n.className=className;return n;};
const number=n=>new Intl.NumberFormat('en',{maximumSignificantDigits:6}).format(n);
const decimal=n=>new Intl.NumberFormat('en',{maximumFractionDigits:4}).format(n);
const percent=n=>`${decimal(100*n)}%`;
function resetView(){parsed=null;current=null;$('workspace').hidden=true;$('issues').hidden=true;for(const id of ['records','candidates','metrics','group','a','b','issue-list','context','outcome','reference','origin','latency','issue-summary'])$(id).replaceChildren();}
function clear(){generation++;resetView();$('file').value='';$('paste').value='';$('status').textContent='Data cleared from the app. Choose another local file.';$('status').className='status';}
function showIssues(result){
  const messages=[...result.errors.map(x=>({...x,severity:'error'})),...result.warnings.map(x=>({...x,severity:'warning'}))];
  $('issues').hidden=!messages.length;$('issues').open=!result.ok;$('issue-list').replaceChildren();
  $('issues-title').textContent=result.ok?`${result.warnings.length} input limitation(s) · expand to review`:`${result.errors.length} input error(s) · fix before importing`;
  $('issue-summary').textContent=result.ok ? `${result.warnings.length} disclosed limitation(s). The format passed; source authenticity and semantic meaning are not verified.` : `${result.errors.length} error(s). Nothing was imported; fix the file and retry.`;
  for(const issue of messages.slice(0,100))$('issue-list').append(node('li',`${issue.line===null?'File':`Line ${issue.line}`} · ${issue.code}: ${issue.message}`,issue.severity));
  if(messages.length>100)$('issue-list').append(node('li',`Showing the first 100 of ${messages.length} issues. A successful comparison download includes all warnings.`));
}
function load(input,label){
  resetView();parsed=parseJSONL(input);showIssues(parsed);
  $('status').className=parsed.ok?'status':'status error';
  if(!parsed.ok){$('status').textContent='Import rejected. No partial comparison is shown.';return;}
  $('status').textContent=`${label}: ${parsed.records.length} physical records across ${parsed.groups.length} model/item group(s). No model was run.`;
  $('group').replaceChildren();parsed.groups.forEach((g,i)=>{const o=node('option',`${g.model} / ${g.itemId} (${g.type})`);o.value=String(i);$('group').append(o);});
  $('workspace').hidden=false;selectGroup();
}
function selectGroup(){
  const group=parsed.groups[Number($('group').value)];
  for(const id of ['a','b']){$(id).replaceChildren();group.records.forEach((r,i)=>{const o=node('option',r.raw.condition);o.value=String(i);$(id).append(o);});}
  $('b').value=String(Math.min(1,group.records.length-1));
  $('context').textContent=`${group.type} · Semantic key schema: ${group.keySchema} · ${group.records.length} condition(s).${group.records.length===1?' Only one condition: A and B show the same record.':''}`;
  render();
}
function render(){
  const group=parsed.groups[Number($('group').value)],a=group.records[Number($('a').value)],b=group.records[Number($('b').value)];
  current=compareRecords(a,b);
  $('outcome').textContent=`${current.label_changed?'Argmax label changed':'Argmax label unchanged'}: ${current.a.label} → ${current.b.label}.${current.a.tied_labels.length>1||current.b.tied_labels.length>1?' Exact ties use the lexical semantic-key rule; see the original values.':''}`;
  $('metrics').replaceChildren();
  const metric=(title,value)=>{const d=node('div',undefined,'metric');d.append(node('span',title),node('strong',value));$('metrics').append(d);};
  if(group.type!=='choice'){metric(group.type==='noul'?'A · P(true)':'A · expected Score',number(current.a.typed_value));metric(group.type==='noul'?'B · P(true)':'B · expected Score',number(current.b.typed_value));}
  metric('Largest |Δ| (pp)',decimal(Math.max(...current.candidates.map(c=>Math.abs(c.delta)))*100));metric('Declared unique physical IDs',current.declared_physical_identities.unique);
  $('candidates').replaceChildren();for(const c of current.candidates){const row=node('tr');row.append(node('th',c.key),node('td',percent(c.a)),node('td',percent(c.b)),node('td',`${c.delta>0?'+':''}${decimal(c.delta*100)}`));row.firstChild.scope='row';$('candidates').append(row);}
  const ref=current.reference;
  $('reference').textContent=ref ? ref.kind==='score' ? `Supplied continuous reference: ${number(ref.value)}. Absolute error: A ${number(ref.aAbsoluteError)}, B ${number(ref.bAbsoluteError)}. This does not verify the reference.` : `Supplied reference label: ${ref.value}. A ${ref.aMatches?'matches':'does not match'}; B ${ref.bMatches?'matches':'does not match'}. This is a comparison with the supplied label.` : 'Reference unknown for one or both conditions. No correctness or reference-error result is available.';
  $('origin').textContent=`Distribution origin — A: ${current.a.origin}; B: ${current.b.origin}. Reported origins are not independently verified.`;
  $('latency').textContent=`Recorded latency — A: ${current.a.recorded_latency_ms===null?'unknown':number(current.a.recorded_latency_ms)+' ms'}; B: ${current.b.recorded_latency_ms===null?'unknown':number(current.b.recorded_latency_ms)+' ms'}. Financial cost is not provided by this schema.`;
  $('records').textContent=JSON.stringify(current.source_records,null,2);
}
$('file').addEventListener('change',async()=>{const file=$('file').files[0];if(!file)return;const ticket=++generation;resetView();if(file.size>LIMITS.bytes){const failure={ok:false,errors:[{line:null,code:'SIZE',message:'Use a JSONL file no larger than 25 MiB.'}],warnings:[]};showIssues(failure);$('status').textContent='Import rejected: the local file exceeds 25 MiB.';$('status').className='status error';return;}try{const text=await file.text();if(ticket===generation)load(text,'Local file');}catch{if(ticket===generation)$('status').textContent='The local file could not be read.';}});
$('parse').addEventListener('click',()=>{generation++;load($('paste').value,'Pasted JSONL');});
$('synthetic').addEventListener('click',()=>{generation++;$('file').value='';$('paste').value='';load(syntheticJSONL,'Clearly synthetic example — hand-written values, no experiment');});
$('clear').addEventListener('click',clear);$('group').addEventListener('change',selectGroup);$('a').addEventListener('change',render);$('b').addEventListener('change',render);
$('download').addEventListener('click',()=>{if(!current)return;const contents={...current,input_warnings:parsed.warnings};const blob=new Blob([JSON.stringify(contents,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),link=node('a');link.href=url;link.download='logittrail-local-comparison.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});

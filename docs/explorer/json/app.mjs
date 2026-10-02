import {validatePanel,compare,comparisonExport} from '../core.mjs';
const $=id=>document.getElementById(id),pretty=x=>JSON.stringify(x,null,2);
const data=new URL('../data/',import.meta.url);
let index,panel,descriptor,current;
function options(id,rows,desired){const select=$(id);select.replaceChildren(...rows.map(([value,label])=>{const option=document.createElement('option');option.value=value;option.textContent=label;return option;}));if(rows.some(r=>r[0]===desired))select.value=desired;}
function render(){
  const item=panel.items.find(i=>i.item_id===$('item').value);
  const a=item.variants.find(v=>v.id===$('a').value),b=item.variants.find(v=>v.id===$('b').value);
  current=comparisonExport(index,panel,item,a,b,compare(panel,item,a,b),{mode:'formatted_json_baseline'});
  current.panel_sha256=descriptor.sha256;
  $('comparison').textContent=pretty(current);
  const params=new URLSearchParams({study:panel.study_id,model:panel.model_key,dataset:panel.dataset,item:item.item_id,a:a.id,b:b.id});
  $('explorer').href=new URL('../#'+params,import.meta.url);
  history.replaceState(null,'','#'+params);
  $('download').disabled=false;
}
function itemChanged(a,b){const item=panel.items.find(i=>i.item_id===$('item').value);const rows=item.variants.map(v=>[v.id,v.id]);options('a',rows,a??rows[0][0]);options('b',rows,b??rows[1]?.[0]);render();}
async function panelChanged(selection={}){
  $('status').textContent='Loading complete saved panel…';
  descriptor=index.panels.find(p=>p.id===$('panel').value);
  const response=await fetch(new URL(descriptor.path,data));if(!response.ok)throw Error('Panel fetch failed: '+response.status);
  const bytes=await response.arrayBuffer();
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
  if(hash!==descriptor.sha256)throw Error('Panel hash mismatch');
  panel=validatePanel(JSON.parse(new TextDecoder().decode(bytes)));
  options('item',panel.items.map(i=>[i.item_id,i.item_id]),selection.item);
  $('summary').textContent=pretty(descriptor);
  $('all-items').textContent=pretty(panel);
  itemChanged(selection.a,selection.b);
  $('status').textContent='Panel SHA-256 verified. Same saved information as the Explorer; zero new inference calls.';
}
async function guard(fn){try{await fn();}catch(error){$('status').textContent='Error: '+error.message;$('download').disabled=true;}}
$('panel').onchange=()=>guard(()=>panelChanged());
$('item').onchange=()=>guard(()=>itemChanged());
for(const id of ['a','b'])$(id).onchange=()=>guard(render);
$('download').onclick=()=>{const url=URL.createObjectURL(new Blob([pretty(current)+'\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='logittrail-complete-comparison.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
await guard(async()=>{
  const response=await fetch(new URL('index.json',data));if(!response.ok)throw Error('Index fetch failed: '+response.status);
  index=await response.json();$('index').textContent=pretty(index);
  const query=new URLSearchParams(location.hash.slice(1));
  const desired=index.panels.find(p=>p.study_id===query.get('study')&&p.model_key===query.get('model')&&p.dataset===query.get('dataset'));
  options('panel',index.panels.map(p=>[p.id,p.study_id+' / '+p.model_key+' / '+p.dataset]),desired?.id);
  await panelChanged({item:query.get('item'),a:query.get('a'),b:query.get('b')});
});

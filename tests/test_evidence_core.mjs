import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {validatePanel,compare,comparisonExport,panelFrequencies} from '../docs/explorer/core.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const physical=(id,probabilities,label,line)=>({id,kind:'physical',probabilities,label,value:probabilities[1],concentration:0.1,calls:1,source:['s',line]});
const first=physical('forward',[.25,.75],'true',1),second=physical('reverse',[.5,.5],'false',2);
const average={id:'cyclic',kind:'derived',member_ids:['forward','reverse'],probabilities:[.375,.625],label:'true',value:.625,concentration:.1,calls:2};
const item={item_id:'test:1',gold_label:'true',variants:[first,second,average]};
const panel={study_id:'fixture',model_key:'fixture',dataset:'JCoLA',type:'noul',canonical_keys:['false','true'],items:[item]};
validatePanel(panel);
const shared=compare(panel,item,first,average);
assert.equal(shared.uniquePhysicalCalls,2);assert.equal(shared.sharedPhysicalCalls,1);
assert.equal(shared.reference.aMatch,true);assert.equal(shared.candidates[0].delta,.125);
assert.equal(compare(panel,item,first,second).labelChanged,true); // recorded tie rule is retained
assert.throws(()=>compare(panel,{...item},first,second),/share one panel/);
assert.throws(()=>validatePanel({...panel,items:[{...item,variants:[{...first,probabilities:[.2,.2]}]}]}),/sum to one/);
assert.throws(()=>validatePanel({...panel,items:[{...item,variants:[{...first,probabilities:[NaN,1]}]}]}),/Invalid candidate/);
assert.throws(()=>validatePanel({...panel,items:[{...item,variants:[first,second,{...average,calls:3}]}]}),/Call count/);
assert.throws(()=>validatePanel({...panel,items:[{...item,variants:[first,{...average,member_ids:['missing']}]}]}),/Missing source/);
const scoreA={...first,id:'s0',label:'1',value:0.75},scoreB={...second,id:'s1',label:'0',value:0.5};
const scoreItem={item_id:'score:1',gold_score:.6,variants:[scoreA,scoreB]};
const scorePanel={...panel,type:'score',canonical_keys:['0','1'],items:[scoreItem]};
const score=compare(scorePanel,scoreItem,scoreA,scoreB);
assert.equal(score.reference.value,.6);assert.ok(Math.abs(score.reference.aError-.15)<1e-15);assert.equal(score.reference.aMatch,undefined);
assert.deepEqual(panelFrequencies(panel,'cyclic'),{items:1,label_counts:{false:0,true:1}});

const path=resolve(root,'docs/explorer/data/index.json');
if(!existsSync(path))throw new Error('Build the actual evidence data before testing.');
const index=JSON.parse(readFileSync(path));let checked=0,exports=0;
for(const descriptor of index.panels){
  const p=validatePanel(JSON.parse(readFileSync(resolve(root,'docs/explorer/data',descriptor.path??descriptor.file))));
  for(const sourceItem of p.items){
    const a=sourceItem.variants[0];
    for(const b of sourceItem.variants){
      const result=compare(p,sourceItem,a,b);assert.equal(result.candidates.length,p.canonical_keys.length);assert.ok(result.uniquePhysicalCalls<=a.calls+b.calls);checked++;
    }
    const b=sourceItem.variants.at(-1),result=compare(p,sourceItem,a,b),record=comparisonExport(index,p,sourceItem,a,b,result,{mode:'test'});
    const restored=JSON.parse(JSON.stringify(record));assert.deepEqual(restored.conditions.a.probabilities,a.probabilities);assert.equal(restored.unique_physical_calls,restored.physical_members.length);assert.ok(Object.values(restored.sources).every(Boolean));for(const v of [a,b,...restored.physical_members]){if(v.source)assert.ok(restored.sources[v.source[0]],'Missing source definition for exported condition/member');}assert.ok(restored.model?.name);if(restored.model.source)assert.ok(restored.sources[restored.model.source]);exports++;
  }
}
console.log(JSON.stringify({status:'pass',actual_variant_comparisons:checked,actual_item_export_roundtrips:exports,invalid_cross_item_and_corrupt_probability_cases_rejected:true,shared_calls_counted_once:true,continuous_reference_not_rounded:true}));

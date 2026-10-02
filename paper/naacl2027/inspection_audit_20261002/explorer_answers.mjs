// Execute the unchanged, published Explorer computations for the entire corpus.
// The Python parent validates these task answers against the original ZIP.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {once} from 'node:events';
import {validatePanel,compare,comparisonExport,panelFrequencies} from '../../../docs/explorer/core.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const data=resolve(root,'docs/explorer/data');
const index=JSON.parse(readFileSync(resolve(data,'index.json')));
async function emit(value){if(!process.stdout.write(JSON.stringify(value)+'\n'))await once(process.stdout,'drain');}
for(const descriptor of index.panels){
  const panel=validatePanel(JSON.parse(readFileSync(resolve(data,descriptor.path))));
  for(const item of panel.items){
    for(let i=0;i<item.variants.length;i++)for(let j=i+1;j<item.variants.length;j++){
      const a=item.variants[i],b=item.variants[j],r=compare(panel,item,a,b);
      const exported=comparisonExport(index,panel,item,a,b,r,{mode:'exhaustive_nonhuman_audit'});
      // The complete formatted-JSON baseline uses the exact same export, with
      // complete panel and index available as separate expandable documents.
      const jsonBaseline=JSON.parse(JSON.stringify(exported,null,2));
      assert.deepEqual(jsonBaseline,exported);
      assert.deepEqual(exported.conditions,{a,b});
      assert.deepEqual(exported.candidate_comparison,r.candidates);
      assert.equal(exported.unique_physical_calls,r.uniquePhysicalCalls);
      assert.equal(exported.shared_physical_calls,r.sharedPhysicalCalls);
      assert.deepEqual(exported.reference,r.reference);
      for(const source of [a,b,...exported.physical_members].map(v=>v.source[0]))assert.deepEqual(exported.sources[source],index.sources[source]);
      await emit({kind:'pair',panel:panel.id,item:item.item_id,a:a.id,b:b.id,
        labelChanged:r.labelChanged,deltas:r.candidates.map(c=>c.delta),
        maxProbabilityDifference:r.maxProbabilityDifference,reference:r.reference,
        unique:r.uniquePhysicalCalls,shared:r.sharedPhysicalCalls,samePool:r.samePhysicalPool,
        physicalSources:exported.physical_members.map(v=>v.source),sourceDefinitions:Object.keys(exported.sources),
        completeJsonRoundTrip:true});
    }
  }
  for(const condition of descriptor.variant_ids)await emit({kind:'frequency',panel:panel.id,condition,...panelFrequencies(panel,condition)});
}

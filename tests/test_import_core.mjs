import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {parseJSONL,validateRecord,compareRecords} from '../docs/explorer/import/core.mjs';
import {syntheticRecords,syntheticJSONL} from '../docs/explorer/import/synthetic.mjs';
const clone=x=>structuredClone(x), lines=rs=>rs.map(r=>JSON.stringify(r)).join('\n'), close=(a,b)=>assert.ok(Math.abs(a-b)<1e-12,`${a} != ${b}`);
const base=()=>clone(syntheticRecords[0]);
const invalid=(change,code)=>{const r=base();change(r);assert.throws(()=>validateRecord(r),e=>e.code===code);};
const rejected=(rows,code)=>{const result=parseJSONL(lines(rows));assert.equal(result.ok,false);assert.ok(result.errors.some(e=>e.code===code));assert.deepEqual(result.records,[]);assert.deepEqual(result.groups,[]);};

test('hand-computed synthetic Choice, Noul and Score oracle',()=>{
 const result=parseJSONL(syntheticJSONL);assert.equal(result.ok,true);assert.equal(result.records.length,6);
 const [choice,noul,score]=result.groups.map(g=>compareRecords(...g.records));
 assert.equal(choice.a.label,'red');assert.equal(choice.b.label,'green');assert.equal(choice.reference.aMatches,true);assert.equal(choice.reference.bMatches,false);
 const c=Object.fromEntries(choice.candidates.map(c=>[c.key,c]));close(c.red.a,4/7);close(c.green.a,2/7);close(c.blue.a,1/7);close(c.green.b,4/7);close(c.red.delta,-2/7);
 close(noul.a.typed_value,0.25);close(noul.b.typed_value,0.75);assert.equal(noul.reference,null);
 close(score.a.typed_value,6.5);close(score.b.typed_value,5.5);close(score.reference.aAbsoluteError,0.25);close(score.reference.bAbsoluteError,0.75);
 assert.equal(score.b.origin,'renormalized_candidate_scores');assert.equal(choice.a.recorded_latency_ms,null);
 assert.equal(result.warnings.some(w=>w.code==='RENORMALIZED_ORIGIN'),true);
});
test('joint tuple permutations preserve probability mapping and typed values',()=>{
 for(const raw of syntheticRecords){const a=validateRecord(raw),b=clone(raw);for(const key of ['candidate_keys','logits','probabilities','score_values'])if(Array.isArray(b[key]))b[key].reverse();const changed=validateRecord(b);assert.deepEqual(changed.candidates,a.candidates);assert.equal(changed.label,a.label);assert.equal(changed.typedValue,a.typedValue);}
});
test('temperature applies to logits and stable softmax handles extreme finite values',()=>{
 const r=base();r.candidate_keys=['a','b'];r.candidate_count=2;r.logits=[Math.log(9),0];r.temperature=2;r.reference={kind:'label',value:'a'};close(validateRecord(r).candidates[0].probability,0.75);
 r.logits=[1e308,-1e308];r.temperature=1e-308;assert.deepEqual(validateRecord(r).candidates.map(c=>c.probability),[1,0]);
});
test('ties are canonical semantic-key ordered independent of input order',()=>{
 const r=base();r.candidate_keys=['z','a'];r.candidate_count=2;r.logits=[0,0];delete r.reference;
 const a=validateRecord(r);assert.equal(a.label,'a');assert.deepEqual(a.tiedLabels,['a','z']);r.candidate_keys.reverse();assert.equal(validateRecord(r).label,'a');
});
test('duplicate physical identity is rejected atomically',()=>{const a=base(),b=clone(a);b.condition='B';rejected([a,b],'DUPLICATE_SOURCE');});
test('distinct IDs cannot alias the same declared physical source location',()=>{
 const a=base(),b=clone(syntheticRecords[1]);a.provenance={file_id:'saved.jsonl',line_1based:2,file_sha256:'a'.repeat(64)};b.provenance={...a.provenance,file_id:'renamed.jsonl'};rejected([a,b],'DUPLICATE_SOURCE_LOCATION');
 b.provenance={...a.provenance,file_sha256:'b'.repeat(64)};rejected([a,b],'DUPLICATE_SOURCE_LOCATION');
});
test('duplicate model/item condition is rejected',()=>{const a=base(),b=clone(syntheticRecords[1]);b.condition=a.condition;rejected([a,b],'DUPLICATE_CONDITION');});
test('different model/item groups cannot be compared',()=>{const a=validateRecord(base()),b=base();b.item_id='other';assert.throws(()=>compareRecords(a,validateRecord(b)),e=>e.code==='COMPARISON_SCOPE');});
test('inconsistent candidate sets reject the full file',()=>{const a=base(),b=clone(syntheticRecords[1]);b.candidate_keys[0]='unknown';rejected([a,b],'CANDIDATE_MISMATCH');});
test('inconsistent semantic schemas reject the full file',()=>{const a=base(),b=clone(syntheticRecords[1]);b.key_schema='other';rejected([a,b],'SEMANTIC_SCHEMA_MISMATCH');});
test('inconsistent Score mappings are rejected after key alignment',()=>{const a=clone(syntheticRecords[4]),b=clone(syntheticRecords[5]);b.score_values[0]=11;rejected([a,b],'SCORE_MAPPING_MISMATCH');});
test('inconsistent references are rejected; missing references remain unknown',()=>{
 const a=base(),b=clone(syntheticRecords[1]);b.reference.value='green';rejected([a,b],'REFERENCE_MISMATCH');delete b.reference;const result=parseJSONL(lines([a,b]));assert.equal(result.ok,true);assert.equal(compareRecords(...result.records).reference,null);
});
test('same-record comparison counts a shared identity once',()=>{const a=validateRecord(base()),c=compareRecords(a,a);assert.equal(c.declared_physical_identities.unique,1);assert.equal(c.declared_physical_identities.shared,1);assert.equal(c.source_records.length,1);});
test('malformed JSON and mixed valid/invalid files never produce partial comparisons',()=>{const x=parseJSONL(lines([base()])+'\n{broken');assert.equal(x.ok,false);assert.equal(x.errors[0].line,2);assert.deepEqual(x.records,[]);assert.deepEqual(x.groups,[]);});
test('blank lines and UTF-8 BOM accepted; empty file and array rejected',()=>{assert.equal(parseJSONL('\uFEFF\n'+syntheticJSONL+'\n').ok,true);assert.equal(parseJSONL(' \n').errors[0].code,'EMPTY');assert.equal(parseJSONL('[]').errors[0].code,'OBJECT');});
test('unsafe strings are treated as data; prototype-like semantic keys remain safe',()=>{
 const r=base();r.model='<img src=x onerror=alert(1)>';r.candidate_keys=['__proto__','constructor','<script>bad</script>'];delete r.reference;const result=parseJSONL(lines([r]));assert.equal(result.ok,true);assert.equal(result.records[0].raw.model,r.model);assert.equal({}.polluted,undefined);
 const app=readFileSync(new URL('../docs/explorer/import/app.mjs',import.meta.url),'utf8');assert.equal(/innerHTML|outerHTML|insertAdjacentHTML|eval\(|fetch\(|XMLHttpRequest|localStorage|sessionStorage|sendBeacon/.test(app),false);
 const html=readFileSync(new URL('../docs/explorer/import/index.html',import.meta.url),'utf8');assert.ok(html.includes("connect-src 'none'"));
});
for(const [name,change,code] of [
 ['wrong schema',r=>r.schema_version=2,'SCHEMA'],['derived observation',r=>r.kind='derived','SCHEMA'],
 ['unknown field',r=>r.member_ids=['x'],'UNKNOWN_FIELD'],['invalid source identity',r=>r.source_id='<script>','SOURCE_ID'],
 ['duplicate candidate',r=>r.candidate_keys[1]=r.candidate_keys[0],'CANDIDATES'],['empty key',r=>r.candidate_keys[1]='','CANDIDATES'],
 ['missing declared candidate count',r=>delete r.candidate_count,'CANDIDATE_COUNT'],['declared-full length mismatch',r=>r.candidate_count=4,'CANDIDATE_COUNT'],
 ['top-k scope',r=>r.distribution_scope='top_k','INCOMPLETE_DISTRIBUTION'],['both distribution representations',r=>r.probabilities=[0.5,0.3,0.2],'DISTRIBUTION'],
 ['missing distribution',r=>delete r.logits,'DISTRIBUTION'],['NaN logit',r=>r.logits[0]=NaN,'LOGITS'],['infinite logit',r=>r.logits[0]=Infinity,'LOGITS'],
 ['string logit',r=>r.logits[0]='4','LOGITS'],['wrong vector length',r=>r.logits.pop(),'LOGITS'],['zero temperature',r=>r.temperature=0,'TEMPERATURE'],
 ['negative temperature',r=>r.temperature=-1,'TEMPERATURE'],['nonfinite temperature',r=>r.temperature=Infinity,'TEMPERATURE'],
 ['unused probability metadata',r=>r.probability_origin='reported_probabilities','MIXED_ORIGIN'],['invalid reference',r=>r.reference.value='missing','REFERENCE'],
 ['negative latency',r=>r.recorded_latency_ms=-1,'LATENCY'],['malformed provenance line',r=>r.provenance={file_id:'a',line_1based:0},'PROVENANCE'],
 ['malformed provenance hash',r=>r.provenance={file_id:'a',line_1based:1,file_sha256:'not-hash'},'PROVENANCE_HASH'],
 ['score field on choice',r=>r.score_values=[0,1,2],'UNUSED_SCORE_VALUES']
])test(name,()=>invalid(change,code));
for(const [name,change,code] of [
 ['missing probability origin',r=>delete r.probability_origin,'PROBABILITY_ORIGIN'],
 ['wrong probability semantics',r=>r.probability_semantics='probability_correct','PROBABILITY_SEMANTICS'],
 ['incomplete mass',r=>r.probabilities=[0.1,0.2],'PROBABILITY_SUM'],
 ['invalid probability range',r=>r.probabilities=[1.1,-0.1],'PROBABILITIES'],
 ['nonfinite probability',r=>r.probabilities=[NaN,1],'PROBABILITIES'],
 ['probabilities with temperature',r=>r.temperature=1,'UNUSED_TEMPERATURE'],
 ['Noul semantic mismatch',r=>r.candidate_keys=['yes','no'],'NOUL_KEYS']
])test(name,()=>{const r=clone(syntheticRecords[2]);change(r);assert.throws(()=>validateRecord(r),e=>e.code===code);});
test('JSON numeric overflow is caught as nonfinite instead of silently accepted',()=>{const r=JSON.stringify(base()).replace('1.3862943611198906','1e999');assert.equal(parseJSONL(r).ok,false);});
test('probabilities within sum tolerance are preserved, not silently renormalized',()=>{const r=clone(syntheticRecords[2]);r.probabilities=[0.75,0.250000001];const v=validateRecord(r);assert.equal(v.candidates[1].probability,0.250000001);});
test('single condition warning, unknown cost and reference never become zero or correctness',()=>{const r=clone(syntheticRecords[2]);const result=parseJSONL(lines([r]));assert.ok(result.warnings.some(w=>w.code==='ONE_CONDITION'));assert.equal(result.records[0].reference,null);assert.equal(result.records[0].recordedLatencyMs,null);});
test('hash-selected archived projection equals the unchanged published values',()=>{
 const here=new URL('../docs/explorer/import/',import.meta.url),bytes=readFileSync(new URL('archived-projection.jsonl',here)),manifest=JSON.parse(readFileSync(new URL('archived-projection.manifest.json',here)));
 const sha=x=>createHash('sha256').update(x).digest('hex');assert.equal(sha(bytes),manifest.projection_sha256);
 const data=new URL('../data/',here),indexBytes=readFileSync(new URL('index.json',data));assert.equal(sha(indexBytes),manifest.index_sha256);
 const index=JSON.parse(indexBytes),choices=[];
 for(const desc of index.panels){const panelBytes=readFileSync(new URL(desc.path,data));assert.equal(sha(panelBytes),desc.sha256);const panel=JSON.parse(panelBytes);for(const item of panel.items)if(item.variants.filter(v=>v.kind==='physical').length>=2)choices.push({hash:sha(JSON.stringify([desc.id,item.item_id])),panelId:desc.id,itemId:item.item_id});}
 choices.sort((a,b)=>a.hash.localeCompare(b.hash));assert.equal(choices.length,manifest.eligible_model_item_groups);assert.equal(choices[0].hash,manifest.selection_hash);assert.equal(choices[0].panelId,manifest.panel_id);assert.equal(choices[0].itemId,manifest.item_id);
 const panelBytes=readFileSync(new URL(manifest.panel_path,data));assert.equal(sha(panelBytes),manifest.panel_sha256);const panel=JSON.parse(panelBytes),item=panel.items.find(x=>x.item_id===manifest.item_id);
 const result=parseJSONL(bytes.toString());assert.equal(result.ok,true);assert.equal(result.records.length,manifest.conditions.length);
 for(const r of result.records){const v=item.variants.find(v=>v.id===r.raw.condition);assert.equal(r.label,v.label);if(v.value!==undefined)close(r.typedValue,v.value);for(const c of r.candidates)assert.equal(c.probability,v.probabilities[panel.canonical_keys.indexOf(c.key)]);assert.equal(r.raw.provenance.line_1based,v.source[1]);assert.equal(r.raw.provenance.file_sha256,index.sources[v.source[0]].sha256);}
});

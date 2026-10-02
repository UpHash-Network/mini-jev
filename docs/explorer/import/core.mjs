// Local physical-record importer. No browser storage, networking, or inference.
export const LIMITS = Object.freeze({bytes: 25 * 1024 * 1024, records: 20000, candidates: 256});
const has = (o, k) => Object.hasOwn(o, k);
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const fail = (code, message) => { const e = new Error(message); e.code = code; throw e; };
const requireThat = (ok, code, message) => { if (!ok) fail(code, message); };
const text = (x, max = 256) => typeof x === 'string' && x.length > 0 && x.length <= max && x.trim() === x && !/[\u0000-\u001f\u007f]/.test(x);
const finite = x => typeof x === 'number' && Number.isFinite(x);
const sourceId = x => typeof x === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:/#-]{0,255}$/.test(x);
const sameSet = (a,b) => a.length === b.length && a.every(k => b.includes(k));
const fields = new Set(['schema_version','kind','model','item_id','type','condition','source_id','key_schema','candidate_keys','candidate_count','distribution_scope','logits','temperature','probabilities','probability_semantics','probability_origin','score_values','reference','recorded_latency_ms','provenance','note']);

export function validateRecord(r, line = 1) {
  requireThat(object(r), 'OBJECT', 'Each JSONL line must be one record object.');
  requireThat(Object.keys(r).every(k => fields.has(k)), 'UNKNOWN_FIELD', 'Unknown field; use only the documented physical-record v1 fields.');
  requireThat(r.schema_version === 1 && r.kind === 'physical', 'SCHEMA', 'schema_version must be 1 and kind must be physical; derived recipes are not supported.');
  for (const k of ['model','item_id','condition','key_schema']) requireThat(text(r[k]), 'IDENTIFIER', `${k} must be a nonempty string (maximum 256 characters, no control characters).`);
  requireThat(sourceId(r.source_id), 'SOURCE_ID', 'source_id must be a stable ASCII identity (letters, numbers, . _ : / # -), maximum 256 characters.');
  requireThat(['choice','noul','score'].includes(r.type), 'TYPE', 'type must be choice, noul, or score.');
  const keys = r.candidate_keys;
  requireThat(Array.isArray(keys) && keys.length >= 2 && keys.length <= LIMITS.candidates && keys.every(k => text(k)) && new Set(keys).size === keys.length, 'CANDIDATES', 'candidate_keys must contain 2–256 unique semantic strings.');
  requireThat(Number.isInteger(r.candidate_count) && r.candidate_count === keys.length, 'CANDIDATE_COUNT', 'candidate_count must equal the full candidate_keys length.');
  requireThat(r.distribution_scope === 'full_candidate_set', 'INCOMPLETE_DISTRIBUTION', 'Only a declared full candidate set is supported; incomplete/top-k distributions are rejected.');
  requireThat(has(r,'logits') !== has(r,'probabilities'), 'DISTRIBUTION', 'Provide exactly one of logits or probabilities.');
  let probabilities, origin;
  if (has(r,'logits')) {
    requireThat(Array.isArray(r.logits) && r.logits.length === keys.length && r.logits.every(finite), 'LOGITS', 'logits must be finite numbers, one per candidate.');
    requireThat(finite(r.temperature) && r.temperature > 0, 'TEMPERATURE', 'temperature must be a finite positive number.');
    requireThat(!has(r,'probability_origin') && !has(r,'probability_semantics'), 'MIXED_ORIGIN', 'Probability-only metadata must not accompany logits.');
    const maximum = Math.max(...r.logits);
    const exp = r.logits.map(x => Math.exp((x - maximum) / r.temperature));
    const sum = exp.reduce((a,b) => a+b, 0);
    probabilities = exp.map(x => x / sum);
    origin = 'softmax_of_supplied_logits';
  } else {
    requireThat(!has(r,'temperature'), 'UNUSED_TEMPERATURE', 'Temperature is only used with logits; probabilities are not rescaled.');
    requireThat(r.probability_semantics === 'conditional_on_candidate_set', 'PROBABILITY_SEMANTICS', 'probability_semantics must be conditional_on_candidate_set; correctness probabilities are unsupported.');
    requireThat(['reported_probabilities','renormalized_candidate_scores'].includes(r.probability_origin), 'PROBABILITY_ORIGIN', 'Declare probability_origin as reported_probabilities or renormalized_candidate_scores.');
    requireThat(Array.isArray(r.probabilities) && r.probabilities.length === keys.length && r.probabilities.every(p => finite(p) && p >= 0 && p <= 1), 'PROBABILITIES', 'probabilities must be finite numbers in [0,1], one per candidate.');
    const sum = r.probabilities.reduce((a,b) => a+b, 0);
    requireThat(Math.abs(sum-1) <= 1e-8, 'PROBABILITY_SUM', 'Full candidate probabilities must sum to 1 within 1e-8; the importer does not renormalize them.');
    probabilities = [...r.probabilities];
    origin = r.probability_origin;
  }
  if (r.type === 'noul') requireThat(sameSet(keys,['false','true']), 'NOUL_KEYS', 'Noul uses the literal semantic keys false and true.');
  if (r.type === 'score') requireThat(Array.isArray(r.score_values) && r.score_values.length === keys.length && r.score_values.every(finite), 'SCORE_VALUES', 'Score requires a finite score_values array aligned with candidate_keys.');
  else requireThat(!has(r,'score_values'), 'UNUSED_SCORE_VALUES', 'score_values is only valid for type score.');
  if (has(r,'reference')) {
    const v = r.reference;
    requireThat(object(v) && Object.keys(v).length === 2 && has(v,'kind') && has(v,'value'), 'REFERENCE', 'reference must contain exactly kind and value.');
    requireThat((v.kind === 'label' && keys.includes(v.value)) || (r.type === 'score' && v.kind === 'score' && finite(v.value)), 'REFERENCE', 'A reference must be a known label, or a finite continuous value for Score.');
  }
  if (has(r,'recorded_latency_ms')) requireThat(finite(r.recorded_latency_ms) && r.recorded_latency_ms >= 0, 'LATENCY', 'recorded_latency_ms must be finite and nonnegative; omit unknown latency.');
  if (has(r,'provenance')) {
    const p = r.provenance;
    requireThat(object(p) && Object.keys(p).every(k => ['file_id','line_1based','file_sha256'].includes(k)) && text(p.file_id,1024) && Number.isSafeInteger(p.line_1based) && p.line_1based > 0, 'PROVENANCE', 'provenance needs file_id and positive line_1based; optional file_sha256 is 64 lowercase hex characters.');
    requireThat(!has(p,'file_sha256') || (typeof p.file_sha256 === 'string' && /^[a-f0-9]{64}$/.test(p.file_sha256)), 'PROVENANCE_HASH', 'file_sha256 must contain 64 lowercase hex characters.');
  }
  if (has(r,'note')) requireThat(text(r.note,4096), 'NOTE', 'note must be a string of at most 4096 characters without control characters.');
  // Canonical lexical ordering makes ties invariant to presentation order.
  const candidates = keys.map((key,i) => ({key,probability:probabilities[i],...(r.type === 'score' ? {score:r.score_values[i]} : {})})).sort((a,b) => a.key < b.key ? -1 : a.key > b.key ? 1 : 0);
  const max = Math.max(...candidates.map(c => c.probability));
  const tiedLabels = candidates.filter(c => c.probability === max).map(c => c.key);
  const typedValue = r.type === 'noul' ? candidates.find(c => c.key === 'true').probability : r.type === 'score' ? candidates.reduce((s,c) => s+c.score*c.probability,0) : null;
  requireThat(typedValue === null || Number.isFinite(typedValue), 'TYPED_OVERFLOW', 'The typed expectation is not finite; check supplied score scale.');
  if (r.reference?.kind === 'score') requireThat(Number.isFinite(Math.abs(typedValue-r.reference.value)), 'REFERENCE_OVERFLOW', 'Reference error overflows the numeric range; check the score scale.');
  return {line,raw:r,candidates,label:tiedLabels[0],tiedLabels,typedValue,origin,reference:r.reference ?? null,recordedLatencyMs:r.recorded_latency_ms ?? null};
}

export function parseJSONL(input) {
  const errors=[], warnings=[], records=[];
  if (typeof input !== 'string' || new TextEncoder().encode(input).length > LIMITS.bytes) return {ok:false,errors:[{line:null,code:'SIZE',message:'Use a UTF-8 JSONL file no larger than 25 MiB.'}],warnings,records:[],groups:[]};
  const lines=input.replace(/^\uFEFF/,'').split(/\r?\n/), groups = new Map(), sources = new Map(), sourceLocations = new Map();
  let nonempty=0;
  for (let i=0;i<lines.length;i++) {
    if (!lines[i].trim()) continue;
    if (++nonempty > LIMITS.records) {errors.push({line:i+1,code:'RECORD_LIMIT',message:'At most 20,000 physical records are supported.'});break;}
    try {
      const record=validateRecord(JSON.parse(lines[i]),i+1), r=record.raw;
      requireThat(!sources.has(r.source_id),'DUPLICATE_SOURCE',`source_id duplicates line ${sources.get(r.source_id)}; one imported record must represent one physical observation.`);
      sources.set(r.source_id,i+1);
      if (r.provenance) {
        const p=r.provenance, locations=[JSON.stringify(['file',p.file_id,p.line_1based])];
        if(p.file_sha256) locations.push(JSON.stringify(['sha256',p.file_sha256,p.line_1based]));
        for (const location of locations) requireThat(!sourceLocations.has(location),'DUPLICATE_SOURCE_LOCATION',`Provenance aliases the physical record on line ${sourceLocations.get(location)}.`);
        for (const location of locations) sourceLocations.set(location,i+1);
      }
      const key=JSON.stringify([r.model,r.item_id]);
      if (!groups.has(key)) groups.set(key,{key,model:r.model,itemId:r.item_id,type:r.type,keySchema:r.key_schema,records:[]});
      const group=groups.get(key), first=group.records[0];
      if (first) {
        requireThat(group.type===r.type && group.keySchema===r.key_schema,'SEMANTIC_SCHEMA_MISMATCH','Same model/item records must share type and key_schema.');
        requireThat(sameSet(first.raw.candidate_keys,r.candidate_keys),'CANDIDATE_MISMATCH','Same model/item records have inconsistent semantic candidate sets.');
        requireThat(!group.records.some(x=>x.raw.condition===r.condition),'DUPLICATE_CONDITION','Same model/item condition appears more than once.');
        if (r.type==='score') requireThat(first.candidates.every((c,j)=>c.score===record.candidates[j].score),'SCORE_MAPPING_MISMATCH','Score values for the same semantic key must agree across conditions.');
        const previousRef=group.records.find(x=>x.reference)?.reference;
        if (previousRef && record.reference) requireThat(previousRef.kind===record.reference.kind && previousRef.value===record.reference.value,'REFERENCE_MISMATCH','References disagree for the same model/item.');
      }
      group.records.push(record);records.push(record);
      if (!record.reference) warnings.push({line:i+1,code:'UNKNOWN_REFERENCE',message:'Reference is unknown; no correctness claim is available for this record.'});
      if (record.recordedLatencyMs===null) warnings.push({line:i+1,code:'UNKNOWN_LATENCY',message:'Recorded latency is unknown; no zero-cost assumption is made.'});
      if (record.origin==='renormalized_candidate_scores') warnings.push({line:i+1,code:'RENORMALIZED_ORIGIN',message:'The producer reports renormalized candidate scores; these are not verified original model probabilities.'});
      if (record.tiedLabels.length>1) warnings.push({line:i+1,code:'TIED_LABEL',message:'Exact argmax tie; display uses the lexically first semantic key.'});
    } catch (error) {errors.push({line:i+1,code:error.code ?? 'JSON',message:error.code ? error.message : 'Malformed JSON. Use one complete JSON object per line.'});}
  }
  if (!nonempty) errors.push({line:null,code:'EMPTY',message:'No JSONL records found.'});
  // Fail closed: a partial parse never becomes an apparently complete comparison.
  if (errors.length) return {ok:false,errors,warnings,records:[],groups:[]};
  for (const group of groups.values()) if (group.records.length<2) warnings.push({line:group.records[0].line,code:'ONE_CONDITION',message:'This model/item has only one condition; a distinct A/B comparison is unavailable.'});
  return {ok:true,errors,warnings,records,groups:[...groups.values()]};
}

export function compareRecords(a,b) {
  const x=a.raw,y=b.raw;
  requireThat(x.model===y.model && x.item_id===y.item_id && x.type===y.type && x.key_schema===y.key_schema && sameSet(x.candidate_keys,y.candidate_keys),'COMPARISON_SCOPE','Choose records sharing model, item, type, semantic schema, and candidate set.');
  requireThat(x.type!=='score' || a.candidates.every((c,i)=>c.score===b.candidates[i].score),'SCORE_MAPPING_MISMATCH','Score mappings must agree.');
  let reference=null;
  if (a.reference && b.reference) {
    requireThat(a.reference.kind===b.reference.kind && a.reference.value===b.reference.value,'REFERENCE_MISMATCH','References must agree.');
    reference=a.reference.kind==='score' ? {...a.reference,aAbsoluteError:Math.abs(a.typedValue-a.reference.value),bAbsoluteError:Math.abs(b.typedValue-b.reference.value)} : {...a.reference,aMatches:a.label===a.reference.value,bMatches:b.label===b.reference.value};
  }
  return {schema_version:1,mode:'local_user_supplied_physical_records',new_inference_calls:0,model:x.model,item_id:x.item_id,type:x.type,key_schema:x.key_schema,
    a:{source_id:x.source_id,condition:x.condition,label:a.label,tied_labels:a.tiedLabels,typed_value:a.typedValue,origin:a.origin,recorded_latency_ms:a.recordedLatencyMs},
    b:{source_id:y.source_id,condition:y.condition,label:b.label,tied_labels:b.tiedLabels,typed_value:b.typedValue,origin:b.origin,recorded_latency_ms:b.recordedLatencyMs},
    label_changed:a.label!==b.label,reference,
    candidates:a.candidates.map((c,i)=>({key:c.key,a:c.probability,b:b.candidates[i].probability,delta:b.candidates[i].probability-c.probability,...(x.type==='score'?{score:c.score}:{})})),
    declared_physical_identities:{shared:x.source_id===y.source_id?1:0,unique:x.source_id===y.source_id?1:2,verified_against_external_source:false},
    source_records:x.source_id===y.source_id?[x]:[x,y],
    limitations:['All source identities, semantics, provenance, and references are supplied by the file author; source authenticity is not verified.','Full means the declared candidate set, not the whole model vocabulary. Omitted candidates cannot be detected if falsely declared complete.','Candidate probabilities and label matches are not calibrated correctness probabilities.','Missing latency or reference remains unknown. No model inference or human evaluation was performed.','This v1 accepts individual physical records; derived or shared-member recipes are unsupported.']};
}

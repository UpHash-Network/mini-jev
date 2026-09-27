// Pure comparison arithmetic. All vectors are already aligned to semantic keys.
export function validatePanel(panel) {
  if (!Array.isArray(panel.items) || !Array.isArray(panel.canonical_keys) || panel.canonical_keys.length < 2) throw new Error('Invalid evidence panel.');
  const keys = panel.canonical_keys;
  if (new Set(keys).size !== keys.length) throw new Error('Duplicate semantic candidate keys.');
  const items = new Set();
  for (const item of panel.items) {
    if (items.has(item.item_id)) throw new Error('Duplicate source item.');
    items.add(item.item_id);
    if (!Array.isArray(item.variants) || !item.variants.length) throw new Error('Missing recorded conditions.');
    const ids = new Set();
    for (const v of item.variants) {
      if (ids.has(v.id)) throw new Error('Duplicate condition.');
      ids.add(v.id);
      if (!Array.isArray(v.probabilities) || v.probabilities.length !== keys.length || v.probabilities.some(p => !Number.isFinite(p) || p < 0 || p > 1)) throw new Error('Invalid candidate probabilities.');
      if (Math.abs(v.probabilities.reduce((a,b) => a+b, 0) - 1) > 1e-8) throw new Error('Candidate probabilities do not sum to one.');
      if (!keys.includes(v.label)) throw new Error('Unknown semantic answer key.');
      if (!['physical','derived'].includes(v.kind)) throw new Error('Unknown observation kind.');
      if (v.kind==='physical' && (!Array.isArray(v.source)||v.source.length!==2||typeof v.source[0]!=='string'||!Number.isInteger(v.source[1])||v.source[1]<1)) throw new Error('Missing original source line.');
      if (!Number.isInteger(v.calls) || v.calls < 1) throw new Error('Invalid recorded call count.');
      if (!Number.isFinite(v.concentration) || v.concentration < -1e-10 || v.concentration > 1+1e-10) throw new Error('Invalid concentration.');
      if (['score','noul'].includes(panel.type) && !Number.isFinite(v.value)) throw new Error('Missing typed value.');
    }
    for (const v of item.variants) {
      if (v.kind === 'derived' && (!v.member_ids?.length || v.member_ids.some(id => !ids.has(id)))) throw new Error('Missing source condition for average.');
      if (new Set(physicalMembers(item,v).map(m=>JSON.stringify(m.source))).size!==v.calls) throw new Error('Call count does not match distinct physical observations.');
    }
  }
  return panel;
}

export function physicalMembers(item, variant) {
  if (variant.kind !== 'derived') return [variant];
  const map = new Map(item.variants.map(v => [v.id,v]));
  return variant.member_ids.map(id => {
    const v=map.get(id);
    if (!v || v.kind === 'derived') throw new Error('Invalid physical averaging member.');
    return v;
  });
}

export function compare(panel, item, a, b) {
  if (!panel.items.includes(item) || !item.variants.includes(a) || !item.variants.includes(b)) throw new Error('Comparisons must share one panel and source item.');
  const aMembers=physicalMembers(item,a), bMembers=physicalMembers(item,b);
  const identity=v=>JSON.stringify(v.source);
  const aSet=new Set(aMembers.map(identity)), bSet=new Set(bMembers.map(identity));
  const shared=[...aSet].filter(id=>bSet.has(id)).length;
  const reference=Number.isFinite(item.gold_score) ? {kind:'continuous',value:item.gold_score,aError:Math.abs(a.value-item.gold_score),bError:Math.abs(b.value-item.gold_score)} : item.gold_label != null ? {kind:'label',value:item.gold_label,aMatch:a.label===item.gold_label,bMatch:b.label===item.gold_label} : null;
  return {
    labelChanged:a.label!==b.label,
    maxProbabilityDifference:Math.max(...a.probabilities.map((p,i)=>Math.abs(b.probabilities[i]-p))),
    candidates:panel.canonical_keys.map((key,i)=>({key,a:a.probabilities[i],b:b.probabilities[i],delta:b.probabilities[i]-a.probabilities[i]})),
    reference,
    aMembers,bMembers,sharedPhysicalCalls:shared,uniquePhysicalCalls:new Set([...aSet,...bSet]).size,
    samePhysicalPool:aSet.size===bSet.size && shared===aSet.size,
  };
}

export function comparisonExport(index,panel,item,a,b,result,selection) {
  const model=panel.model??panel.model_metadata??index.models?.[panel.study_id]?.[panel.model_key]??null;
  const used=[...new Set([...[a,b,...result.aMembers,...result.bMembers].map(v=>v.source?.[0]),model?.source].filter(Boolean))];
  const mappingIds=[...new Set([...result.aMembers,...result.bMembers].map(v=>v.mapping).filter(Boolean))];
  return {
    schema_version:1,mode:'saved_research_records',new_inference_calls:0,
    study_id:panel.study_id,model_key:panel.model_key,dataset:panel.dataset,type:panel.type,
    item_id:item.item_id,source_question_sha256:item.source_question_sha256,split:item.split,group:item.group,
    canonical_keys:panel.canonical_keys,score_values:panel.score_values??null,
    reference:result.reference,conditions:{a,b},physical_members:[...new Map([...result.aMembers,...result.bMembers].map(v=>[JSON.stringify(v.source),v])).values()],
    candidate_comparison:result.candidates,shared_physical_calls:result.sharedPhysicalCalls,unique_physical_calls:result.uniquePhysicalCalls,
    sources:Object.fromEntries(used.map(id=>[id,index.sources[id]])),
    mappings:Object.fromEntries(mappingIds.map(id=>[id,index.mappings[id]])),
    archive:index.archive??index.bundle??null,model,
    selection,limitations:['Recorded-data inspection, not new inference or a human usability study.','Candidate probabilities are conditional on the supplied set, not correctness probabilities.','Continuous reference scores are not rounded into labels.','Calls shared by conditions are counted once in the union.','Source task text is not distributed in this artifact.'],
  };
}

export function panelFrequencies(panel,condition) {
  const counts=Object.fromEntries(panel.canonical_keys.map(k=>[k,0]));
  let n=0;
  for(const item of panel.items){const v=item.variants.find(v=>v.id===condition);if(v){counts[v.label]++;n++;}}
  return {items:n,label_counts:counts};
}

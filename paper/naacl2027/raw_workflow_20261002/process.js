// Custom ChainForge processor. Receives only projected archived logits/recipes.
// No model, network, saved answers, or existing LogitTrail comparison code.
function process(response) {
  let input;
  function requireValue(ok, code) { if (!ok) throw new Error(code); }
  function finite(x) { return typeof x === 'number' && Number.isFinite(x); }
  function sameKeys(a, b) { return Array.isArray(a) && a.length === b.length && new Set(a).size === b.length && a.every(k => b.includes(k)); }
  function sourceIdentity(s) {
    requireValue(s && typeof s.source_id === 'string' && typeof s.member === 'string' &&
      Number.isInteger(s.line_1based) && s.line_1based > 0 && /^[a-f0-9]{64}$/.test(s.member_sha256), 'source_identity');
    return s.source_id + ':' + s.line_1based;
  }
  try {
    input = JSON.parse(response.text);
    const keys = input.canonical_keys;
    requireValue(Array.isArray(keys) && keys.length >= 2 && new Set(keys).size === keys.length, 'candidate_keys');
    requireValue(['choice','noul','score'].includes(input.type), 'type');
    if (input.type === 'noul') requireValue(sameKeys(keys, ['false','true']), 'candidate_keys');
    if (input.type === 'score') requireValue(input.score_values && keys.every(k => finite(input.score_values[k])), 'score_values');
    requireValue(Array.isArray(input.physical_records) && Array.isArray(input.items), 'records');
    const physical = new Map();
    for (const record of input.physical_records) {
      const rid = sourceIdentity(record.source);
      requireValue(record.rid === rid, 'source_identity');
      requireValue(!physical.has(rid), 'duplicate_source');
      requireValue(record.model_key === input.model_key && record.dataset === input.dataset && record.type === input.type, 'record_context');
      requireValue(sameKeys(record.candidate_keys, keys) && sameKeys(record.tie_order, keys), 'candidate_keys');
      requireValue(Array.isArray(record.candidate_tokens) && record.candidate_tokens.length === keys.length, 'candidate_tokens');
      requireValue(Array.isArray(record.logits) && record.logits.length === keys.length && record.logits.every(finite), 'invalid_logits');
      requireValue(finite(record.temperature) && record.temperature > 0, 'temperature');
      requireValue(Number.isInteger(record.input_tokens) && record.input_tokens >= 0 && finite(record.latency_ms) && record.latency_ms >= 0, 'record_cost');
      const maximum = Math.max(...record.logits);
      const exp = record.logits.map(x => Math.exp((x - maximum) / record.temperature));
      const total = exp.reduce((a,b) => a+b, 0);
      const probabilities = Object.fromEntries(record.candidate_keys.map((k,i) => [k, exp[i]/total]));
      const logitByKey = Object.fromEntries(record.candidate_keys.map((k,i) => [k,record.logits[i]]));
      const label = record.tie_order.find(k => logitByKey[k] === maximum);
      physical.set(rid, {record, probabilities, label});
    }
    function answer(item, recipe) {
      requireValue(Array.isArray(recipe.member_ids) && recipe.member_ids.length > 0, 'empty_recipe');
      requireValue(new Set(recipe.member_ids).size === recipe.member_ids.length, 'duplicate_member');
      requireValue(['single','mean'].includes(recipe.operation), 'recipe_operation');
      requireValue(recipe.operation !== 'single' || recipe.member_ids.length === 1, 'single_member');
      sourceIdentity(recipe.recipe_source);
      const members = recipe.member_ids.map(rid => {
        requireValue(physical.has(rid), 'missing_member');
        const member = physical.get(rid);
        requireValue(member.record.item_id === item.item_id, 'cross_item_member');
        return member;
      });
      const probabilities = Object.fromEntries(keys.map(k => [k,members.reduce((sum,m) => sum+m.probabilities[k],0)/members.length]));
      const maxProbability = Math.max(...keys.map(k => probabilities[k]));
      const label = recipe.operation === 'single' ? members[0].label : keys.find(k => probabilities[k] === maxProbability);
      const value = input.type === 'choice' ? label : input.type === 'noul' ? probabilities.true : keys.reduce((sum,k) => sum + probabilities[k]*input.score_values[k],0);
      const entropy = -keys.reduce((sum,k) => sum + (probabilities[k] ? probabilities[k]*Math.log(probabilities[k]) : 0),0);
      return {id:recipe.id,probabilities,label,typed_value:value,concentration:Math.min(1,Math.max(0,1-entropy/Math.log(keys.length))),
        calls:members.length,member_ids:[...recipe.member_ids].sort(),
        member_sources:members.map(m => m.record.source).sort((a,b)=>sourceIdentity(a).localeCompare(sourceIdentity(b))),
        recipe_source:recipe.recipe_source,input_tokens:members.reduce((sum,m)=>sum+m.record.input_tokens,0),
        recorded_latency_sum_ms:members.reduce((sum,m)=>sum+m.record.latency_ms,0)};
    }
    const seen = new Set(), computed = [];
    for (const item of input.items) {
      requireValue(!seen.has(item.item_id), 'duplicate_item');seen.add(item.item_id);
      const a=answer(item,item.conditions.a),b=answer(item,item.conditions.b);
      const aSet=new Set(a.member_ids),bSet=new Set(b.member_ids),shared=[...aSet].filter(x=>bSet.has(x)).length;
      const reference={...item.reference};
      if (input.type === 'score') {
        requireValue(reference.kind === 'continuous' && finite(reference.value),'reference');
        reference.a_error=Math.abs(a.typed_value-reference.value);reference.b_error=Math.abs(b.typed_value-reference.value);
      } else {
        requireValue(reference.kind === 'label' && keys.includes(reference.value),'reference');
        reference.a_match=a.label===reference.value;reference.b_match=b.label===reference.value;
      }
      computed.push({item_id:item.item_id,a,b,reference,shared_physical_calls:shared,
        unique_physical_calls:new Set([...aSet,...bSet]).size,same_physical_pool:aSet.size===bSet.size&&shared===aSet.size,
        label_changed:a.label!==b.label,candidate_differences:keys.map(k=>({key:k,a:a.probabilities[k],b:b.probabilities[k],delta:b.probabilities[k]-a.probabilities[k]}))});
    }
    const selected=computed.find(x=>x.item_id===input.selected_item);requireValue(selected,'selected_item');
    const panel={items:computed.length,conditions:{}};
    for (const side of ['a','b']) {
      const values=computed.map(x=>x[side]),counts=Object.fromEntries(keys.map(k=>[k,0]));
      for(const value of values)counts[value.label]++;
      const summary={items:values.length,label_counts:counts,maximum_label_share:Math.max(...Object.values(counts))/values.length,used_labels:Object.values(counts).filter(x=>x>0).length};
      if(input.type==='score') {
        const nums=values.map(x=>x.typed_value),mean=nums.reduce((a,b)=>a+b,0)/nums.length;
        summary.value_min=Math.min(...nums);summary.value_max=Math.max(...nums);
        summary.value_population_variance=nums.reduce((sum,n)=>sum+(n-mean)**2,0)/nums.length;
      }
      panel.conditions[side]=summary;
    }
    return JSON.stringify({schema_version:1,case_id:input.case_id,status:'ok',new_model_calls:0,
      computation:'Custom JavaScript reconstruction from projected archived logits and recipes; not an unmodified built-in decision feature.',
      physical_records:physical.size,selected,panel,reconstructed_items:computed});
  } catch (error) {
    return JSON.stringify({schema_version:1,case_id:input?.case_id??null,status:'rejected',error_code:error.message});
  }
}

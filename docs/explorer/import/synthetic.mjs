// Deterministic hand-written demonstration. No model or human produced these observations.
const base = {schema_version:1,kind:'physical',model:'Synthetic demonstration — no model run',key_schema:'synthetic-semantic-keys-v1',distribution_scope:'full_candidate_set'};
const p = {probability_semantics:'conditional_on_candidate_set',probability_origin:'reported_probabilities'};
export const syntheticRecords = [
  {...base,item_id:'synthetic-choice',type:'choice',condition:'A',source_id:'synthetic:choice:a',candidate_keys:['red','green','blue'],candidate_count:3,logits:[Math.log(4),Math.log(2),0],temperature:1,reference:{kind:'label',value:'red'},note:'Clearly synthetic fixture; no measured model accuracy.'},
  {...base,item_id:'synthetic-choice',type:'choice',condition:'B',source_id:'synthetic:choice:b',candidate_keys:['blue','green','red'],candidate_count:3,logits:[0,Math.log(4),Math.log(2)],temperature:1,reference:{kind:'label',value:'red'}},
  {...base,...p,item_id:'synthetic-noul',type:'noul',condition:'A',source_id:'synthetic:noul:a',candidate_keys:['false','true'],candidate_count:2,probabilities:[0.75,0.25]},
  {...base,...p,item_id:'synthetic-noul',type:'noul',condition:'B',source_id:'synthetic:noul:b',candidate_keys:['true','false'],candidate_count:2,probabilities:[0.75,0.25]},
  {...base,...p,item_id:'synthetic-score',type:'score',condition:'A',source_id:'synthetic:score:a',candidate_keys:['low','middle','high'],candidate_count:3,probabilities:[0.2,0.3,0.5],score_values:[0,5,10],reference:{kind:'score',value:6.25}},
  {...base,...p,item_id:'synthetic-score',type:'score',condition:'B',source_id:'synthetic:score:b',candidate_keys:['high','low','middle'],candidate_count:3,probabilities:[0.3,0.2,0.5],score_values:[10,0,5],reference:{kind:'score',value:6.25},probability_origin:'renormalized_candidate_scores'},
];
export const syntheticJSONL = syntheticRecords.map(r => JSON.stringify(r)).join('\n')+'\n';

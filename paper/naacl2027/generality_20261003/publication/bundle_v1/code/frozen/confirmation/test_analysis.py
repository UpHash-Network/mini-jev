"""Analytical controls for paid routing and strict physical-pool validation."""
import copy
import json
import math
from pathlib import Path
import unittest
import analyze as a

P=json.loads((Path(__file__).parent/'PROTOCOL.json').read_text())

def fixture(n=24):
    result=[];keys=['option_'+str(i) for i in range(5)]
    for i in range(n):
        for j in range(5):
            result.append({'item_id':str(i),'request_index':i*5+j,'replicate':j,'error':None,
                'model_key':'synthetic','dataset':'JCommonsenseQA','type':'choice','method':'fixed_cyclic',
                'anchor':'canonical','backend':'transformers','forward_calls':1,'output_tokens':0,
                'canonical_keys':keys,'candidate_keys':keys,'temperature':1.0,'logits':[math.log(x) for x in [.5,.2,.1,.1,.1]],'gold_label':keys[i%2],'group':str(i),
                'source_question_sha256':str(i),'probabilities':dict(zip(keys,[.5,.2,.1,.1,.1])),
                'label':keys[0],'request_sha256':str(i*5+j),'input_tokens':10+j,'latency_ms':j+1.0})
    return result

class Tests(unittest.TestCase):
    def setUp(self):
        self.rows=fixture();self.records=a.records_from_rows(self.rows,'synthetic',24)

    def test_metrics_exact_controls(self):
        a.metric.check_metrics()

    def test_every_budget_pays_exact_physical_union(self):
        # Twenty-four permits exact allocations for all prespecified fractions.
        for policy in a.POLICIES:
            for budget in P['B']['budgets_calls_per_item']:
                r=a.replay(self.records,policy,budget,P['B'])
                self.assertEqual(r['calls'],budget*24)
                self.assertEqual(sum(x['calls'] for x in r['outcomes']),r['calls'])
                self.assertEqual(sum(len(x['paid_request_indices']) for x in r['outcomes']),r['calls'])
                expected_tokens=sum(sum(10+j for j in range(x['calls'])) for x in r['outcomes'])
                self.assertEqual(r['input_tokens'],expected_tokens)

    def test_future_and_gold_cannot_change_gate(self):
        modified=copy.deepcopy(self.records)
        for r in modified:
            r['gold_label']='changed';r['full_mean_label']='changed'
            r['probability_vectors'][2:]=[[0,0,0,0,1]]*3
            r['members'][2:]=[]
        for policy in a.POLICIES:
            self.assertEqual(a.allocation(self.records,policy,3,P['B']),a.allocation(modified,policy,3,P['B']))

    def test_first_policy_never_reads_pair_scores(self):
        only=[{'item_id':r['item_id'],'scores':{'first_entropy':r['scores']['first_entropy']}} for r in self.records]
        self.assertEqual(a.allocation(self.records,'first_entropy',3,P['B']),a.allocation(only,'first_entropy',3,P['B']))

    def test_ties_and_random_independent_of_input_order(self):
        for policy in a.POLICIES:
            self.assertEqual(a.allocation(self.records,policy,3,P['B']),a.allocation(list(reversed(self.records)),policy,3,P['B']))

    def test_pool_failure_is_not_silently_dropped(self):
        for mutate in ('missing','duplicate','nan','normalization','error','group','counter','index','temperature','logits','mapping'):
            rows=copy.deepcopy(self.rows)
            if mutate=='missing':rows.pop()
            if mutate=='duplicate':rows[-1]=copy.deepcopy(rows[0])
            if mutate=='nan':rows[0]['probabilities']['option_0']=float('nan')
            if mutate=='normalization':rows[0]['probabilities']['option_0']=.6
            if mutate=='error':rows[0]['error']='failure'
            if mutate=='group':rows[1]['group']='other'
            if mutate=='counter':rows[0]['forward_calls']=2
            if mutate=='index':rows[0]['request_index']=10000
            if mutate=='temperature':rows[0]['temperature']=2
            if mutate=='logits':rows[0]['logits'][0]+=1
            if mutate=='mapping':rows[0]['candidate_keys']=list(reversed(rows[0]['candidate_keys']))
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):
                a.records_from_rows(rows,'synthetic',24)

    def test_native_counter_alternative(self):
        for r in self.rows:
            r['backend']='llama.cpp';r['native_decode_count']=1;r['state_cleared']=True
            del r['forward_calls']
        self.assertEqual(a.records_from_rows(self.rows,'synthetic',24),self.records)

    def test_endpoint_has_all_members(self):
        for policy in a.POLICIES:
            r=a.replay(self.records,policy,5,P['B'])
            self.assertEqual(r['selected_count'],24)
            self.assertEqual(r['input_tokens'],1440)
            self.assertEqual(r['recorded_serial_latency_ms'],360)
            self.assertEqual(r['accuracy'],.5)

    def test_infeasible_budget_rejected(self):
        with self.assertRaises(ValueError):
            a.allocation(self.records,'pair_mean_entropy',2.1,P['B'])

    def test_schedule_rejects_coherent_but_different_pool(self):
        schedule=[{k:r[k] for k in ('request_index','item_id','request_sha256','source_question_sha256','gold_label','replicate')} for r in self.rows]
        a.verify_schedule(self.rows,schedule)
        changed=copy.deepcopy(self.rows)
        for r in changed[:5]:r['item_id']='other'
        with self.assertRaises(ValueError):a.verify_schedule(changed,schedule)
        with self.assertRaises(ValueError):a.verify_schedule(list(reversed(self.rows)),schedule)

if __name__=='__main__':unittest.main()

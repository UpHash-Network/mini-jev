import http.client
import unittest
from collections import Counter
import run_study as study


class StudyTests(unittest.TestCase):
    def test_gold_never_enters_question(self):
        row={'type':'choice','state':'state','instructions':'choose','criteria':{'a':'first','b':'second'},
             'label':'SECRET_GOLD','gold_score':2.9,'group':'SECRET_GROUP'}
        self.assertNotIn('SECRET',study.canonical(study.question(row)))

    def test_primary_requests_are_identical_except_mode(self):
        for q in [
            {'type':'choice','state':'s','instructions':'q','criteria':{'b':'b','a':'a'}},
            {'type':'score','state':'s','instructions':'q','criteria':['low','medium','high']},
            {'type':'noul','state':'s','instructions':'q','criteria':{'true':'yes','false':'no'}},
        ]:
            a,ak=study.native_request(q,'direct',9)
            b,bk=study.native_request(q,'one_token',9)
            a.pop('mode');b.pop('mode')
            self.assertEqual(a,b);self.assertEqual(ak,bk)

    def test_json_has_no_prefilled_prefix(self):
        q={'type':'score','state':'s','instructions':'q','criteria':['low','medium','high']}
        a,_=study.native_request(q,'direct',1);b,_=study.native_request(q,'json',1)
        self.assertEqual(a['assistant_prefix'],'{"answer":')
        self.assertNotIn('assistant_prefix',b)
        self.assertEqual(a['messages'],b['messages'])
        self.assertEqual(b['json_value_kind'],'number')

    def test_local_selection_contains_each_generated_family(self):
        rows=study.local_sample()
        self.assertEqual(len(rows),150)
        self.assertEqual(Counter(r['type'] for r in rows),{'choice':50,'noul':50,'score':50})
        groups=Counter(r['group'] for r in rows if r['source']=='generated')
        self.assertEqual(len(groups),45);self.assertEqual(set(groups.values()),{3})

    def test_schedule_keeps_all_paired_repetitions(self):
        local=study.local_sample()
        external=[{'id':'ext'+str(i),'dataset':'external'} for i in range(600)]
        schedule=study.schedule(local+external)
        self.assertEqual(schedule,study.schedule(local+external))
        self.assertEqual(len(schedule),4050)
        by_id=Counter(x['id'] for x in schedule)
        self.assertEqual({by_id[x['id']] for x in local},{15})
        self.assertEqual({by_id[x['id']] for x in external},{3})
        groups=Counter((x['id'],x['repetition'],x['mode']) for x in schedule)
        self.assertEqual(set(groups.values()),{1})

    def test_http_public_schema_equal_for_three_modes(self):
        class FakeResident:
            def call(self,request):
                return {'id':request['id'],'label_index':1,'mode':request['mode'],'logits':[0.,1.]}
        audits={};server,worker=study.serve(FakeResident(),audits)
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
        q={'type':'choice','state':'s','instructions':'q','criteria':{'a':'a','b':'b'}}
        try:
            for i,mode in enumerate(study.MODES):
                answer,status,ms,_=study.invoke(connection,q,mode,i)
                self.assertEqual(answer,{'type':'choice','label':'b'});self.assertEqual(status,200)
                self.assertGreater(ms,0)
                self.assertEqual(audits[i]['native']['logits'],[0.,1.])
                self.assertNotIn('logits',answer)
        finally:
            connection.close();server.shutdown();server.server_close();worker.join()


if __name__=='__main__':unittest.main()

"""Offline infrastructure checks. Scripted replies are NOT LLM results."""
import json
import tempfile
import unittest
from pathlib import Path
from advanced.engine import Engine, validate_answer, read
from advanced.policies import single

ROOT=Path(__file__).resolve().parents[1]

class Scripted:
    def __init__(self, actions, usage=True):self.actions=iter(actions);self.usage=usage;self.requests=[]
    def complete(self,messages,max_output_tokens,seed):
        self.requests.append(messages)
        action=next(self.actions)
        return {'content':json.dumps(action),'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15} if self.usage else None,
                'model':'offline-script','id':'fixture','seconds':0}

class AdvancedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.config=read(ROOT/'advanced/config.json')
        self.folder=self.root/'M00';(self.folder/'starter/app').mkdir(parents=True)
        (self.folder/'starter/app/__init__.py').write_text('')
        (self.folder/'starter/app/api.py').write_text('def solve(data):\n    return data\n')
        (self.folder/'SPEC.md').write_text('Return twice the integer input.')
        (self.folder/'task.json').write_text(json.dumps({'id':'M00','editable_files':['app/api.py','app/__init__.py']}))
        (self.folder/'visible.json').write_text(json.dumps([{'id':'x','input':2,'expected':4}]))
        self.correct={'action':'replace_files','files':{'app/api.py':'def solve(data):\n    return 2 * data\n'}}
    def tearDown(self):self.temp.cleanup()
    def engine(self,provider,budget=1000,folder=None):
        return Engine(folder or self.folder,self.config,provider,budget,1,self.root/'out')
    def test_real_project_baseline(self):
        engine=self.engine(Scripted([self.correct,{'action':'finish'}]))
        result=engine.execute(single,{'architecture':'single'})
        self.assertEqual(result['status'],'visible_success');self.assertTrue(result['finished'])
        self.assertEqual(result['model_calls'],2);self.assertEqual(result['total_tokens_known'],30)
        self.assertIsNone(result['success'])
    def test_overbudget_reply_cannot_edit(self):
        engine=self.engine(Scripted([self.correct]),budget=10)
        result=engine.execute(single,{})
        self.assertEqual(result['status'],'budget_exhausted');self.assertEqual(result['budget_overrun'],5)
        self.assertIn('return data',engine.files()['app/api.py'])
    def test_missing_usage_cannot_create_unmetered_edit(self):
        engine=self.engine(Scripted([self.correct],usage=False));result=engine.execute(single,{})
        self.assertEqual(result['status'],'usage_error');self.assertFalse(result['usage_complete'])
        self.assertIn('return data',engine.files()['app/api.py'])
    def test_fixed_sequence_and_handoff(self):
        provider=Scripted([self.correct,{'action':'yield','message':'draft ready'},
                          {'action':'yield','message':'review: check negative input'}, {'action':'finish'}])
        engine=self.engine(provider)
        def workflow(e):
            draft=e.run_role('programmer','draft',16)
            review=e.run_role('reviewer',str(draft),8)
            e.run_role('programmer',str(review),24);e.finish()
        result=engine.execute(workflow,{})
        self.assertTrue(result['finished'])
        self.assertEqual([r[0]['content'].split('Твоя роль: ')[-1] for r in provider.requests],['programmer','programmer','reviewer','programmer'])
        self.assertIn('review: check negative input',provider.requests[-1][-1]['content'])
    def test_reviewer_cannot_replace_source(self):
        engine=self.engine(Scripted([]));report=engine.tool('reviewer',self.correct)
        self.assertIn('error',report);self.assertIn('return data',engine.files()['app/api.py'])
    def test_source_change_invalidates_finish(self):
        engine=self.engine(Scripted([]));engine.tool('developer',self.correct);self.assertTrue(engine.finish())
        engine.tool('developer',{'action':'replace_files','files':{'app/api.py':'def solve(data):\n    return 0\n'}})
        self.assertFalse(engine.finished);self.assertFalse(engine.finish())
    def test_wrong_valid_corpus_answer_is_not_success(self):
        folder=ROOT/'advanced/tasks/M04';engine=self.engine(Scripted([]),folder=folder)
        answer={'audit_date':engine.task['audit_date'],'decisions':[{'case_id':x,'recognized_cents':0,'accepted_count':0,
            'rejected_count':0,'flagged_count':0,'over_limit_cents':0,'status':'PASS'} for x in engine.task['target_case_ids']]}
        def workflow(e):e.tool('single',{'action':'submit_answer','answer':answer});e.finish()
        result=engine.execute(workflow,{})
        self.assertEqual(result['status'],'submitted');self.assertIsNone(result['success'])
        self.assertFalse(result['visible_report']['correctness_checked'])
    def test_bool_is_not_integer_in_corpus_answer(self):
        task={'audit_date':'2026-06-30','target_case_ids':['T']}
        answer={'audit_date':'2026-06-30','decisions':[{'case_id':'T','recognized_cents':0,'accepted_count':True,
            'rejected_count':0,'flagged_count':0,'over_limit_cents':0,'status':'PASS'}]}
        with self.assertRaises(ValueError):validate_answer(answer,task)
    def test_corpus_search_pages_do_not_hide_remaining_matches(self):
        engine=self.engine(Scripted([]),folder=ROOT/'advanced/tasks/M04')
        first=engine.tool('single',{'action':'search_corpus','query':'GRANT-001','limit':1,'offset':0})
        second=engine.tool('single',{'action':'search_corpus','query':'GRANT-001','limit':1,'offset':1})
        self.assertTrue(first['has_more']);self.assertEqual(first['total_matches'],second['total_matches'])
        self.assertNotEqual(first['matches'],second['matches'])
    def test_notes_private_and_compaction_role_local(self):
        engine=self.engine(Scripted([]));engine.histories['tester']=[{'role':'user','content':'tester history'}]
        engine.histories['developer']=[{'role':'user','content':'large input'}]
        engine.tool('developer',{'action':'save_note','key':'mine','text':'saved data'})
        self.assertIsNone(engine.tool('tester',{'action':'load_note','key':'mine'})['text'])
        engine.tool('developer',{'action':'compact_notes','text':'short note'})
        self.assertEqual(engine.histories['tester'][0]['content'],'tester history')
        self.assertEqual(engine.tool('developer',{'action':'load_note','key':'mine'})['text'],'saved data')

if __name__=='__main__':unittest.main()

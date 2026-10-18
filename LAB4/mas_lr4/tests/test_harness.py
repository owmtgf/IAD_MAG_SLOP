"""Offline harness tests. These are NOT task cases and NOT a real-LLM pilot."""
import copy
import http.client
import io
import json
from email.message import Message
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
import urllib.request
import urllib.response
from maslab.engine import Engine,EpisodeStop
from maslab.executor import digest,run_checks
from maslab.provider import HTTPProvider,ProviderError,_NoRedirectHandler,parse_usage
from maslab.policies import single
from maslab.runner import ROOT,read_json,freeze,fingerprint,save_json,summarize,close_interrupted,run,result_matches_job,result_is_complete,validate_config

CASE=[{'id':'C01','input':2,'expected':3}]
GOOD='def solve(data):\n    return data+1\n'
BAD='def solve(data):\n    return data\n'

class ScriptedProvider:
    """Prewritten actions only. Never label these runs as LLM evaluation."""
    def __init__(self,actions,usage=10):
        self.actions=iter(actions);self.usage=usage;self.calls=[]
    def complete(self,messages,maximum,seed):
        self.calls.append(copy.deepcopy(messages))
        action=next(self.actions)
        if isinstance(action,Exception):raise action
        usage={'prompt_tokens':self.usage-1,'completion_tokens':1,'total_tokens':self.usage}
        return {'content':json.dumps(action),'usage':usage,'seconds':0,'model':'SCRIPTED_FIXTURE'}

def engine(provider,budget=1000):
    return Engine({'id':'fixture','statement':'Return input+1'},BAD,CASE,
        read_json(ROOT/'config.json'),provider,budget,1)

class HarnessTests(unittest.TestCase):
    def test_good_and_bad(self):
        self.assertTrue(run_checks(GOOD,CASE)['passed'])
        self.assertFalse(run_checks(BAD,CASE)['passed'])
    def test_bool_is_not_int(self):
        self.assertFalse(run_checks('def solve(data):\n    return True\n',[{'id':'x','input':0,'expected':1}])['passed'])
    def test_mutation_even_before_expected_exception(self):
        result=run_checks('def solve(data):\n    data.append(1)\n    raise ValueError()\n',[{'id':'x','input':[],'raises':'ValueError'}])
        self.assertFalse(result['passed']);self.assertTrue(result['cases'][0]['input_changed'])
    def test_no_import(self):
        self.assertFalse(run_checks('import os\ndef solve(data):\n    return 3\n',CASE)['passed'])
    def test_no_introspection(self):
        result=run_checks('def solve(data):\n    return data.__class__\n',CASE)
        self.assertFalse(result['passed'])
    def test_loop_limit(self):
        result=run_checks('def solve(data):\n    while True:\n        pass\n',CASE)
        self.assertFalse(result['passed']);self.assertLess(result['seconds'],6)
    def test_nondeterministic_default(self):
        result=run_checks('def solve(data, cache=[]):\n    cache.append(1)\n    return len(cache)\n',[{'id':'x','input':0,'expected':1}])
        self.assertFalse(result['passed']);self.assertFalse(result['cases'][0]['deterministic'])
    def test_tuple_is_not_json_list(self):
        self.assertFalse(run_checks('def solve(data):\n    return (1,2)\n',[{'id':'x','input':0,'expected':[1,2]}])['passed'])
    def test_dict_order_irrelevant(self):
        self.assertTrue(run_checks("def solve(data):\n    return {'b':2,'a':1}\n",[{'id':'x','input':0,'expected':{'a':1,'b':2}}])['passed'])
    def test_single_revises(self):
        p=ScriptedProvider([{'action':'run_tests'},{'action':'replace_code','code':GOOD},{'action':'run_tests'},{'action':'finish'}])
        r=engine(p).execute(single)
        self.assertTrue(r['success']);self.assertEqual(r['total_tokens_known'],40)
    def test_false_finish_rejected(self):
        p=ScriptedProvider([{'action':'finish'},{'action':'replace_code','code':GOOD},{'action':'finish'}])
        r=engine(p).execute(single)
        self.assertTrue(r['success']);self.assertEqual(r['model_calls'],3)
    def test_fake_test_result_is_not_trusted(self):
        e=engine(ScriptedProvider([]))
        obs=e.tool('single',{'action':'run_tests','passed':True})
        self.assertIn('error',obs);self.assertFalse(e.finish())
    def test_stale_report_invalidated(self):
        e=engine(ScriptedProvider([]));e.code=GOOD;e.tool('single',{'action':'run_tests'})
        self.assertTrue(e.current_report()['passed'])
        e.tool('single',{'action':'replace_code','code':BAD})
        self.assertIsNone(e.current_report());self.assertFalse(e.finish())
    def test_reviewer_cannot_edit(self):
        e=engine(ScriptedProvider([]));r=e.tool('reviewer',{'action':'replace_code','code':GOOD})
        self.assertIn('error',r);self.assertEqual(e.code,BAD)
    def test_overrun_is_charged_but_not_applied(self):
        e=engine(ScriptedProvider([{'action':'replace_code','code':GOOD}],usage=11),budget=10)
        r=e.execute(single)
        self.assertEqual(r['status'],'budget_exhausted');self.assertEqual(r['total_tokens_known'],11)
        self.assertEqual(r['budget_overrun'],1);self.assertEqual(e.code,BAD)
    def test_exact_budget_last_action_accepted(self):
        p=ScriptedProvider([{'action':'replace_code','code':GOOD}],usage=10)
        e=engine(p,budget=10)
        def policy(e):
            a=e.ask('single',[]);e.tool('single',a);e.finish()
        self.assertTrue(e.execute(policy)['success'])
    def test_missing_usage_invalidates(self):
        class NoUsage(ScriptedProvider):
            def complete(self,*args):return {'content':json.dumps({'action':'replace_code','code':GOOD})}
        e=engine(NoUsage([]));r=e.execute(single)
        self.assertEqual(r['status'],'usage_error');self.assertFalse(r['usage_complete']);self.assertEqual(e.code,BAD)
    def test_usage_validation(self):
        for bad in [None,{}, {'prompt_tokens':1,'completion_tokens':2,'total_tokens':4},
                    {'prompt_tokens':True,'completion_tokens':0,'total_tokens':1}]:
            with self.assertRaises(ValueError):parse_usage(bad)
    def test_network_error_unknown_spend(self):
        r=engine(ScriptedProvider([OSError('offline')])).execute(single)
        self.assertEqual(r['status'],'model_error');self.assertFalse(r['usage_complete'])
    def test_malformed_http_content_preserves_usage(self):
        config=read_json(ROOT/'config.json');config['model']='fixture-model'
        with patch.dict('os.environ',{'MAS_LLM_BASE_URL':'https://fixture.invalid/v1','MAS_LLM_API_KEY':''}):
            provider=HTTPProvider(config)
        for choices in (None,[],[None],[{}],[{'message':[]}],[{'message':{'content':None}}],[{'message':{'content':[]}}]):
            with self.subTest(choices=choices):
                response=MagicMock()
                response.__enter__.return_value.read.return_value=json.dumps({'choices':choices,
                    'usage':{'prompt_tokens':7,'completion_tokens':3,'total_tokens':10}}).encode()
                with patch.object(provider.opener,'open',return_value=response):
                    result=engine(provider).execute(single)
                self.assertEqual(result['status'],'model_error');self.assertTrue(result['usage_complete'])
                self.assertEqual(result['total_tokens_known'],10)
                self.assertEqual(result['tokens_by_role']['single']['total'],10)
    def test_http_exception_details_do_not_leak(self):
        config=read_json(ROOT/'config.json');config['model']='fixture-model'
        with patch.dict('os.environ',{'MAS_LLM_BASE_URL':'https://fixture.invalid/v1','MAS_LLM_API_KEY':''}):
            provider=HTTPProvider(config)
        with patch.object(provider.opener,'open',side_effect=http.client.BadStatusLine('fixture-secret')):
            with self.assertRaises(ProviderError) as caught:provider.complete([],10,1)
        self.assertIn('BadStatusLine',str(caught.exception));self.assertNotIn('fixture-secret',str(caught.exception))
    def test_http_redirect_never_forwards_request(self):
        config=read_json(ROOT/'config.json');config['model']='fixture-model'
        with patch.dict('os.environ',{'MAS_LLM_BASE_URL':'https://fixture.invalid/v1','MAS_LLM_API_KEY':'fixture-secret'}):
            provider=HTTPProvider(config)
        class FakeHTTPS(urllib.request.HTTPSHandler):
            def __init__(self,code):super().__init__();self.code=code;self.calls=[]
            def https_open(self,request):
                self.calls.append(request)
                headers=Message();headers['Location']='http://other.invalid/collect'
                response=urllib.response.addinfourl(io.BytesIO(b'fixture-secret'),headers,request.full_url,self.code)
                response.msg='Found'
                return response
        for code in (301,302,303,307,308):
            with self.subTest(code=code):
                handler=FakeHTTPS(code);provider.opener=urllib.request.build_opener(_NoRedirectHandler(),handler)
                with patch('socket.create_connection',side_effect=AssertionError('No network allowed')):
                    with self.assertRaisesRegex(ProviderError,'^HTTP '+str(code)+'$'):provider.complete([],10,1)
                self.assertEqual(len(handler.calls),1);self.assertEqual(handler.calls[0].get_method(),'POST')
    def test_tool_limit(self):
        e=engine(ScriptedProvider([]));e.config['max_tool_calls']=1
        e.tool('single',{'action':'read_code'})
        with self.assertRaises(EpisodeStop):e.tool('single',{'action':'read_code'})
    def test_deadline_blocks_tools_and_finish(self):
        for action in ({'action':'read_code'},{'action':'replace_code','code':GOOD},
                       {'action':'run_tests'},{'action':'finish'}):
            with self.subTest(action=action['action']):
                e=engine(ScriptedProvider([]))
                with patch('maslab.engine.time.monotonic',return_value=e.started+e.config['episode_timeout_seconds']+1):
                    with self.assertRaises(EpisodeStop) as caught:e.tool('single',action)
                self.assertEqual(caught.exception.status,'episode_timeout')
                self.assertEqual(e.code,BAD);self.assertEqual(e.tool_calls,0)
    def test_checks_crossing_deadline_do_not_finish(self):
        e=engine(ScriptedProvider([]));e.code=GOOD;clock=[e.started]
        def delayed_checks(code,cases,timeout):
            clock[0]+=e.config['episode_timeout_seconds']+1
            return {'passed':True,'passed_count':1,'code_sha256':digest(code)}
        with patch('maslab.engine.time.monotonic',side_effect=lambda:clock[0]),patch('maslab.engine.run_checks',side_effect=delayed_checks):
            result=e.execute(lambda e:e.finish())
        self.assertEqual(result['status'],'episode_timeout');self.assertFalse(result['success'])
        self.assertTrue(result['visible_passed'])
    def test_late_policy_return_cannot_count_as_success(self):
        e=engine(ScriptedProvider([]));e.code=GOOD;clock=[e.started]
        def policy(e):
            self.assertTrue(e.finish())
            clock[0]+=e.config['episode_timeout_seconds']+1
        with patch('maslab.engine.time.monotonic',side_effect=lambda:clock[0]):
            result=e.execute(policy)
        self.assertEqual(result['status'],'episode_timeout');self.assertFalse(result['success'])
    def test_edit_invalidates_successful_finish(self):
        e=engine(ScriptedProvider([]));e.code=GOOD
        def policy(e):
            self.assertTrue(e.finish())
            e.tool('single',{'action':'replace_code','code':GOOD+'\n'})
        result=e.execute(policy)
        self.assertEqual(result['status'],'unfinished');self.assertFalse(result['success'])
        self.assertTrue(result['visible_passed'])
    def test_config_rejects_nonfinite_numbers_and_invalid_budgets(self):
        for key in ('temperature','input_price_per_million','output_price_per_million'):
            for value in (float('nan'),float('inf'),float('-inf')):
                with self.subTest(key=key,value=value):
                    config=read_json(ROOT/'config.json');config[key]=value
                    with self.assertRaises(ValueError):validate_config(config)
        for value in (10,'6000',[],[10,10],[True]):
            with self.subTest(budgets=value):
                config=read_json(ROOT/'config.json');config['budgets']=value
                with self.assertRaises(ValueError):validate_config(config)
    def test_freeze_changes_with_config(self):
        with tempfile.TemporaryDirectory() as folder:
            config=Path(folder)/'config.json';save_json(config,read_json(ROOT/'config.json'))
            original=freeze(config,'maslab.student_policies',Path(folder)/'freeze.json')
            data=read_json(config);data['temperature']=0.5;save_json(config,data)
            self.assertNotEqual(original['sha256'],fingerprint(config,'maslab.student_policies')['sha256'])
    def test_freeze_includes_private_task_files_when_present(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);config=root/'config.json';save_json(config,read_json(ROOT/'config.json'))
            task=root/'teacher/private/H01';task.mkdir(parents=True)
            for name in ('task.json','main.py','tests.json'):(task/name).write_text('initial',encoding='utf-8')
            with patch('maslab.runner.ROOT',root):
                before=fingerprint(config,'maslab.student_policies')
                for name in ('task.json','main.py','tests.json'):
                    self.assertIn('teacher/private/H01/'+name,before['files'])
                (task/'tests.json').write_text('changed',encoding='utf-8')
                self.assertNotEqual(before['sha256'],fingerprint(config,'maslab.student_policies')['sha256'])
    def test_saved_result_has_identity_and_exact_code_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            e=engine(ScriptedProvider([]));e.out_dir=Path(folder);e.code=GOOD.replace('\n','\r\n')
            job={'episode_id':'fixture_single_b1000_r1','task_id':'fixture','architecture':'single','budget':1000,'repeat':1,'seed':1}
            result=e.execute(lambda e:e.finish(),result_metadata=job)
            saved=read_json(Path(folder)/'result.json')
            self.assertTrue(result_matches_job(saved,job));self.assertEqual(saved,result)
            self.assertEqual((Path(folder)/'main.py').read_bytes(),e.code.encode('utf-8'))
            self.assertFalse((Path(folder)/'result.json.tmp').exists())
            trace=[json.loads(line) for line in (Path(folder)/'trace.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertTrue(result_matches_job(trace[-1]['result'],job))
    def test_result_identity_requires_all_fields_and_exact_types(self):
        job={'episode_id':'a','task_id':'D01','architecture':'single','budget':10,'repeat':1,'seed':1}
        self.assertTrue(result_matches_job(dict(job),job))
        for key,value in job.items():
            bad=dict(job);del bad[key];self.assertFalse(result_matches_job(bad,job))
        bad=dict(job);bad['repeat']=True
        self.assertFalse(result_matches_job(bad,job));self.assertFalse(result_matches_job([],job))
    def test_completed_run_resumes_without_replaying_model_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            config=Path(folder)/'config.json';save_json(config,read_json(ROOT/'config.json'))
            args=SimpleNamespace(config=str(config),policies='maslab.student_policies',split='dev',freeze='',
                ids='D01',architectures='single',budgets='1000',repeats=1,out=str(Path(folder)/'run'),resume=False)
            provider=ScriptedProvider([{'action':'replace_code','code':GOOD},{'action':'finish'}])
            with patch('maslab.runner.HTTPProvider',return_value=provider),patch('maslab.runner.load_task',return_value=({'id':'D01'},BAD,CASE)),patch('builtins.print'):
                run(args);self.assertEqual(len(provider.calls),2)
                args.resume=True;run(args);self.assertEqual(len(provider.calls),2)
                manifest=read_json(Path(args.out)/'manifest.json');job=manifest['jobs'][0]
                save_json(Path(args.out)/'episodes'/job['episode_id']/'result.json',job)
                with self.assertRaisesRegex(ValueError,'Incomplete or mismatched result'):run(args)
                self.assertEqual(len(provider.calls),2)
                args.repeats=0;args.resume=False;args.out=str(Path(folder)/'zero-repeat')
                with self.assertRaisesRegex(ValueError,'Invalid protocol'):run(args)
    def test_missing_kept_in_denominator(self):
        with tempfile.TemporaryDirectory() as folder:
            jobs=[{'episode_id':'a','task_id':'T01','architecture':'single','budget':6000,'repeat':1},
                  {'episode_id':'b','task_id':'T02','architecture':'single','budget':6000,'repeat':1}]
            save_json(Path(folder)/'manifest.json',{'source':'scripted_fixture','config':read_json(ROOT/'config.json'),'jobs':jobs})
            save_json(Path(folder)/'episodes/a/result.json',{**jobs[0],'status':'success','success':True,'usage_complete':True,
                'total_tokens_known':20,'input_tokens_known':19,'output_tokens_known':1,'seconds':1})
            metrics=summarize(folder)
            self.assertEqual(metrics[0]['success_rate'],0.5);self.assertEqual(metrics[0]['planned'],2)
    def test_invalid_results_cannot_count_as_summary_successes(self):
        for content in ('{"status":"success","success":true,"usage_complete":true}','{"status":'):
            with self.subTest(content=content),tempfile.TemporaryDirectory() as folder:
                job={'episode_id':'a','task_id':'T01','architecture':'single','budget':6000,'repeat':1}
                save_json(Path(folder)/'manifest.json',{'source':'scripted_fixture','config':read_json(ROOT/'config.json'),'jobs':[job]})
                path=Path(folder)/'episodes/a/result.json';path.parent.mkdir(parents=True);path.write_text(content,encoding='utf-8')
                metrics=summarize(folder)
                self.assertEqual(metrics[0]['success_rate'],0);self.assertEqual(metrics[0]['planned'],1)
                self.assertEqual(metrics[0]['completed'],0);self.assertEqual(metrics[0]['unknown_usage'],1)
                self.assertFalse(read_json(Path(folder)/'summary.json')['complete'])
    def test_metadata_only_and_malformed_usage_are_not_completed_results(self):
        job={'episode_id':'a','task_id':'D01','architecture':'single','budget':10,'repeat':1,'seed':1}
        valid={**job,'status':'success','success':True,'usage_complete':True,
               'input_tokens_known':7,'output_tokens_known':3,'total_tokens_known':10}
        invalid=[dict(job),{**valid,'status':None},{**valid,'success':'true'},
                 {**valid,'usage_complete':'true'},{**valid,'input_tokens_known':'7'},
                 {**valid,'output_tokens_known':True},{**valid,'input_tokens_known':None},
                 {**valid,'total_tokens_known':-1},{**valid,'total_tokens_known':11}]
        missing=dict(valid);del missing['input_tokens_known'];invalid.append(missing)
        self.assertTrue(result_is_complete(valid,job))
        for index,result in enumerate(invalid):
            with self.subTest(index=index),tempfile.TemporaryDirectory() as folder:
                self.assertTrue(result_matches_job(result,job))
                self.assertFalse(result_is_complete(result,job))
                config=read_json(ROOT/'config.json')
                config['input_price_per_million']=config['output_price_per_million']=1
                save_json(Path(folder)/'manifest.json',{'source':'scripted_fixture','config':config,'jobs':[job]})
                path=Path(folder)/'episodes/a/result.json';save_json(path,result)
                metrics=summarize(folder)
                self.assertEqual(metrics[0]['completed'],0);self.assertEqual(metrics[0]['successes'],0)
                self.assertEqual(close_interrupted(folder),['a'])
                self.assertEqual(read_json(path.parent/'result.partial.json'),result)
                self.assertTrue(result_is_complete(read_json(path),job))
                self.assertEqual(close_interrupted(folder),[])
    def test_interrupted_never_silently_replayed(self):
        with tempfile.TemporaryDirectory() as folder:
            job={'episode_id':'a','task_id':'T01','architecture':'single','budget':6000,'repeat':1}
            save_json(Path(folder)/'manifest.json',{'jobs':[job]})
            (Path(folder)/'episodes/a').mkdir(parents=True)
            self.assertEqual(close_interrupted(folder),['a'])
            result=read_json(Path(folder)/'episodes/a/result.json')
            self.assertEqual(result['status'],'interrupted');self.assertFalse(result['usage_complete'])
    def test_incomplete_result_can_be_closed_without_losing_evidence(self):
        for content in ('{"task_id":"D01","status":"success"}','{"task_id":'):
            with self.subTest(content=content),tempfile.TemporaryDirectory() as folder:
                job={'episode_id':'a','task_id':'D01','architecture':'single','budget':10,'repeat':1,'seed':1}
                save_json(Path(folder)/'manifest.json',{'jobs':[job]})
                path=Path(folder)/'episodes/a/result.json';path.parent.mkdir(parents=True)
                path.write_text(content,encoding='utf-8')
                self.assertEqual(close_interrupted(folder),['a'])
                result=read_json(path)
                self.assertTrue(result_matches_job(result,job));self.assertEqual(result['status'],'interrupted')
                self.assertEqual((path.parent/'result.partial.json').read_text(encoding='utf-8'),content)
                self.assertEqual(close_interrupted(folder),[])

if __name__=='__main__':unittest.main()

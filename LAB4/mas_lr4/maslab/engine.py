import json
from pathlib import Path
import time
from .executor import digest,run_checks
from .provider import parse_usage

class EpisodeStop(Exception):
    def __init__(self,status):
        self.status = status
        super().__init__(status)

class Engine:
    """One isolated episode. Every role must call this API for LLM/tools.

    Student policy code is trusted orchestration code, not a sandboxed submission.
    Reference solution execution is restricted separately by executor.py.
    """
    def __init__(self,task,code,cases,config,provider,budget,seed,out_dir=None,prompt_root=None):
        self.task,self.code,self.cases = task,code,cases
        self.config,self.provider,self.budget,self.seed = config,provider,budget,seed
        self.out_dir = Path(out_dir) if out_dir else None
        self.prompt_root = Path(prompt_root) if prompt_root else Path(__file__).resolve().parents[1]/'prompts'
        self.started = time.monotonic()
        self.tokens_in = self.tokens_out = self.calls = self.tool_calls = self.invalid_actions = 0
        self.usage_complete = True
        self.report = None
        self.events = []
        self.histories = {}
        self.tokens_by_role = {}
        self.finished = False
        if self.out_dir:
            self.out_dir.mkdir(parents=True,exist_ok=True)

    @property
    def tokens(self):
        return self.tokens_in+self.tokens_out

    def log(self,event,**values):
        entry = json.loads(json.dumps({'event':event,'elapsed_seconds':round(time.monotonic()-self.started,6),**values},ensure_ascii=False))
        self.events.append(entry)
        if self.out_dir:
            with (self.out_dir/'trace.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(entry,ensure_ascii=False)+'\n')

    def check_time(self):
        if time.monotonic()-self.started > self.config['episode_timeout_seconds']:
            raise EpisodeStop('episode_timeout')

    def guard(self):
        self.check_time()
        if self.tokens >= self.budget:
            raise EpisodeStop('budget_exhausted')
        if self.calls >= self.config['max_model_calls']:
            raise EpisodeStop('call_limit')

    def context(self):
        return {'task':self.task,'visible_cases':self.cases,'code':self.code,
                'code_sha256':digest(self.code),'last_test_report':self.current_report(),
                'tokens_used':self.tokens,'token_limit':self.budget}

    def current_report(self):
        return self.report if self.report and self.report['code_sha256']==digest(self.code) else None

    def ask(self,role,messages):
        self.guard()
        self.calls += 1
        maximum = min(self.config['max_output_tokens'],self.budget-self.tokens)
        self.log('model_request',role=role,call=self.calls,messages=messages,max_output_tokens=maximum)
        try:
            response = self.provider.complete(messages,maximum,self.seed+self.calls)
        except Exception as exc:
            self.usage_complete = False
            self.log('model_error',role=role,error=type(exc).__name__,detail=str(exc)[:200])
            raise EpisodeStop('model_error') from None
        self.log('model_response',role=role,call=self.calls,**response)
        try:
            tin,tout,total = parse_usage(response.get('usage'))
        except ValueError as exc:
            self.usage_complete = False
            self.log('usage_error',role=role,reason=str(exc))
            raise EpisodeStop('usage_error') from None
        self.tokens_in += tin; self.tokens_out += tout
        role_usage = self.tokens_by_role.setdefault(role,{'input':0,'output':0,'total':0,'calls':0})
        role_usage['input']+=tin;role_usage['output']+=tout;role_usage['total']+=total;role_usage['calls']+=1
        # The response is charged, but no action from an over-budget response is accepted.
        if self.tokens > self.budget:
            self.log('budget_overrun',tokens=self.tokens,overrun=self.tokens-self.budget)
            raise EpisodeStop('budget_exhausted')
        self.check_time()
        if type(response.get('content')) is not str:
            self.log('model_error',role=role,error='invalid_content',
                     detail='Assistant content must be a string')
            raise EpisodeStop('model_error')
        text = response['content'].strip()
        if text.startswith('```json\n') and text.endswith('\n```'):
            text = text[8:-4]
        try:
            action = json.loads(text)
            if type(action) is not dict or not isinstance(action.get('action'),str):
                raise ValueError()
            return action
        except (ValueError,TypeError):
            self.invalid_actions += 1
            return {'action':'invalid','error':'Return exactly one JSON action object'}

    def tool(self,role,action):
        """Only real tool results can attest to a current artifact."""
        self.check_time()
        name = action.get('action')
        schema = {'read_code':{'action'},'replace_code':{'action','code'},
                  'run_tests':{'action'},'yield':{'action','message'},'finish':{'action'}}
        if name not in schema or set(action)!=schema[name]:
            self.invalid_actions += 1
            return {'error':'invalid action or unexpected fields'}
        if name == 'yield':
            if type(action['message']) is not str or len(action['message'])>6000:
                return {'error':'message must be a string of at most 6000 characters'}
            return {'yield':action['message']}
        if name == 'finish':
            return {'finish_requested':True}
        if self.tool_calls >= self.config['max_tool_calls']:
            raise EpisodeStop('tool_limit')
        self.tool_calls += 1
        if name == 'read_code':
            result = {'code':self.code,'code_sha256':digest(self.code)}
        elif name == 'replace_code':
            if role not in ('single','programmer','developer'):
                result = {'error':'this role cannot edit code'}
            elif type(action['code']) is not str or len(action['code'].encode())>40000:
                result = {'error':'code must be a string of at most 40000 bytes'}
            else:
                self.code = action['code']
                self.report = None
                self.finished = False
                result = {'saved':True,'code_sha256':digest(self.code)}
                if self.out_dir:
                    (self.out_dir/'main.py').write_bytes(self.code.encode('utf-8'))
        else:
            self.report = run_checks(self.code,self.cases,self.config['test_timeout_seconds'])
            result = self.report
        self.log('tool_result',role=role,action=action,result=result)
        self.check_time()
        return result

    def run_role(self,role,instruction='',max_turns=6):
        """A separate history per role; shared code and trusted tool state."""
        system = (self.prompt_root/'base.txt').read_text(encoding='utf-8')+'\n'+(self.prompt_root/(role+'.txt')).read_text(encoding='utf-8')
        history = self.histories.setdefault(role,[{'role':'system','content':system}])
        history.append({'role':'user','content':json.dumps({'instruction':instruction,**self.context()},ensure_ascii=False)})
        for _ in range(max_turns):
            action = self.ask(role,history)
            history.append({'role':'assistant','content':json.dumps(action,ensure_ascii=False)})
            observation = self.tool(role,action)
            history.append({'role':'user','content':json.dumps({'tool_observation':observation},ensure_ascii=False)})
            if 'yield' in observation or 'finish_requested' in observation:
                return {'message':observation.get('yield','role finished'),
                        'finish_requested':'finish_requested' in observation,
                        'code_sha256':digest(self.code),'verified_report':self.current_report()}
        return {'message':'role turn limit reached','finish_requested':False,
                'code_sha256':digest(self.code),'verified_report':self.current_report()}

    def coordinator_decision(self,feedback=None):
        system = (self.prompt_root/'base.txt').read_text(encoding='utf-8')+'\n'+(self.prompt_root/'coordinator.txt').read_text(encoding='utf-8')
        history = self.histories.setdefault('coordinator',[{'role':'system','content':system}])
        history.append({'role':'user','content':json.dumps({'feedback':feedback,**self.context()},ensure_ascii=False)})
        action = self.ask('coordinator',history)
        history.append({'role':'assistant','content':json.dumps(action,ensure_ascii=False)})
        self.log('coordinator_decision',action=action)
        return action

    def finish(self):
        # Mandatory independent check; never trust role prose or an obsolete report.
        report = self.tool('single',{'action':'run_tests'})
        if report.get('passed') is True and report.get('code_sha256')==digest(self.code):
            self.finished = True
            return True
        return False

    def execute(self,policy,result_metadata=None):
        status = 'unfinished'
        try:
            policy(self)
            self.check_time()
            if self.finished:
                status = 'success'
        except EpisodeStop as exc:
            status = exc.status
        except NotImplementedError:
            status = 'not_implemented'
        except Exception as exc:
            status = 'policy_error'
            self.log('policy_error',error=type(exc).__name__,detail=str(exc)[:300])
        final = run_checks(self.code,self.cases,self.config['test_timeout_seconds'])
        if status=='success':
            if time.monotonic()-self.started > self.config['episode_timeout_seconds']:
                status='episode_timeout'
            elif not final['passed']:
                status='verification_failed'
        result = {'task_id':self.task['id'],'status':status,'success':status=='success',
            'visible_passed':final['passed'],'visible_passed_count':final.get('passed_count',0),
            'visible_total':len(self.cases),'code_sha256':digest(self.code),
            'input_tokens_known':self.tokens_in,'output_tokens_known':self.tokens_out,
            'total_tokens_known':self.tokens,'usage_complete':self.usage_complete,
            'budget':self.budget,'budget_overrun':max(0,self.tokens-self.budget),
            'model_calls':self.calls,'tool_calls':self.tool_calls,'invalid_actions':self.invalid_actions,
            'tokens_by_role':self.tokens_by_role,
            'seconds':round(time.monotonic()-self.started,6),'final_report':final}
        if result_metadata:
            result.update(result_metadata)
        self.log('episode_end',result=result)
        if self.out_dir:
            (self.out_dir/'main.py').write_bytes(self.code.encode('utf-8'))
            temporary = self.out_dir/'result.json.tmp'
            temporary.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            temporary.replace(self.out_dir/'result.json')
        return result

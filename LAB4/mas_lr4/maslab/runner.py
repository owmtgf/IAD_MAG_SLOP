import csv
import hashlib
import importlib
import inspect
import itertools
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
from .engine import Engine
from .provider import HTTPProvider
from .policies import single

ROOT = Path(__file__).resolve().parents[1]

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def save_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)

def fingerprint(config_path,policy_module):
    files = [Path(config_path).resolve()]
    for folder in ('maslab','prompts','data'):
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    private = ROOT/'teacher'/'private'
    if private.exists():
        files.extend(p for p in private.glob('*/*') if p.is_file() and p.name in ('task.json','main.py','tests.json'))
    module = importlib.import_module(policy_module)
    files.append(Path(module.__file__).resolve())
    result = {}
    for p in sorted(set(files)):
        try: label=str(p.relative_to(ROOT))
        except ValueError: label='external_config/'+p.name
        result[label]=hashlib.sha256(p.read_bytes()).hexdigest()
    digest=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return {'sha256':digest,'files':result,'policy_module':policy_module}

def validate_config(config):
    required = {'model','temperature','send_seed','seed','budgets','repeats','max_output_tokens',
        'max_model_calls','max_tool_calls','request_timeout_seconds','episode_timeout_seconds',
        'test_timeout_seconds','input_price_per_million','output_price_per_million'}
    if set(config)!=required:
        raise ValueError('Config keys differ from the supplied config.json contract')
    for key in ('repeats','max_output_tokens','max_model_calls','max_tool_calls','request_timeout_seconds','episode_timeout_seconds','test_timeout_seconds'):
        if type(config[key]) is not int or config[key]<=0:raise ValueError('Invalid '+key)
    if type(config['budgets']) is not list or not config['budgets'] or any(type(x)is not int or x<=0 for x in config['budgets']):raise ValueError('Invalid budgets')
    if len(set(config['budgets']))!=len(config['budgets']):raise ValueError('Invalid budgets')
    if type(config['seed']) is not int or type(config['send_seed']) is not bool:raise ValueError('Invalid seed settings')
    if not isinstance(config['model'],str) or type(config['temperature']) not in (float,int) or not math.isfinite(config['temperature']):raise ValueError('Invalid model settings')
    for key in ('input_price_per_million','output_price_per_million'):
        if config[key] is not None and (type(config[key]) not in (float,int) or not math.isfinite(config[key]) or config[key]<0):raise ValueError('Invalid '+key)

def freeze(config_path,policy_module,path):
    config=read_json(config_path);validate_config(config)
    obj=fingerprint(config_path,policy_module)
    save_json(path,obj)
    return obj

def load_task(folder,visible_only=False):
    folder=Path(folder)
    return (read_json(folder/'task.json'),(folder/'main.py').read_text(encoding='utf-8'),
            read_json(folder/'tests.json')[:3] if visible_only else read_json(folder/'tests.json'))

def result_matches_job(result,job):
    return type(result) is dict and all(type(result.get(key)) is type(value) and result.get(key)==value
                                        for key,value in job.items())

def result_is_complete(result,job):
    """Recognize a completion record separately from its episode identity."""
    if not result_matches_job(result,job):
        return False
    if type(result.get('status')) is not str or not result['status']:
        return False
    if type(result.get('success')) is not bool or type(result.get('usage_complete')) is not bool:
        return False
    fields=('input_tokens_known','output_tokens_known','total_tokens_known')
    if any(key not in result for key in fields):
        return False
    counts=[result[key] for key in fields]
    if any(value is not None and (type(value) is not int or value<0) for value in counts):
        return False
    if any(value is None for value in counts):
        return result['usage_complete'] is False
    return counts[0]+counts[1]==counts[2]

def run(args):
    config_path=Path(args.config).resolve();config=read_json(config_path);validate_config(config)
    fingerprint_now=fingerprint(config_path,args.policies)
    if args.split in ('test','private','extra'):
        locked=read_json(args.freeze)
        if locked!=fingerprint_now:raise ValueError('Freeze mismatch. Do not change code/config/prompts/data after final freeze.')
    provider=HTTPProvider(config)
    policies=importlib.import_module(args.policies)
    routes={'single':single,'fixed':policies.fixed,'coordinator':policies.coordinator}
    architectures=args.architectures.split(',')
    if len(set(architectures))!=len(architectures) or any(x not in routes for x in architectures):raise ValueError('Invalid architectures')
    for architecture in architectures:
        if 'raise NotImplementedError' in inspect.getsource(routes[architecture]):
            raise ValueError('Implement '+architecture+' before this run; for the supplied baseline use --architectures single')
    if args.split=='private':
        base=ROOT/'teacher'/'private'
    else:
        base=ROOT/'data'/args.split
    paths={p.name:p for p in sorted(base.glob('*')) if p.is_dir()}
    ids=args.ids.split(',') if args.ids else list(paths)
    if not ids or len(set(ids))!=len(ids) or any(x not in paths for x in ids):raise ValueError('Unknown or duplicate task IDs')
    budgets=[int(x) for x in args.budgets.split(',')] if args.budgets else config['budgets']
    repeats=config['repeats'] if args.repeats is None else args.repeats
    if any(x<=0 for x in budgets) or len(set(budgets))!=len(budgets) or repeats<=0:raise ValueError('Invalid protocol')
    jobs=[{'task_id':t,'architecture':a,'budget':b,'repeat':r}
          for t,a,b,r in itertools.product(ids,architectures,budgets,range(1,repeats+1))]
    random.Random(config['seed']).shuffle(jobs)
    for job in jobs:
        # The same task/repeat seed across architectures and budgets.
        job['seed']=config['seed']+int(hashlib.sha256((job['task_id']+str(job['repeat'])).encode()).hexdigest()[:7],16)
        job['episode_id']=f"{job['task_id']}_{job['architecture']}_b{job['budget']}_r{job['repeat']}"
    manifest={'protocol_version':1,'split':args.split,'config':config,'fingerprint':fingerprint_now,
        'python':platform.python_version(),'platform':platform.platform(),
        'provider_base':os.environ.get('MAS_LLM_BASE_URL','').rstrip('/'),
        'source':'real_http_model','jobs':jobs}
    out=Path(args.out).resolve()
    if (out/'manifest.json').exists():
        if not args.resume:raise ValueError('Output exists: use --resume for the same frozen run or a new --out')
        if read_json(out/'manifest.json')!=manifest:raise ValueError('Resume manifest mismatch')
    elif out.exists() and any(out.iterdir()):
        raise ValueError('Output folder is not empty')
    else:
        save_json(out/'manifest.json',manifest)
    for i,job in enumerate(jobs,1):
        target=out/'episodes'/job['episode_id']
        if args.resume and (target/'result.json').exists():
            try:
                old=read_json(target/'result.json')
            except ValueError:
                old=None
            if not result_is_complete(old,job):
                raise ValueError('Incomplete or mismatched result '+job['episode_id']+': use close-interrupted before resume')
            continue
        if target.exists() and any(target.iterdir()):
            # No silent recharging after interrupted or potentially billed calls.
            raise ValueError('Interrupted episode '+job['episode_id']+': use close-interrupted before resume')
        task,code,cases=load_task(paths[job['task_id']],visible_only=args.split=='private')
        episode=Engine(task,code,cases,config,provider,job['budget'],job['seed'],target)
        episode.log('episode_start',**job,source='real_http_model')
        result=episode.execute(routes[job['architecture']],result_metadata=job)
        print(f"[{i}/{len(jobs)}] {job['episode_id']}: {result['status']} ({result['total_tokens_known']} known tokens)",flush=True)
    return summarize(out)

def summarize(out):
    out=Path(out);manifest=read_json(out/'manifest.json');config=manifest['config']
    rows=[];groups={}
    for job in manifest['jobs']:
        path=out/'episodes'/job['episode_id']/'result.json'
        if path.exists():
            try:
                result=read_json(path)
            except ValueError:
                result=None
            if not result_is_complete(result,job):
                result={'status':'invalid_result','success':False,'usage_complete':False}
        else:
            result={'status':'missing','success':False,'usage_complete':False}
        row={**job,**{k:result.get(k) for k in ('status','success','visible_passed','total_tokens_known','input_tokens_known','output_tokens_known','usage_complete','budget_overrun','model_calls','tool_calls','seconds','code_sha256')}}
        prices=[config[k] for k in ('input_price_per_million','output_price_per_million')]
        row['estimated_cost']=((result['input_tokens_known']*prices[0]+result['output_tokens_known']*prices[1])/1000000
            if result['usage_complete'] and all(p is not None for p in prices) else None)
        rows.append(row)
        groups.setdefault((job['architecture'],job['budget']),[]).append(row)
    metrics=[]
    for (architecture,budget),values in sorted(groups.items()):
        complete=[v for v in values if v['status'] not in ('missing','invalid_result')]
        token_values=[v['total_tokens_known'] for v in complete if v['usage_complete'] and v['total_tokens_known'] is not None]
        metrics.append({'architecture':architecture,'budget':budget,'planned':len(values),'completed':len(complete),
            'successes':sum(v['success'] is True for v in values),'success_rate':sum(v['success'] is True for v in values)/len(values),
            'median_tokens_complete_usage':statistics.median(token_values) if token_values else None,
            'median_seconds':statistics.median([v['seconds'] for v in complete if v['seconds'] is not None]) if any(v['seconds'] is not None for v in complete) else None,
            'unknown_usage':sum(v['usage_complete'] is not True for v in values),
            'budget_exhausted':sum(v['status']=='budget_exhausted' for v in values)})
    with (out/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    save_json(out/'summary.json',{'source':manifest['source'],'metrics':metrics,
        'complete':all(v['status'] not in ('missing','invalid_result') for v in rows),
        'comparable_usage':all(v['usage_complete'] is True for v in rows)})
    return metrics

def close_interrupted(out):
    """Preserve incomplete traces; count interrupted requests as unknown spend/failure."""
    out=Path(out);manifest=read_json(out/'manifest.json');closed=[]
    for job in manifest['jobs']:
        folder=out/'episodes'/job['episode_id']
        path=folder/'result.json'
        if not folder.exists():
            continue
        if path.exists():
            try:
                old=read_json(path)
            except ValueError:
                old=None
            if result_is_complete(old,job):
                continue
            # Keep the incomplete record as evidence; never silently overwrite it.
            backup=folder/'result.partial.json'
            suffix=1
            while backup.exists():
                backup=folder/('result.partial.'+str(suffix)+'.json');suffix+=1
            path.replace(backup)
        if not path.exists():
            save_json(folder/'result.json',{**job,'status':'interrupted','success':False,
                'usage_complete':False,'total_tokens_known':None,'input_tokens_known':None,
                'output_tokens_known':None,'seconds':None,'visible_passed':False})
            closed.append(job['episode_id'])
    return closed

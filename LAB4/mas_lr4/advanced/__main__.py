import argparse
import csv
import hashlib
import importlib
import inspect
import itertools
import json
import os
import random
import sys
from pathlib import Path
from maslab.provider import HTTPProvider
from maslab.runner import validate_config
from .engine import Engine, read, save
from .executor import probe, check
from .policies import single

ROOT=Path(__file__).resolve().parent

def fingerprint(config, policies):
    module=importlib.import_module(policies)
    files=[Path(config).resolve(),Path(module.__file__).resolve(),ROOT.parent/'maslab/provider.py',ROOT.parent/'maslab/engine.py']
    files += [p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    return {str(p.relative_to(ROOT.parent)) if p.is_relative_to(ROOT.parent) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}

def run(args):
    config=read(args.config);validate_config(config)
    locked=read(args.freeze)
    if locked != fingerprint(args.config,args.policies):
        raise ValueError('Freeze mismatch: code, model, data or protocol changed')
    ids=args.ids.split(',');architectures=args.architectures.split(',')
    if not ids or len(set(ids))!=len(ids) or any(x not in ('M01','M02','M03','M04') for x in ids):
        raise ValueError('Select M01..M04 without duplicates')
    module=importlib.import_module(args.policies)
    routes={'single':single,'fixed':module.fixed,'coordinator':module.coordinator}
    if len(set(architectures))!=len(architectures) or any(x not in routes for x in architectures):
        raise ValueError('Unknown or duplicate architecture')
    for name in architectures:
        if 'raise NotImplementedError' in inspect.getsource(routes[name]):
            raise ValueError('Implement '+name+' first; baseline uses --architectures single')
    budgets=[int(x) for x in args.budgets.split(',')] if args.budgets else config['budgets']
    repeats=args.repeats if args.repeats is not None else config['repeats']
    if repeats<=0 or not budgets or min(budgets)<=0 or len(set(budgets))!=len(budgets):
        raise ValueError('Invalid budgets or repeats')
    jobs=[{'task_id':task,'architecture':arch,'budget':budget,'repeat':rep}
          for task,arch,budget,rep in itertools.product(ids,architectures,budgets,range(1,repeats+1))]
    random.Random(config['seed']).shuffle(jobs)
    for job in jobs:
        job['seed']=config['seed']+int(hashlib.sha256((job['task_id']+str(job['repeat'])).encode()).hexdigest()[:7],16)
        job['episode_id']=f"{job['task_id']}_{job['architecture']}_b{job['budget']}_r{job['repeat']}"
    manifest={'source':'real_http_model','config':config,'fingerprint':locked,'jobs':jobs,
              'provider_base':os.environ.get('MAS_LLM_BASE_URL','').rstrip('/')}
    out=Path(args.out).resolve()
    if (out/'manifest.json').exists():
        if not args.resume or read(out/'manifest.json')!=manifest:
            raise ValueError('Existing run: use exact frozen --resume or new --out')
    elif out.exists() and any(out.iterdir()):
        raise ValueError('Output must be empty')
    else:
        out.mkdir(parents=True,exist_ok=True);save(out/'manifest.json',manifest)
    provider=HTTPProvider(config)
    for job in jobs:
        folder=out/'episodes'/job['episode_id']
        if folder.exists() and any(folder.iterdir()):
            if args.resume and (folder/'result.json').exists():
                result=read(folder/'result.json')
                counts=[result.get(k) for k in ('input_tokens_known','output_tokens_known','total_tokens_known')]
                valid_usage=(result.get('usage_complete') is False and counts==[None,None,None]) or (
                    all(type(x)is int and x>=0 for x in counts) and counts[0]+counts[1]==counts[2])
                if all(type(result.get(k))is type(v) and result.get(k)==v for k,v in job.items()) and type(result.get('status'))is str and result.get('status') and type(result.get('finished'))is bool and type(result.get('usage_complete'))is bool and valid_usage:
                    continue
            raise ValueError('Interrupted episode: preserve it and mark infrastructure_interrupted; do not silently repeat')
        engine=Engine(ROOT/'tasks'/job['task_id'],config,provider,job['budget'],job['seed'],folder)
        result=engine.execute(routes[job['architecture']],job)
        print(job['episode_id']+': '+result['status'],flush=True)
    summarize(out)

def summarize(out):
    out=Path(out);manifest=read(out/'manifest.json');rows=[]
    for job in manifest['jobs']:
        path=out/'episodes'/job['episode_id']/'result.json'
        result=read(path) if path.exists() else {**job,'status':'missing','finished':False,'success':None}
        report=result.get('visible_report',{});examples=report.get('open_program_examples',{})
        config=manifest['config'];prices=[config['input_price_per_million'],config['output_price_per_million']]
        cost=None
        if result.get('usage_complete') is True and all(x is not None for x in prices):
            cost=(result['input_tokens_known']*prices[0]+result['output_tokens_known']*prices[1])/1000000
        rows.append({**job,'status':result.get('status'),'finished':result.get('finished',False),
                     'model_calls':result.get('model_calls'),'tool_calls':result.get('tool_calls'),
                     'tokens':result.get('total_tokens_known'),'input_tokens_known':result.get('input_tokens_known'),
                     'output_tokens_known':result.get('output_tokens_known'),'usage_complete':result.get('usage_complete',False),
                     'seconds':result.get('seconds'),'cost':cost,'budget_overrun':result.get('budget_overrun'),
                     'visible_passed':report.get('passed'),'visible_passed_count':report.get('passed_count'),
                     'visible_total':report.get('total'),'schema_valid':report.get('schema_valid'),
                     'open_program_examples_passed':examples.get('passed_count'),'open_program_examples_total':examples.get('total'),
                     'final_success':None})
    with (out/'results.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    save(out/'summary.json',{'episodes_expected':len(rows),'rows':rows,
                            'interpretation':'Visible checks/schema only. Final success determined by teacher.'})

def close_interrupted(args):
    out=Path(args.out).resolve();manifest=read(out/'manifest.json')
    jobs=[j for j in manifest['jobs'] if j['episode_id']==args.episode_id]
    if len(jobs)!=1:raise ValueError('Unknown episode')
    folder=out/'episodes'/args.episode_id
    if not folder.exists() or not any(folder.iterdir()):raise ValueError('Episode did not start')
    if (folder/'result.json').exists():raise ValueError('Episode already has a result')
    save(folder/'result.json',{**jobs[0],'status':'infrastructure_interrupted','finished':False,
         'success':False,'usage_complete':False,'total_tokens_known':None,'reason':args.reason})
    summarize(out)

def main():
    parser=argparse.ArgumentParser(description='Additional M01-M04 tasks, same-model architecture comparison')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    q=sub.add_parser('check');q.add_argument('task',choices=['M01','M02','M03']);q.add_argument('--project')
    q=sub.add_parser('schema');q.add_argument('answer')
    q=sub.add_parser('freeze');q.add_argument('--config',default='advanced/config.json');q.add_argument('--policies',default='advanced.student_policies');q.add_argument('--out',default='advanced_freeze.json')
    q=sub.add_parser('run');q.add_argument('--config',default='advanced/config.json');q.add_argument('--policies',default='advanced.student_policies');q.add_argument('--freeze',default='advanced_freeze.json');q.add_argument('--ids',default='M01,M02,M03,M04');q.add_argument('--architectures',default='single,fixed,coordinator');q.add_argument('--budgets');q.add_argument('--repeats',type=int);q.add_argument('--out',required=True);q.add_argument('--resume',action='store_true')
    q=sub.add_parser('summary');q.add_argument('out')
    q=sub.add_parser('close-interrupted');q.add_argument('--out',required=True);q.add_argument('--episode-id',required=True);q.add_argument('--reason',required=True)
    args=parser.parse_args()
    if args.command=='doctor':
        probe();print(json.dumps({'sandbox_available':True,'tasks':4,'real_model_called':False}))
    elif args.command=='check':
        folder=ROOT/'tasks'/args.task
        result=check(Path(args.project).resolve() if args.project else folder/'starter',read(folder/'visible.json'))
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
    elif args.command=='schema':
        from .engine import validate_answer
        validate_answer(read(args.answer),read(ROOT/'tasks/M04/task.json'));print('Format valid; numerical correctness not checked')
    elif args.command=='freeze':save(args.out,fingerprint(args.config,args.policies));print('Frozen')
    elif args.command=='run':run(args)
    elif args.command=='close-interrupted':close_interrupted(args)
    else:summarize(args.out)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr);raise SystemExit(2)

import argparse
import json
import os
from pathlib import Path
import sys
from .executor import run_checks
from .runner import ROOT,read_json,load_task,freeze,run,summarize,close_interrupted

def main():
    p=argparse.ArgumentParser(description='MAS ЛР4 experiment harness')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor',help='offline environment/data check, never calls a model')
    q=sub.add_parser('check',help='run the visible tests against a candidate')
    q.add_argument('task_id');q.add_argument('--code')
    q=sub.add_parser('freeze');q.add_argument('--config',default='config.json');q.add_argument('--policies',default='maslab.student_policies');q.add_argument('--out',default='freeze.json')
    q=sub.add_parser('run');q.add_argument('--config',default='config.json');q.add_argument('--policies',default='maslab.student_policies');q.add_argument('--freeze',default='freeze.json')
    q.add_argument('--split',choices=['dev','test','private','extra'],default='dev');q.add_argument('--ids');q.add_argument('--architectures',default='single,fixed,coordinator');q.add_argument('--budgets');q.add_argument('--repeats',type=int);q.add_argument('--out',required=True);q.add_argument('--resume',action='store_true')
    for command in ('summary','close-interrupted'):
        q=sub.add_parser(command);q.add_argument('out')
    args=p.parse_args()
    if args.command=='doctor':
        sample=ROOT/'data'/'dev'/'D01'
        task,code,cases=load_task(sample)
        report=run_checks('def solve(data):\n    return data\n',[{'id':'smoke','input':[1,2],'expected':[1,2]}])
        result={'python':sys.version.split()[0],'worker_ok':report['passed'],
                'dev_tasks':len(list((ROOT/'data/dev').glob('D*'))),
                'test_tasks':len(list((ROOT/'data/test').glob('T*'))),
                'provider_url_configured':bool(os.environ.get('MAS_LLM_BASE_URL')),
                'provider_key_configured':bool(os.environ.get('MAS_LLM_API_KEY')),
                'real_model_called':False}
    elif args.command=='check':
        paths=list((ROOT/'data').glob('*/'+args.task_id))
        if len(paths)!=1:raise ValueError('Unknown public task ID')
        task,code,cases=load_task(paths[0])
        if args.code:code=Path(args.code).read_text(encoding='utf-8')
        result=run_checks(code,cases)
    elif args.command=='freeze':result=freeze(args.config,args.policies,args.out)
    elif args.command=='run':result=run(args)
    elif args.command=='summary':result=summarize(args.out)
    else:result=close_interrupted(args.out)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError,KeyError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        sys.exit(2)

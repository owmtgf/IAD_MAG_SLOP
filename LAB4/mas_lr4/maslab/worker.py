"""Standalone restricted runner. Invoked with python -I; no provider credentials.

This is a deliberately small Python dialect, not a general security sandbox.
Never use it as the sole isolation boundary for untrusted orchestrator code.
"""
import ast
import builtins
import copy
import json
import math
import sys

NODES = set('Module FunctionDef arguments arg Return Assign AugAssign Expr For While '
            'If Break Continue Pass Raise Name Load Store Constant List Tuple Dict Set '
            'ListComp DictComp SetComp GeneratorExp comprehension Lambda IfExp '
            'Subscript Slice Call keyword Attribute BinOp UnaryOp BoolOp Compare '
            'Add Sub Mult Div FloorDiv Mod Pow BitOr BitAnd USub UAdd Not And Or '
            'Eq NotEq Lt LtE Gt GtE In NotIn Is IsNot'.split())
METHODS = set('append extend insert pop remove sort reverse copy get items keys values '
              'setdefault update count index join split strip lstrip rstrip lower upper '
              'startswith endswith replace isdigit add discard difference intersection '
              'union issubset'.split())
BUILTINS = set('abs all any bool dict enumerate float int isinstance len list max min '
               'next range reversed round set sorted str sum tuple zip '
               'ValueError TypeError KeyError IndexError'.split())

class ContractError(Exception):
    pass

def check_ast(code):
    if len(code.encode()) > 40000:
        raise ContractError('code exceeds 40000 bytes')
    tree = ast.parse(code)
    if not tree.body or not all(isinstance(n,ast.FunctionDef) for n in tree.body):
        raise ContractError('only function definitions at module level')
    if not any(n.name == 'solve' for n in tree.body):
        raise ContractError('def solve(data) is required')
    for n in ast.walk(tree):
        if type(n).__name__ not in NODES:
            raise ContractError('forbidden syntax: '+type(n).__name__)
        if isinstance(n,ast.Name) and (n.id.startswith('_') and n.id != '_'):
            raise ContractError('private names forbidden')
        if isinstance(n,(ast.FunctionDef,ast.arg)):
            name = n.name if isinstance(n,ast.FunctionDef) else n.arg
            if name.startswith('_') and name != '_':
                raise ContractError('private names forbidden')
        if isinstance(n,ast.FunctionDef) and (n.decorator_list or n.returns):
            raise ContractError('decorators and annotations forbidden')
        if isinstance(n,ast.arg) and n.annotation:
            raise ContractError('annotations forbidden')
        if isinstance(n,ast.Attribute) and n.attr not in METHODS:
            raise ContractError('forbidden attribute: '+n.attr)
        if isinstance(n,ast.Call) and not isinstance(n.func,(ast.Name,ast.Attribute)):
            raise ContractError('indirect call forbidden')
    return tree

def same(a,b):
    if type(a) is not type(b):
        return False
    if isinstance(a,dict):
        return a.keys() == b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,list):
        return len(a) == len(b) and all(same(x,y) for x,y in zip(a,b))
    return a == b

def json_value(value, depth=0):
    if depth > 60:
        return False
    if value is None or type(value) in (bool,int,str):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(json_value(v,depth+1) for v in value)
    if type(value) is dict:
        return all(type(k) is str and json_value(v,depth+1) for k,v in value.items())
    return False

def evaluate(code,cases):
    tree = check_ast(code)
    ns = {'__builtins__':{k:getattr(builtins,k) for k in BUILTINS}}
    exec(compile(tree,'<candidate>','exec'),ns)
    if not callable(ns.get('solve')):
        raise ContractError('solve is not callable')
    events = [0]
    def trace(frame,event,arg):
        if event == 'line' and frame.f_code.co_filename == '<candidate>':
            events[0] += 1
            if events[0] > 200000:
                raise ContractError('execution step limit')
        return trace
    results = []
    for case in cases:
        events[0] = 0
        observations = []
        changed = False
        for repeat in range(2):
            value = copy.deepcopy(case['input'])
            try:
                sys.settrace(trace)
                got = ns['solve'](value)
                sys.settrace(None)
                if not json_value(got):
                    obs = {'invalid_output':'only finite JSON values are allowed'}
                else:
                    obs = {'value':copy.deepcopy(got)}
            except Exception as exc:
                sys.settrace(None)
                obs = {'raises':type(exc).__name__}
            finally:
                sys.settrace(None)
            changed = changed or not same(value,case['input'])
            observations.append(obs)
        wanted = {'raises':case['raises']} if 'raises' in case else {'value':case['expected']}
        deterministic = same(observations[0],observations[1])
        ok = not changed and deterministic and same(observations[0],wanted)
        results.append({'id':case['id'],'passed':ok,'expected':wanted,
                        'actual':observations[0],'input_changed':changed,
                        'deterministic':deterministic})
    return {'passed':all(r['passed'] for r in results), 'total':len(results),
            'passed_count':sum(r['passed'] for r in results),'cases':results}

def main():
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
            resource.setrlimit(resource.RLIMIT_CPU,(3,3))
            resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
            resource.setrlimit(resource.RLIMIT_NOFILE,(16,16))
        except ImportError:
            pass
        payload = json.loads(sys.stdin.read(2000000))
        result = evaluate(payload['code'],payload['cases'])
        out = json.dumps(result,ensure_ascii=False,allow_nan=False)
        if len(out.encode()) > 1000000:
            out = json.dumps({'passed':False,'error':'output_limit'})
        print(out)
    except BaseException as exc:
        print(json.dumps({'passed':False,'error':type(exc).__name__+': '+str(exc)[:300]}))

if __name__ == '__main__':
    main()

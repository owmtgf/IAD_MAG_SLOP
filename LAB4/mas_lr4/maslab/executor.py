import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

def digest(code):
    return hashlib.sha256(code.encode('utf-8')).hexdigest()

def run_checks(code,cases,timeout=5):
    started = time.monotonic()
    worker = Path(__file__).with_name('worker.py').resolve()
    # Deliberate allowlist; API keys and the parent's Python path are absent.
    env = {k:os.environ[k] for k in ('SYSTEMROOT','WINDIR') if k in os.environ}
    env.update({'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'})
    with tempfile.TemporaryDirectory(prefix='maslab-') as work:
        try:
            proc = subprocess.run([sys.executable,'-I',str(worker)],
                input=json.dumps({'code':code,'cases':cases}), text=True,
                encoding='utf-8',capture_output=True,cwd=work,env=env,timeout=timeout)
            if proc.returncode or len(proc.stdout.encode()) > 1000000:
                result = {'passed':False,'error':'worker_failed','returncode':proc.returncode}
            else:
                result = json.loads(proc.stdout)
                if type(result) is not dict or type(result.get('passed')) is not bool:
                    raise ValueError('invalid worker report')
        except subprocess.TimeoutExpired:
            result = {'passed':False,'error':'timeout'}
        except (ValueError,OSError) as exc:
            result = {'passed':False,'error':type(exc).__name__}
    result.update({'code_sha256':digest(code),'seconds':round(time.monotonic()-started,6)})
    return result

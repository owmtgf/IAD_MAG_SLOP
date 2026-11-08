"""Create a verified submission ZIP from an explicit public-file allowlist."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {'README.md', 'SUBMISSION_README.md', 'config.json',
             'freeze.json', 'extra_freeze.json', 'advanced_freeze.json'}
TOP_FOLDERS = {'maslab', 'advanced', 'data', 'prompts', 'docs', 'tests',
               'scripts', 'runs', 'analysis', 'report'}
DENIED_PARTS = {'__pycache__', '.git', '.venv', 'venv', 'node_modules',
                'teacher', '.aws', '.codex', '.agents', '.pytest_cache'}
DENIED_SUFFIXES = {'.pyc', '.pyo', '.zip', '.pem', '.key', '.p12', '.pfx',
                   '.safetensors', '.pt', '.pth', '.bin'}


def allowed(path):
    relative = path.relative_to(ROOT)
    if any(part in DENIED_PARTS or part.startswith('.env') for part in relative.parts):
        return False
    if path.suffix.lower() in DENIED_SUFFIXES:
        return False
    if relative.parts[:2] == ('report', 'build'):
        return False
    if relative.parts[0] == 'report':
        return relative.as_posix() in {'report/LAB4_report.md', 'report/LAB4_report.pdf'}
    if len(relative.parts) == 1:
        return relative.name in TOP_FILES
    return relative.parts[0] in TOP_FOLDERS


def main():
    subprocess.run([sys.executable, str(ROOT / 'scripts/final_analysis.py')], cwd=ROOT, check=True)
    if not (ROOT / 'report/LAB4_report.md').is_file():
        raise SystemExit('Missing report/LAB4_report.md')
    paths = sorted(path for path in ROOT.rglob('*') if path.is_file() and allowed(path))
    inventory = []
    for path in paths:
        if path.is_symlink():
            raise SystemExit('Refusing symlink: ' + str(path))
        data = path.read_bytes()
        # Fail rather than print a possible credential. Fixture strings are not
        # real keys, and no environment variables or home files are collected.
        if re.search(rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}', data):
            raise SystemExit('Possible API key in: ' + str(path.relative_to(ROOT)))
        if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', data):
            raise SystemExit('Private key in: ' + str(path.relative_to(ROOT)))
        inventory.append((path, hashlib.sha256(data).hexdigest()))
    destination = ROOT.parent / 'LAB4_submission.zip'
    if destination.exists():
        raise SystemExit('Archive already exists; preserve it or choose a new version before packaging')
    sums = ''.join(f'{digest}  mas_lr4/{path.relative_to(ROOT).as_posix()}\n' for path, digest in inventory)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, _ in inventory:
            archive.write(path, 'mas_lr4/' + path.relative_to(ROOT).as_posix())
        archive.writestr('SUBMISSION_FILES.sha256', sums)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise SystemExit('ZIP CRC validation failed')
        for path, digest in inventory:
            name = 'mas_lr4/' + path.relative_to(ROOT).as_posix()
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise SystemExit('ZIP content hash mismatch: ' + name)
        for folder, expected in [('final', 600), ('extra', 72), ('advanced', 24)]:
            count = sum(name.startswith(f'mas_lr4/runs/{folder}/episodes/') and
                        name.endswith('/result.json') for name in archive.namelist())
            if count != expected:
                raise SystemExit(f'Archive matrix mismatch: {folder}: {count}/{expected}')
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.zip.sha256').write_text(digest + '  ' + destination.name + '\n')
    print(json.dumps({'archive': str(destination), 'files': len(inventory) + 1,
                      'bytes': destination.stat().st_size, 'sha256': digest,
                      'verified_final_episodes': 696}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

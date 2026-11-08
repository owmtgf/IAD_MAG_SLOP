"""Build the two-page PDF with XeLaTeX; does not call a model."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    for executable in ('xelatex', 'pdfinfo', 'pdftotext'):
        if not shutil.which(executable):
            raise SystemExit('Required executable not found: ' + executable)
    with tempfile.TemporaryDirectory(prefix='lab4-report-') as tmp:
        build = Path(tmp)
        environment = dict(os.environ, XDG_CACHE_HOME=str(build / 'cache'),
                           TEXMFVAR=str(build / 'texmf-var'), TEXMFCONFIG=str(build / 'texmf-config'))
        logs = []
        for _ in range(2):
            result = subprocess.run([
                'xelatex', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error',
                '-output-directory=' + str(build), str(ROOT / 'report/report.tex'),
            ], cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            logs.append(result.stdout)
            if result.returncode:
                print(result.stdout)
                raise SystemExit(result.returncode)
        info = subprocess.check_output(['pdfinfo', str(build / 'report.pdf')], text=True)
        if not re.search(r'^Pages:\s+2\s*$', info, re.MULTILINE):
            raise SystemExit('Report must contain exactly two pages:\n' + info)
        text = subprocess.check_output(['pdftotext', str(build / 'report.pdf'), '-'], text=True)
        if 'Межмодульная ошибка' not in text or 'ЛР4.' not in text:
            raise SystemExit('PDF text extraction failed')
        if 'Overfull \\hbox' in logs[-1] or 'Missing character:' in logs[-1]:
            raise SystemExit('Report has overflowing lines or missing glyphs')
        destination = ROOT / 'report/LAB4_report.pdf'
        shutil.copyfile(build / 'report.pdf', destination)
        log_folder = ROOT / 'analysis/final'
        log_folder.mkdir(parents=True, exist_ok=True)
        (log_folder / 'report_build.log').write_text('\n'.join(logs), encoding='utf-8')
        (log_folder / 'report_pdfinfo.txt').write_text(info, encoding='utf-8')
        print(str(destination), '(2 pages)')


if __name__ == '__main__':
    main()

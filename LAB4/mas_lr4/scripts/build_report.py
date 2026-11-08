"""Build a PDF duplicate of the Markdown report using XeLaTeX."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def escape(text):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%',
                    '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{',
                    '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(char, char) for char in text)


def inline(text):
    parts = re.split(r'(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))', text)
    result = []
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            result.append(r'\textbf{' + escape(part[2:-2]) + '}')
        elif part.startswith('`') and part.endswith('`'):
            result.append(r'\texttt{' + escape(part[1:-1]) + '}')
        elif re.fullmatch(r'\[[^\]]+\]\([^)]+\)', part):
            label, target = re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)', part).groups()
            result.append(r'\href{' + escape(target) + '}{' + escape(label) + '}')
        else:
            result.append(escape(part))
    return ''.join(result)


def latex(markdown, size):
    lines = markdown.splitlines()
    body = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith('```'):
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith('```'):
                code.append(lines[index])
                index += 1
            body.append('\\begingroup\\fontsize{8}{9.5}\\selectfont\n\\begin{verbatim}\n' +
                        '\n'.join(code) + '\n\\end{verbatim}\n\\endgroup')
        elif line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].startswith('|'):
                cells = [cell.strip() for cell in lines[index].strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', cell) for cell in cells):
                    rows.append(cells)
                index += 1
            columns = len(rows[0])
            spec = '@{}l' + ('l' if columns >= 6 else '') + (
                r'>{\raggedleft\arraybackslash}X' * (columns - (2 if columns >= 6 else 1))) + '@{}'
            table = [r'\par\begingroup\fontsize{8.2}{9.5}\selectfont',
                     r'\begin{tabularx}{\linewidth}{' + spec + '}', r'\toprule']
            for number, cells in enumerate(rows):
                table.append(' & '.join(inline(cell) for cell in cells) + r'\\')
                if number == 0:
                    table.append(r'\midrule')
            table += [r'\bottomrule', r'\end{tabularx}\endgroup\par']
            body.append('\n'.join(table))
            continue
        elif line.startswith('# '):
            body.append(r'{\sffamily\bfseries\Large ' + inline(line[2:]) + '}\par')
        elif line.startswith('## '):
            if line == '## Парное сравнение':
                body.append(r'\newpage')
            body.append(r'\par\vspace{4pt}{\sffamily\bfseries ' + inline(line[3:]) + '}\par')
        elif line.strip():
            body.append(inline(line))
        else:
            body.append(r'\par')
        index += 1
    preamble = r'''\documentclass[10pt,a4paper]{article}
\usepackage[margin=14mm]{geometry}
\usepackage{fontspec}
\setmainfont{DejaVuSerif.ttf}[Path=/usr/share/fonts/truetype/dejavu/,BoldFont=DejaVuSerif-Bold.ttf]
\setsansfont{DejaVuSans.ttf}[Path=/usr/share/fonts/truetype/dejavu/,BoldFont=DejaVuSans-Bold.ttf]
\setmonofont{DejaVuSansMono.ttf}[Path=/usr/share/fonts/truetype/dejavu/]
\usepackage{polyglossia}
\setmainlanguage{russian}
\usepackage{booktabs,tabularx,array}
\usepackage[unicode,hidelinks,pdfauthor={},pdftitle={ЛР4. Один агент и две MAS}]{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3pt}
\setlength{\tabcolsep}{3pt}
\setlength{\emergencystretch}{2em}
\begin{document}
'''
    return preamble + f'\\fontsize{{{size}}}{{{size + 1.1}}}\\selectfont\n' + '\n'.join(body) + '\n\\end{document}\n'


def main():
    for tool in ('xelatex', 'pdfinfo', 'pdftotext'):
        if not shutil.which(tool):
            raise SystemExit('Missing executable: ' + tool)
    markdown = (ROOT / 'report/LAB4_report.md').read_text()
    with tempfile.TemporaryDirectory(prefix='lab4-markdown-pdf-') as folder:
        build = Path(folder)
        environment = dict(os.environ, XDG_CACHE_HOME=str(build / 'cache'),
                           TEXMFVAR=str(build / 'texmf-var'), TEXMFCONFIG=str(build / 'texmf-config'))
        for size in (9.5, 9.0, 8.5):
            (build / 'report.tex').write_text(latex(markdown, size))
            for _ in range(2):
                result = subprocess.run(['xelatex', '-no-shell-escape', '-interaction=nonstopmode',
                    '-halt-on-error', '-output-directory=' + str(build), str(build / 'report.tex')],
                    cwd=ROOT, env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if result.returncode:
                    raise SystemExit(result.stdout[-6000:])
            info = subprocess.check_output(['pdfinfo', str(build / 'report.pdf')], text=True)
            pages = int(re.search(r'^Pages:\s+(\d+)', info, re.MULTILINE).group(1))
            if pages <= 2:
                break
        else:
            raise SystemExit('Report exceeds two pages')
        text = subprocess.check_output(['pdftotext', str(build / 'report.pdf'), '-'], text=True)
        for phrase in ('696', 'Qwen3.5-4B', 'Межмодульная ошибка', '105 077'):
            if phrase not in text:
                raise SystemExit('PDF content check failed: ' + phrase)
        if '/home/' in text or '192.168.' in text or 'Missing character:' in result.stdout:
            raise SystemExit('Unwanted local details or missing glyphs in PDF')
        destination = ROOT / 'report/LAB4_report.pdf'
        shutil.copyfile(build / 'report.pdf', destination)
        print(f'{destination}: {pages} pages, generated from LAB4_report.md')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Rebuild the editorial note from released evidence. Requires Pandoc and XeLaTeX.

This never performs inference or changes scientific records. Refresh SHA256SUMS
only after reviewing the generated files; run verify.py afterwards.
"""
from pathlib import Path
import json
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://aryan-gupta123.github.io/feedback-lab-demo/'


def build():
    data = json.loads((ROOT / 'replay.json').read_text())
    rows = ['| Checkpoint | Source | Difference (bp) | Descriptive 95% interval |',
            '| --- | --- | ---: | --- |']
    for key, label in [('qwen3_4b', 'Qwen3-4B'), ('qwen25_7b', 'Qwen2.5-7B')]:
        for condition, name in [('reliable', 'Reliable'), ('noise', 'Noise'), ('inverted', 'Inverted')]:
            value = data['analysis']['models'][key]['contrasts'][condition]['versus_own_public']
            rows.append(f"| {label} | {name} | {value['mean_bp']:+.2f} | [{value['ci95_bp'][0]:+.2f}, {value['ci95_bp'][1]:+.2f}] |")
    path = ROOT / 'research-note.md'
    text, n = re.subn(r'(?s)(<!-- primary-contrasts:start -->).*?(<!-- primary-contrasts:end -->)',
                      lambda m: m[1] + '\n\n' + '\n'.join(rows) + '\n\n' + m[2], path.read_text())
    if n != 1:
        raise ValueError('Expected one primary-contrasts table marker pair')
    path.write_text(text)
    subprocess.run(['pandoc', str(path), '--from=gfm', '--to=html5', '--standalone',
                    '--metadata', 'pagetitle=Valid JSON. Unreliable decisions.',
                    '--template=' + str(ROOT / 'assets/research-note-template.html'),
                    '--output=' + str(ROOT / 'research-note.html')], check=True)
    pdf_text = re.sub(r'(?<!!)\[([^\]]+)\]\((?!https?://|#)([^)]+)\)',
                      lambda m: f'[{m[1]}]({BASE}{m[2]})', text)
    with tempfile.TemporaryDirectory(prefix='feedback-note-') as folder:
        source = Path(folder) / 'note.md'
        source.write_text(pdf_text)
        subprocess.run(['pandoc', str(source), '--from=gfm', '--pdf-engine=xelatex',
                        '--resource-path=' + str(ROOT), '-V', 'geometry:margin=0.8in',
                        '-V', 'fontsize=11pt', '-V', 'mainfont=DejaVu Serif',
                        '-V', 'monofont=DejaVu Sans Mono', '-V', 'colorlinks=true',
                        '-V', 'urlcolor=teal', '--output=' + str(ROOT / 'research-note.pdf')], check=True)
    print('Built research-note.html and research-note.pdf from the released primary contrasts; zero inference requests.')


if __name__ == '__main__':
    build()

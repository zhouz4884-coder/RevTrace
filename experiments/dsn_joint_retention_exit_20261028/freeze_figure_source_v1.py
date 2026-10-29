"""Freeze a complete CPU-only source checkout before summary/figure execution."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
root = HERE / 'figure_source_v1'
root.mkdir(exist_ok=False)
for name in ['summarize_and_plot_v1.py']:
    shutil.copyfile(HERE / name, root / name)
(root / '.gitignore').write_text('__pycache__/\n*.pyc\n', encoding='utf8')
(root / 'PROTOCOL.md').write_text(
    'CPU-only summary of the complete frozen 24-cell R x K campaign. Retain all cells, original D2/C8, '
    'all-offered denominators, complete-history comparisons, quality and energy. No pooled P99, invented '
    'confidence intervals, natural-fault prevalence or assumed positive interaction. Plots show all three '
    'temporal repetitions at both preselected phases. Independent recount code is aa4e01af1a9c49df435fdefd479b9ed50cc45fbe; '
    'this source only summarizes its complete recorded output and plots bounded evidence.\n', encoding='utf8')
subprocess.run(['git', '-C', str(root), 'init'], check=True, capture_output=True)
def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
git('config', 'core.autocrlf', 'false')
git('checkout', '-b', 'codex/dsn-joint-retention-exit-figure-v1')
git('add', '.')
git('commit', '-m', 'Freeze all-cell retention and coverage-exit summary figure')
manifest = dict(code_commit=git('rev-parse', 'HEAD'), scope='CPU-only all-cell R x K summary and figure',
                files=[dict(path=name, bytes=(root/name).stat().st_size,
                            sha256=hashlib.sha256((root/name).read_bytes()).hexdigest())
                       for name in git('ls-files').splitlines()])
with (HERE / 'FIGURE_SOURCE_v1.json').open('x', encoding='utf8') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
git('bundle', 'create', str(HERE/'FIGURE_SOURCE_v1.bundle'), 'HEAD')
assert not git('status', '--porcelain', '--untracked-files=all')
print(json.dumps(manifest))

from pathlib import Path
import shutil,json
E=Path(__file__).resolve().parent;A=E/'figure_source_v2';B=E/'figure_source_v3'
assert not B.exists();shutil.copytree(A,B,ignore=shutil.ignore_patterns('.git','__pycache__'))
p=B/'render_editorial_figures.py';s=p.read_text(encoding='utf8');assert 'axes[1].text(.985,.94' in s
p.write_bytes(s.replace('axes[1].text(.985,.94','axes[1].text(.985,.50').encode())
p=B/'CONFIG.json';d=json.loads(p.read_bytes());d['experiment_id']='DSN_EDITORIAL_DELTA_FIGURES_20261101_LABEL_LAYOUT'
p.write_bytes((json.dumps(d,indent=2)+'\n').encode())
s=(E/'freeze_figure_source_v2.py').read_text(encoding='utf8')
for a,b in [('figure_source_v2','figure_source_v3'),('FIGURE_SOURCE_v2','FIGURE_SOURCE_v3'),('figure_snapshot_v2','figure_snapshot_v3'),('FIGURE_ENVIRONMENT_v2','FIGURE_ENVIRONMENT_v3'),('FIGURE_FREEZE_v2','FIGURE_FREEZE_v3'),('20261101-v2','20261101-v3'),('FIGURES_v2','FIGURES_v3')]:s=s.replace(a,b)
(E/'freeze_figure_source_v3.py').write_bytes(s.encode())
print('Prepared one-position label correction; unchanged underlying data and prior outputs')

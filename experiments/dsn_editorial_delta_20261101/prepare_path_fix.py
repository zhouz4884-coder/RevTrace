from pathlib import Path
import shutil,json
E=Path(__file__).resolve().parent
A=E/'figure_source_dev';B=E/'figure_source_v2'
assert not B.exists();shutil.copytree(A,B,ignore=shutil.ignore_patterns('.git','__pycache__'))
p=B/'render_editorial_figures.py';s=p.read_text(encoding='utf8')
old="sha(HERE/'inputs/ACTUAL_INTERVAL_COMPARISON.json')"
new="sha(HERE/next(r['copy'] for r in json.loads((HERE/'SOURCE_MAP.json').read_bytes())['bounded_inputs'] if r['key']=='actual_interval_comparison'))"
assert old in s;p.write_bytes(s.replace(old,new).encode())
p=B/'CONFIG.json';d=json.loads(p.read_bytes());d['experiment_id']='DSN_EDITORIAL_DELTA_FIGURES_20261101_PATH_FIX'
p.write_bytes((json.dumps(d,indent=2)+'\n').encode())
s=(E/'freeze_figure_source.py').read_text(encoding='utf8')
for a,b in [("S=E/'figure_source_dev'","S=E/'figure_source_v2'"),('FIGURE_SOURCE.json','FIGURE_SOURCE_v2.json'),('FIGURE_SOURCE.bundle','FIGURE_SOURCE_v2.bundle'),("'figure_snapshot'","'figure_snapshot_v2'"),('FIGURE_ENVIRONMENT.json','FIGURE_ENVIRONMENT_v2.json'),('FIGURE_FREEZE.json','FIGURE_FREEZE_v2.json'),('dsn-editorial-figures-20261101','dsn-editorial-figures-20261101-v2'),("E/'FIGURES'","E/'FIGURES_v2'"),('FIGURES/SUMMARY.json','FIGURES_v2/SUMMARY.json'),('FIGURES/GATE.json','FIGURES_v2/GATE.json')]:s=s.replace(a,b)
(E/'freeze_figure_source_v2.py').write_bytes(s.encode())
print('Prepared minimal metadata-path fix; old frozen source preserved')

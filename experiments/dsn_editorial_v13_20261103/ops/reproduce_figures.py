"""Reproduce editorial figures from the accompanying anonymous frozen inputs."""
from pathlib import Path
import argparse, csv, hashlib, importlib.util, json
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'output_figures');a=p.parse_args()
manifest=json.loads((ROOT/'MANIFEST.json').read_bytes())
for row in manifest['files']:
 path=ROOT/row['path'];assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],row['path']
source=ROOT/'figure_source/render.py';spec=importlib.util.spec_from_file_location('frozen_figures',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a.out.mkdir(parents=True,exist_ok=False);m.style();load=lambda n:json.loads((ROOT/'figure_source/inputs'/n).read_bytes())
rows=list(csv.DictReader((ROOT/'figure_source/inputs/pairs.csv').open(encoding='utf-8-sig',newline='')))
results=[m.case(a.out,load('case.json')),m.mechanism(a.out),m.core(a.out,load('core.json')),m.native(a.out,load('native.json')),m.pairs(a.out,rows,load('native_report.json'))]
(a.out/'REPRODUCED.json').write_text(json.dumps(dict(gate='PASS_ANONYMOUS_FROZEN_FIGURES',figures=results,new_model_calls=0),indent=2)+'\n',encoding='utf-8')
print('PASS: reproduced four main figures and one artifact-only paired-effect figure; no models or raw journals read.')

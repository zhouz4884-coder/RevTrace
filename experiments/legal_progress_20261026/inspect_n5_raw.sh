set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - "$B" <<'PY'
import pathlib,json,sys
b=pathlib.Path(sys.argv[1]);r=b/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
print('root_exists',r.exists());print('children',[p.name for p in r.iterdir() if p.is_dir()])
for f in [r/s/'SUMMARY.json' for s in ['formal_normal','formal_fault','recovery_development']]:
 if not f.exists():continue
 x=json.loads(f.read_text());print(str(f),{k:v for k,v in x.items() if k not in ['completed','cells']})
 if isinstance(x.get('completed'),list) and x['completed']:
  z=x['completed'][0];print('first',z)
  if isinstance(z,str):
   e=f.parent/z
   if e.exists():print('episode_dirs',[p.name for p in e.iterdir() if p.is_dir()]);print('configs',[str(p) for p in e.glob('*/config.json')])
for f in r.glob('*/FREEZE.json'):
 x=json.loads(f.read_text());print('FREEZE',str(f),'keys',list(x),'cell0',x.get('cells',[None])[0])
PY

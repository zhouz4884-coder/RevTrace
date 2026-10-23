"""Independent original pure-Python statistics on the actual collected bank."""
from pathlib import Path
import collections,csv,hashlib,json,sys,time
import numpy as np
W=Path(__file__).resolve().parent;A=W/'collected/evidence/formal_v1_independent_audit_final'
from analysis_core import paired_bootstrap as original
from row_stats_core import paired_bootstrap as vector
def csvread(p):return list(csv.DictReader(p.open()))
cells=csvread(A/'SERVICE_CELLS.csv');fronts=csvread(A/'COMMON_FRONTIERS.csv');quality=csvread(A/'SOURCE_QUALITY.csv')
assert len(cells)==180
bycell={c['cell']:c for c in cells};fs=collections.defaultdict(list);qs=collections.defaultdict(dict)
for f in fronts:fs[f['cell']].append({k:(None if f[k]=='' else float(f[k])) for k in ['audio_seconds','display','commit']}|{'source_id':f['source_id']})
for q in quality:qs[q['cell']][q['source_id']]={k:int(v) for k,v in q.items() if k not in ['source_id','cell']}
def arm(arrival,method):
 out={}
 for repeat in range(3):
  name=f'validation-{arrival}-mixed-{method}-r{repeat}';c=bycell[name]
  out[repeat]={'wall':float(c['wall_seconds']),'energy':float(c['GPU_J_audio_s']),
   'sources':{s:dict(q,frontiers=[f for f in fs[name] if f['source_id']==s]) for s,q in qs[name].items()}}
 return out
stored=json.loads((W/'collected/evidence/FORMAL_RESULTS_v1/PAIRED_MIXED_COMPARISONS.json').read_text())
checked=[];started=time.time()
for arrival in ['sync','staggered']:
 for baseline in ['fine','strict','standard','readiness','ready_any','cost_gate','cost','causal_only']:
  args=(arm(arrival,baseline),arm(arrival,'ces'));samples=10000 if baseline in ['fine','cost'] else 1000
  a=original(args,samples=samples,seed=20261023);b=vector(args,samples=samples,seed=20261023)
  for section in ['paired_median','paired_95_interval']:
   for k in a[section]:np.testing.assert_allclose(a[section][k],b[section][k],rtol=1e-12,atol=1e-12)
  official=next(x['effect'] for x in stored if x['pool']=='validation' and x['arrival']==arrival and x['baseline']==baseline)
  full=vector(args,samples=10000,seed=20261023)
  for section in ['paired_median','paired_95_interval','paired_99_84375_interval']:
   for k in full[section]:np.testing.assert_allclose(full[section][k],official[section][k],rtol=1e-12,atol=1e-12)
  checked.append({'arrival':arrival,'baseline':baseline,'original_pure_Python_samples':samples,'full_10k_official_recomputed':True})
  print('MATCHED',arrival,baseline,samples,flush=True)
out={'status':'PASS_ACTUAL_INDEPENDENT_PURE_PYTHON_AND_FULL_BOOTSTRAP_RECOMPUTATION','pairs':checked,
 'tolerance':1e-12,'seconds':time.time()-started,'new_GPU_calls':0,
 'scope':'actual independent-source Mixed records; no queue or model resimulation',
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(W/'INDEPENDENT_ACTUAL_RECOMPUTE.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

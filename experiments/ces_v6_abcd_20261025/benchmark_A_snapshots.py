"""Same real snapshots: exact decisions and alternating CPU timing, not GPU benefit."""
from pathlib import Path
import argparse,copy,csv,gzip,hashlib,json,statistics,sys,time
W=Path(__file__).resolve().parent;old=W.parent/'ces_v5_closed_loop_20261025'
sys.path[:0]=[str(W/'runtime/src'),str(old)]
from revtrace.ces_closed_loop import ClosedLoopState,Identity,ServiceRecord,PlannerConfig,choose_closed_loop
from revtrace.ces_v5_policy import V5Target
from audit_closed_helpers_v2 import restore_context
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=W/'A_snapshot_benchmark_v1');ap.add_argument('--repeats',type=int,default=3);a=ap.parse_args()
assert not a.output.exists();a.output.mkdir()
norm=lambda v:json.dumps(json.loads(json.dumps(v,allow_nan=False)),sort_keys=True,allow_nan=False)
def read(p):return json.loads(p.read_text())
def restore(v):
 s=ClosedLoopState(scope=tuple(v['scope']));s.dispatches=v['actual_dispatches']
 for r in v['records']:
  x=dict(r);k=Identity(**x.pop('identity'));s.records[k]=ServiceRecord(**x)
 for x in v['symbolic_continuation_intents']:s.continuation_intents[x['sid'],x['epoch'],x['contract_digest'],x['frontier_end']]=dict(x)
 return s
out=[];inputs=[]
for p in sorted((old/'collected/formal_cpu_snapshot_profile_v1').glob('*decision-*.json')):
 x=read(p);c=old/'collected/cell_metadata/formal'/x['cell']/'config.json.gz'
 with gzip.open(c,'rt') as f:cfg=json.load(f)
 obs=x['observation'];record=x['recorded_decision'];contexts={int(k):restore_context(v['target_context']) for k,v in obs['contexts'].items()};targets=[V5Target(**v) for v in x['features']]
 state=restore(obs['service_book']);cal=cfg['ces_study']['calibration'];measured={'reference':[],'memoized':[]}
 for rep in range(a.repeats):
  for mode in (['reference','memoized'] if rep%2==0 else ['memoized','reference']):
   conf=dict(cfg['ces_study']['closed_loop_config'],cache_mode=mode)
   s=copy.deepcopy(state);begin=time.perf_counter()
   y=choose_closed_loop(targets,contexts,now=record['observed_perf'],mode=cfg['ces_study']['method'],cal=cal,limit=cfg['microbatch'],
       observed_credit_audio=obs['observed_credit_audio'],elapsed_seconds=obs['elapsed_seconds'],state=s,display_slo=2.,config=PlannerConfig(**conf))
   elapsed=time.perf_counter()-begin
   for k,v in y.items():assert norm(v)==norm(record[k]),(p.name,mode,k)
   measured[mode].append(elapsed)
 out.append({'snapshot':p.name,'cell':x['cell'],'all_fields_exact':True,'reference_median_s':statistics.median(measured['reference']),
   'memoized_median_s':statistics.median(measured['memoized']),'speedup':statistics.median(measured['reference'])/statistics.median(measured['memoized'])})
 inputs.append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
with (a.output/'TIMINGS.csv').open('w',newline='',encoding='utf8') as f:
 z=csv.DictWriter(f,fieldnames=list(out[0]));z.writeheader();z.writerows(out)
report={'status':'PASS_EXACT_REAL_SNAPSHOT_CPU_CACHE_REPLAY','snapshots':len(out),'timing_repeats':a.repeats,
 'median_speedup':statistics.median(r['speedup'] for r in out),'reference_median_s':statistics.median(r['reference_median_s'] for r in out),
 'memoized_median_s':statistics.median(r['memoized_median_s'] for r in out),'new_GPU_calls':0,'timing_scope':'pure choose CPU; original Owner context build/logging excluded; no end-to-end speedup claim',
 'inputs':inputs,'source_sha256':hashlib.sha256((W/'runtime/src/revtrace/ces_closed_loop.py').read_bytes()).hexdigest()}
(a.output/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='inputs'}))

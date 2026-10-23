"""Local host-cost fixtures for the actual V5 planner, not serving results."""
from pathlib import Path
import argparse,hashlib,json,platform,statistics,sys,time
W=Path(__file__).resolve().parent
sys.path.insert(0,str(W/'runtime/src'))
from revtrace.ces_v5_policy import V5Target,choose_v5,_row_cdf
parser=argparse.ArgumentParser()
parser.add_argument('--output',default='CPU_PLANNER_COST.json')
parser.add_argument('--calibration',default='calibration_v2/CALIBRATION.json')
args=parser.parse_args()
calpath=W/args.calibration
cal=json.loads(calpath.read_text())
rows=[]
for n in [1,4,8,16]:
 for fraction in [0.,.5,1.]:
  ts=[V5Target(i,5,8.,16.,i<int(n*fraction),i%2==0,False,24+i,0,0.,None,
      audio_seconds=10.+i*.2,interval_seconds=2.,prompt_tokens=20+i,
      display_met=i%3==0,display_expired=False,audio_weight=2.) for i in range(n)]
  for mode in ['risk_cost','progress']:
   times=[];decision=None
   for rep in range(6):
    if rep==0:_row_cdf.cache_clear()
    start=time.perf_counter();decision=choose_v5(ts,now=9.,mode=mode,cal=cal,limit=16);times.append(time.perf_counter()-start)
   rows.append({'tasks':n,'candidate_fraction':fraction,'mode':mode,
     'cold_ms':1000*times[0],'warm_median_ms':1000*statistics.median(times[1:]),
     'warm_max_ms':1000*max(times[1:]),'plans':decision['partitions_evaluated'],
     'scenario_combinations_selected_plan':decision['scenario_combinations'],
     'plans_fully_evaluated':decision.get('plans_fully_evaluated'),
     'plans_pruned_by_model_bound':decision.get('plans_pruned_by_model_bound')})
out={'evidence':'Windows CPU host benchmark on constructed features, not GPU or production overhead',
 'python':sys.version,'platform':platform.platform(),'GPU_calls':0,'repeats':6,
 'calibration_sha256':hashlib.sha256(calpath.read_bytes()).hexdigest(),
 'source_sha256':hashlib.sha256((W/'runtime/src/revtrace/ces_v5_policy.py').read_bytes()).hexdigest(),
 'rows':rows}
dest=W/args.output;assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))

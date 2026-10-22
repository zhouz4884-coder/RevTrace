from pathlib import Path
import csv,json,statistics as st
from collections import defaultdict
W=Path(__file__).resolve().parent;rows=list(csv.DictReader((W/'OLD_DEMAND_AND_WAITS.csv').open()));groups=defaultdict(list)
for r in rows:
 if r['stage']=='N_T1_v4' and '-decoupled-' in r['cell'] or r['stage']=='D_R4_strict' and r['cell'].startswith(('Fine-D','Coarse-D')):
  groups[r['stage'],r['cell'].rsplit('-r',1)[0]].append(r)
out=[]
for (stage,case),rs in groups.items():
 x={'stage':stage,'case':case,'n':len(rs)}
 for k in ['dedup_worker_service_seconds','dedup_model_call_seconds','coverage_accumulation_wait_median','ready_to_enqueue_p99','eligible_to_enqueue_p99','gpu_execution_job_median','commit_P99_common_frontier','GPU_J_audio_s']:
  x[k]=st.median(float(r[k]) for r in rs)
 out.append(x)
(W/'OLD_CROSS_TRENDS.json').write_text(json.dumps({'rows':out,'not_one_pooled_matched_workload':True,'C2_original_contribution_not_downgraded_by_elastic_gate':True},indent=2)+'\n');print(json.dumps(out))

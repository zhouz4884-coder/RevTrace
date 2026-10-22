"""Recompute finite-window authority demand and common-frontier waits, not simulation."""
from pathlib import Path
import csv,json,statistics as st
from collections import defaultdict
W=Path(__file__).resolve().parent;N=Path(r'D:\StreamTxn\outputs\revtrace_phaseN_20261021');D=Path(r'D:\StreamTxn\outputs\revtrace_phaseD_20261021\collected_final');rows=[]
def record(a,stage,cell):
 jobs=a['authority_lifecycles'];distinct={(r['worker_started'],r['worker_completed']) for r in jobs};models={(r['gpu_started'],r['gpu_completed']) for r in jobs if r['gpu_started'] is not None};frontiers=a['common_frontiers']
 row={'stage':stage,'cell':cell,'authority_targets':len(jobs),'actual_authority_batches':len(distinct),'dedup_worker_service_seconds':sum(b-a for a,b in distinct),'dedup_model_call_seconds':sum(b-a for a,b in models),'audio_seconds':sum(p['weight_seconds'] for p in frontiers),'display_P99_server_common_frontier':a['display_p99'],'commit_P99_common_frontier':a['commit_p99'],'xRT':a['xrt'],'GPU_J_audio_s':a['gpu_j_per_audio_second']}
 for key in ['coverage_accumulation_wait','ready_to_enqueue','ready_to_eligible','eligible_to_enqueue']:
  vals=[r[key] for r in frontiers if r[key] is not None];row[key+'_median']=st.median(vals);row[key+'_p99']=sorted(vals)[int(.99*(len(vals)-1))]
 for key in ['enqueue_to_worker_start','worker_preprocessing','gpu_execution','delivery','owner_wal_call']:
  v=[r[key] for r in jobs if r[key] is not None];row[key+'_job_median']=st.median(v) if v else None
 rows.append(row)
for a in json.loads((N/'collected/t1_v4/INDEPENDENT_AUDIT_SUMMARY.json').read_text())['cells']:
 if '-obs1-' in a['cell']:record(a,'N_T1_v4',a['cell'])
for stage in ['R4_scout','R4_strict']:
 for p in (D/stage).glob('*/INDEPENDENT_AUDIT.json'):record(json.loads(p.read_text()),'D_'+stage,p.parent.name)
with (W/'OLD_DEMAND_AND_WAITS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(W/'OLD_DEMAND_AND_WAITS.json').write_text(json.dumps({'rows':rows,'scope':'same-workload within declared cell families; T1 uses old repeated source pool, R4 new independent nested source sets; not one pooled crossover','job_medians_duplicate_batch_span_not_device_utilization':True},indent=2)+'\n')
print('recomputed',len(rows),'old cells')

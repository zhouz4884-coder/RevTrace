"""Small transparent grouped/paired view of already audited cell CSVs."""
from pathlib import Path
import csv,json,statistics
W=Path(__file__).resolve().parent
with (W/'precollection/SERVICE_CELLS.csv').open(newline='',encoding='utf8') as f:rows=list(csv.DictReader(f))
metrics=['Audio_Goodput_2_8','Audio_Goodput_stable_2_8','display_P99','commit_P99','GPU_J_audio_s','WER','CER',
         'verified_rows','rejected_rows','fallback_rows','planner_wall_s','capped_authority_admissions','unfinished_sources','obsolete_private_jobs']
g={}
for r in rows:g.setdefault((r['cell'].split('-')[1],r['method']),[]).append(r)
for key,rr in sorted(g.items()):
 print(json.dumps({'arrival':key[0],'method':key[1],'runs':len(rr),'whole_run_dual_passes':sum(r['dual_P99_2_8_pass']=='True' for r in rr),
                   **{k:statistics.median(float(r[k]) for r in rr) for k in metrics}}))
for arrival in ['sync','staggered']:
 for t,b in [('causal','fine'),('causal','cost'),('causal','inherit'),('inherit','reserved_progress'),
             ('causal_joint','cost_joint'),('causal_joint','fine'),('causal_joint','causal'),
             ('fine_shared_progress','fine'),('standard_shared_progress','standard'),('cost_joint','cost')]:
  tr={r['cell'].rsplit('-r',1)[1]:r for r in g[arrival,t]};br={r['cell'].rsplit('-r',1)[1]:r for r in g[arrival,b]}
  delta={k:[float(tr[i][k])/float(br[i][k])-1 for i in sorted(tr)] for k in ['Audio_Goodput_2_8','GPU_J_audio_s','display_P99','commit_P99']}
  print(json.dumps({'paired':True,'arrival':arrival,'treatment':t,'baseline':b,'changes':delta,'paired_median':{k:statistics.median(v) for k,v in delta.items()}}))

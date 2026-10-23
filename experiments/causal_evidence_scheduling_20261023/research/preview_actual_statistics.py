"""Local CPU preview of actual audited metrics; input replay gate still pending."""
from pathlib import Path
import collections,csv,json
from row_stats_core import paired_bootstrap
W=Path(__file__).resolve().parent
def rd(n):return list(csv.DictReader((W/n).open()))
cells={c['cell']:c for c in rd('FORMAL_SERVICE_CELLS_PREVIEW.csv')}
fronts=collections.defaultdict(list);quality=collections.defaultdict(dict)
for f in rd('FORMAL_COMMON_FRONTIERS_PREVIEW.csv'):
 fronts[f['cell']].append({'source_id':f['source_id'],**{k:(None if f[k]=='' else float(f[k])) for k in ['display','commit','audio_seconds']}})
for q in rd('FORMAL_SOURCE_QUALITY_PREVIEW.csv'):
 quality[q['cell']][q['source_id']]={k:int(v) for k,v in q.items() if k not in ['cell','source_id']}
def arm(arrival,mode):
 out={}
 for r in range(3):
  name=f'validation-{arrival}-mixed-{mode}-r{r}';c=cells[name]
  out[r]={'wall':float(c['wall_seconds']),'energy':float(c['GPU_J_audio_s']),
   'sources':{s:dict(q,frontiers=[f for f in fronts[name] if f['source_id']==s]) for s,q in quality[name].items()}}
 return out
rows=[]
for arrival in ['sync','staggered']:
 for baseline in ['fine','strict','standard','readiness','ready_any','cost_gate','cost','causal_only']:
  e=paired_bootstrap((arm(arrival,baseline),arm(arrival,'ces')),samples=10000,seed=20261023)
  rows.append({'arrival':arrival,'baseline':baseline,'effect':e})
  print(json.dumps({'arrival':arrival,'baseline':baseline,'point':e['paired_median'],'95':e['paired_95_interval']}),flush=True)
(W/'ACTUAL_STATISTICS_LOCAL_PREVIEW.json').write_text(json.dumps({'status':'ACTUAL_METRIC_PREVIEW_INPUT_REPLAY_AND_FINAL_GATES_PENDING','comparisons':rows,'new_GPU_calls':0},indent=2)+'\n')

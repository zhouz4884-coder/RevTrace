"""Only physical service clocks/batch sizes. Never reads Z/P/transcript/ref text."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,statistics,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/elastic_20261022';F=O/'stress_scout';assert (O/'STRESS_SCOUT_SUMMARY.json').exists()
groups=defaultdict(list);samples=[]
def q(values,p):
 v=sorted(values);i=(len(v)-1)*p;k=int(i);return v[k]+(v[min(k+1,len(v)-1)]-v[k])*(i-k)
for c in sorted(F.iterdir()):
 if not (c/'result.json').exists():continue
 cfg=json.loads((c/'config.json').read_text());rho=cfg['rho'];es=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];seen=set();sizes={}
 for e in es:
  if e['kind']=='batch-dispatched' and e['role']=='authority':
   for jid in e['job_ids']:sizes[jid]=len(e['job_ids'])
 for e in es:
  if e['kind']!='executor-complete' or e['role']!='authority':continue
  key=(e['started'],e['completed'])
  if key in seen:continue
  seen.add(key);n=sizes[e['job_id']];service=e['completed']-e['started'];groups[rho,n].append(service);samples.append({'cell':c.name,'rho':rho,'batch_rows':n,'worker_service_seconds':service,'gpu_model_seconds':e['gpu_model_completed']-e['gpu_model_started']})
table=[{'rho':r,'batch_rows':n,'n_batches':len(v),'median_seconds':statistics.median(v),'p90_seconds':q(v,.9)} for (r,n),v in sorted(groups.items())]
out={'scope':'past service calibration only, not a neural-output or dynamic Oracle','dynamic_algorithm_implemented':False,'input_event_hashes':{c.name:hashlib.sha256((c/'events.jsonl').read_bytes()).hexdigest() for c in F.iterdir() if (c/'events.jsonl').exists()},'table':table,'samples':samples,'no_quality_labels_or_Z_P_used':True,'model':'piecewise-linear interpolation over measured batch sizes, linear endpoint extrapolation above maximum, fixed within later evaluation; median for capacity, p90 for deadline heuristic'}
(O/'SERVICE_CALIBRATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'calibrated_batches':len(samples),'table_cells':len(table)}))

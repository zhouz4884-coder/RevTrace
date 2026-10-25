"""Paired whole-run effects with explicit source reuse and small-n uncertainty."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,json,math,random,statistics,hashlib

def readcsv(p):
 with p.open(newline='') as f:rows=list(csv.DictReader(f))
 for r in rows:
  for k,v in r.items():
   if v in ['True','False']:r[k]=v=='True'
   else:
    try:r[k]=float(v)
    except ValueError:pass
 return rows
def q(xs,p):
 xs=sorted(xs);pos=(len(xs)-1)*p;i=int(pos);return xs[i] if i==len(xs)-1 else xs[i]+(pos-i)*(xs[i+1]-xs[i])
def paired(base,new,key):
 assert set(base)==set(new)
 absolute=key in ['WER','CER'];values=[]
 for i in sorted(base):
  x,y=base[i][key],new[i][key]
  if not absolute and x<=0:return {'status':'ZERO_BASE_REPORTED_WITHOUT_RATIO','base':[base[i][key] for i in sorted(base)],'new':[new[i][key] for i in sorted(new)]}
  values.append(y-x if absolute else y/x-1)
 rng=random.Random(20261025);bs=[statistics.mean(rng.choices(values,k=len(values))) for _ in range(10000)]
 # n3 t interval is intentionally wider than a percentile bootstrap.
 critical={2:12.706,3:4.303,4:3.182,5:2.776,6:2.571}.get(len(values),2.262)
 mean=statistics.mean(values);se=statistics.stdev(values)/math.sqrt(len(values)) if len(values)>1 else math.inf
 return {'status':'PAIRED_WHOLE_RUN_DESCRIPTIVE','n':len(values),'values':values,'mean':mean,'median':statistics.median(values),'bootstrap_mean_95':[q(bs,.025),q(bs,.975)],'small_n_t95':[mean-critical*se,mean+critical*se],'all_positive':all(v>0 for v in values),'not_independent_sources':True}
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--stage',required=True);a=p.parse_args();O=a.root
 summary=json.loads((O/(a.stage+'_SUMMARY.json')).read_text());assert summary['status']=='COMPLETE_GPU_MATRIX_AND_SAFETY_AUDIT'
 rows=readcsv(O/(a.stage+'_audit')/'SERVICE_CELLS.csv');costs=readcsv(O/(a.stage+'_audit')/'PHYSICAL_COSTS.csv');groups=defaultdict(list)
 for r in rows:
  pool,arrival,traffic=r['cell'].split('-',3)[:3];r.update(pool=pool,arrival=arrival,traffic=traffic,repeat=int(r['cell'].rsplit('-r',1)[1]))
  for role in ['proposal','authority']:
   c=next(c for c in costs if c['cell']==r['cell'] and c['role']==role)
   for key in ['physical_batches','worker_service_s','physical_model_calls']:r[role+'_'+key]=c[key]
  groups[pool,arrival,traffic,r['method']].append(r)
 aggregates=[]
 keys=['Audio_Goodput_2_8','Audio_Goodput_stable_2_8','display_P99','commit_P99','GPU_J_audio_s','WER','CER','planner_wall_s','feature_wall_s','proposal_worker_service_s','authority_worker_service_s','verified_rows','fallback_rows','obsolete_private_jobs','physical_fsyncs']
 for g,rs in groups.items():
  aggregates.append({'pool':g[0],'arrival':g[1],'traffic':g[2],'method':g[3],'runs':len(rs),'dual_P99_passes':sum(r['dual_P99_2_8_pass'] for r in rs),'authority_caps':sum(r['capped_authority_admissions'] for r in rs),'unfinished':sum(r['unfinished_sources'] for r in rs),**{k+'_median':statistics.median(r[k] for r in rs) for k in keys}})
 effects=[]
 for pool,arrival,traffic,method in sorted(groups):
  choices=['fine','v5_reference','cached'] if a.stage=='A' else ['fine','standard']
  for baseline in choices:
   key=pool,arrival,traffic,baseline
   if baseline==method or key not in groups:continue
   x={r['repeat']:r for r in groups[key]};y={r['repeat']:r for r in groups[pool,arrival,traffic,method]}
   if set(x)!=set(y):continue
   effects.append({'pool':pool,'arrival':arrival,'traffic':traffic,'base':baseline,'new':method,'metrics':{k:paired(x,y,k) for k in keys}})
 A=O/(a.stage+'_summary');A.mkdir()
 with (A/'GROUPS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(aggregates[0]));w.writeheader();w.writerows(aggregates)
 report={'status':'COMPLETE_PAIRED_WHOLE_RUN_SUMMARY','stage':a.stage,'runs':len(rows),'source_cohort':'new speaker-audited confirmation' if a.stage=='D_heldout' else 'reused development audio','groups':aggregates,'paired':effects,'small_n_warning':'Three repeats estimate schedule variability on a shared16-source cohort; neither frontier count nor repeats are independent new audio samples. Intervals are not a population guarantee.','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (A/'SUMMARY.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({'stage':a.stage,'runs':len(rows),'groups':aggregates}))
if __name__=='__main__':main()

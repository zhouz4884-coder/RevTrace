"""Read-only timing decomposition of already completed online GPU measurements."""
from collections import defaultdict
from pathlib import Path
import csv
import hashlib
import json
import statistics

W=Path(__file__).resolve().parent
E=W/'collected_evidence_v1'
A=E/'collected/formal_v1_audit_v3'
D=W/'C2_BOTTLENECK_v1'
D.mkdir(exist_ok=False)

def rows(name):
 p=A/name
 expected=next(r for r in json.loads((E/'MANIFEST.json').read_text())['files']
               if r['path']==p.relative_to(E).as_posix())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==expected['sha256']
 return list(csv.DictReader(p.open(newline='',encoding='utf-8')))

def num(r,k):return float(r[k])
def quant(xs,q):
 xs=sorted(xs); pos=(len(xs)-1)*q;i=int(pos)
 return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(pos-i) if xs else None
def med(xs):return statistics.median(xs)
def save(name,x):(D/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def csvsave(name,rs):
 with (D/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)

cells=rows('SERVICE_CELLS.csv');costs=rows('COST_DECOMPOSITION.csv')
frontiers=rows('COMMON_FRONTIERS.csv');jobs=rows('JOB_CLOCKS.csv')
selection=rows('SELECTION_AND_ADMISSION.csv');phases=rows('PHYSICAL_MODEL_PHASES.csv')
assert len(cells)==72
byfront=defaultdict(list);byjob=defaultdict(list);byphase=defaultdict(list)
for r in frontiers:byfront[r['cell']].append(r)
for r in jobs:byjob[r['cell'],r['role']].append(r)
for r in phases:byphase[r['cell'],r['role']].append(r)
source_select=defaultdict(list);clock={(r['cell'],r['job_id']):r for r in jobs}
for r in selection:source_select[r['cell'],r['source_id']].append(r)
for rs in source_select.values():rs.sort(key=lambda r:int(r['audio_end_sample']))
bycell={r['cell']:r for r in cells};cellout=[];rolem=[];parts=[]
for c in cells:
 name=c['cell'];load=name.split('-')[1];fs=byfront[name]
 weight=defaultdict(float);part=[]
 for f in fs:
  dp=num(f,'display')<=2;cp=num(f,'commit')<=8
  status='pass' if dp and cp else 'display_only_miss' if not dp and cp else 'commit_only_miss' if dp else 'both_miss'
  weight[status]+=num(f,'audio_seconds')
  sel=next(r for r in source_select[name,f['source_id']] if int(r['audio_end_sample'])>=int(f['frontier_sample']))
  j=clock[name,sel['job_id']];end=int(sel['audio_end_sample'])/16000
  q=int(f['frontier_sample'])/16000;offset=num(f,'release')-q
  t0=num(j,'audio_ready_perf')-offset-end
  parent=int(sel['parent'])
  previous=next((r for r in source_select[name,f['source_id']] if int(r['version'])==parent),None)
  parent_ready=t0+num(previous,'installed') if previous else t0
  eligible=max(num(j,'audio_ready_perf'),parent_ready)
  decomposed={
   'intentional_audio_accumulation_s':end-q,
   'parent_after_audio_s':max(0.,parent_ready-num(j,'audio_ready_perf')),
   'eligible_to_enqueue_s':num(j,'enqueue_perf')-eligible,
   'worker_queue_s':num(j,'worker_queue_s'),
   'worker_service_s':num(j,'worker_service_s'),
   'completion_to_owner_s':num(j,'completion_to_owner_receipt_s'),
   'owner_received_to_install_s':t0+num(sel,'installed')-num(j,'owner_received_perf')}
  assert min(decomposed.values())>=-1e-6
  assert abs(sum(decomposed.values())-num(f,'commit'))<1e-6
  r={'cell':name,'method':c['method'],'load':load,'traffic':c['traffic'],
     'source_id':f['source_id'],'frontier_sample':f['frontier_sample'],'audio_seconds':num(f,'audio_seconds'),
     'display_s':num(f,'display'),'commit_s':num(f,'commit'),'status':status,
     'authority_job_id':sel['job_id'],**decomposed}
  parts.append(r);part.append(r)
 total=num(c,'audio_seconds')
 out={'cell':name,'method':c['method'],'load':load,'traffic':c['traffic'],
      'repeat':int(name.rsplit('r',1)[1]),'audio_seconds':total,'wall_s':num(c,'wall_seconds'),
      'raw_audio_throughput':total/num(c,'wall_seconds'),'goodput':num(c,'Audio_Goodput_2_8'),
      'qualifying_audio_fraction':weight['pass']/total,
      **{k+'_audio_s':weight[k] for k in ['pass','display_only_miss','commit_only_miss','both_miss']},
      'render_host_wall_s':num(c,'render_host_wall_s'),'wal_owner_wall_s':num(c,'wal_owner_wall_s'),
      'fsync_s':num(c,'physical_fsync_s'),'consumer_cpu_s':num(c,'consumer_cpu_s'),
      'commits':int(c['certified_commits'])}
 for k in decomposed:
  out[k+'_audio_weighted_mean']=sum(r[k]*r['audio_seconds'] for r in part)/total
  out[k+'_frontier_p99']=quant([r[k] for r in part],.99)
 cellout.append(out)
 for role in ['proposal','authority']:
  js=byjob[name,role];ps=byphase[name,role]
  cost=next(r for r in costs if r['cell']==name and r['role']==role)
  rolem.append({'cell':name,'method':c['method'],'load':load,'traffic':c['traffic'],'role':role,
   'row_jobs':len(js),'physical_model_seconds':sum(num(r,'seconds') for r in ps),
   'physical_worker_seconds':num(cost,'worker_service_seconds'),
   'physical_model_calls':len(ps),'physical_rows_sum':sum(int(r['physical_rows']) for r in ps),
   'model_duration_p50_s':quant([num(r,'seconds') for r in ps],.5),
   'model_duration_p99_s':quant([num(r,'seconds') for r in ps],.99),
   'new_tokens_total':sum(int(r['new_tokens']) for r in js),
   'new_tokens_p99':quant([int(r['new_tokens']) for r in js],.99),
   'row_enqueue_delay_p99_s':quant([num(r,'audio_ready_to_enqueue_s') for r in js],.99),
   'row_worker_service_p99_s':quant([num(r,'worker_service_s') for r in js],.99),
   'row_receipt_delay_p99_s':quant([num(r,'completion_to_owner_receipt_s') for r in js],.99),
   'capped_row_jobs':sum(r['hit_token_limit']=='True' for r in js)})

csvsave('CELL_DECOMPOSITION.csv',cellout);csvsave('ROLE_COSTS.csv',rolem)
csvsave('FRONTIER_COMMIT_DECOMPOSITION.csv',parts)
groups=[]
for key in sorted({(r['load'],r['traffic'],r['method']) for r in cellout}):
 rs=[r for r in cellout if (r['load'],r['traffic'],r['method'])==key]
 out=dict(zip(['load','traffic','method'],key))
 for k,v in rs[0].items():
  if isinstance(v,(int,float)):out[k+'_median']=med([r[k] for r in rs])
 groups.append(out)
csvsave('GROUP_DECOMPOSITION.csv',groups)
role_groups=[]
for key in sorted({(r['load'],r['traffic'],r['method'],r['role']) for r in rolem}):
 rs=[r for r in rolem if (r['load'],r['traffic'],r['method'],r['role'])==key]
 out=dict(zip(['load','traffic','method','role'],key))
 for k,v in rs[0].items():
  if isinstance(v,(int,float)):out[k+'_median']=med([r[k] for r in rs])
 role_groups.append(out)
csvsave('GROUP_ROLE_COSTS.csv',role_groups)
save('SUMMARY.json',{'status':'PASS_POSTHOC_TABLE_CLOCK_DECOMPOSITION','formal_cells':72,
 'common_frontiers':len(parts),'all_commit_decompositions_match_original':True,
 'source_tables_verified_against_original_manifest':True,
 'physical_batch_times_not_row_time_sums':True,
 'scope':'descriptive existing real GPU records; no new GPU or causal repair counterfactual',
 'not_a_changed_performance_gate':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
for r in groups:
 if r['method'] in ['fine','dgft']:
  print(json.dumps({k:r[k] for k in ['load','traffic','method','raw_audio_throughput_median','qualifying_audio_fraction_median',
    'display_only_miss_audio_s_median','commit_only_miss_audio_s_median','both_miss_audio_s_median',
    'intentional_audio_accumulation_s_audio_weighted_mean_median','worker_service_s_frontier_p99_median',
    'eligible_to_enqueue_s_frontier_p99_median','wal_owner_wall_s_median']}))
for r in role_groups:
 if r['method'] in ['fine','dgft'] and r['load']=='sync16':print(json.dumps(r))

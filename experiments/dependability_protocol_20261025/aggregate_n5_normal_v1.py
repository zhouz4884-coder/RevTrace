"""All frozen groups and whole-run paired comparisons; no winner filtering."""
from pathlib import Path
import argparse,csv,hashlib,itertools,json,math,statistics
def read(p):return json.loads(p.read_text())
def median(v):return statistics.median(v)
def exported(x):return x if not isinstance(x,float) or math.isfinite(x) else None
def quantile(v,q):
 v=sorted(v);p=(len(v)-1)*q;i=int(p);j=min(i+1,len(v)-1)
 return v[i]+(v[j]-v[i])*(p-i)
def descriptive_bootstrap(v):
 # Three timing repeats are not hundreds of independent windows. This tiny
 # discrete bootstrap is descriptive, not a p-value or proof of superiority.
 if any(x is None for x in v):return None
 values=[median([v[i] for i in indices]) for indices in itertools.product(range(3),repeat=3)]
 return [quantile(values,.025),quantile(values,.975)]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 a.output.mkdir(exist_ok=False);raw=read(a.root/'postnormal_cpu_v1/primary/SUMMARY.json');freeze=read(a.root/'formal_normal/FREEZE.json')
 assert raw['cells']==105 and raw['status']=='PASS_INDEPENDENT_INPUT_AND_ACTUAL_VIEW_RECOUNT'
 rows={r['episode']:r for r in raw['episodes']};group={};all_cells={}
 for c in freeze['cells']:
  name=f"{c['method']}-{c['workload']}-r{c['repeat']}";r=rows[name]
  assert r['method']==c['method'] and r['sources']==c['load'] and not r['unauthorized_admissions']
  group.setdefault((c['workload'],c['method']),{})[c['repeat']]=r;all_cells[name]=c
 assert set(rows)==set(all_cells) and len(group)==35
 for workload in {w for w,m in group}:
  related=[r for (w,m),reps in group.items() if w==workload for r in reps.values()]
  assert len({(r['sources'],r['whole_offered_frontiers'],r['WER_reference_words']) for r in related})==1
 groups=[];comparisons=[]
 metrics=['all_offered_audio_goodput_2_8','GPU_J_per_offered_audio_second','GPU_J_per_certified_audio_second',
  'display_P50','display_P95','display_P99','commit_view_P50','commit_view_P95','commit_view_P99',
  'final_certified_audio_coverage','valid_provisional_ahead_coverage_per_offered_audio','explicit_rejected_offered_audio_seconds',
  'uncompleted_offered_audio_seconds','all_offered_WER_percent','all_offered_character_error_percent',
  'exact_unadmitted_offered_peak_audio_seconds','accepted_debt_peak_audio_seconds','reserved_debt_peak_audio_seconds',
  'exact_pending_unaccepted_peak_audio_seconds','canonical_commit_group_fsync_calls','canonical_commit_group_fsync_seconds',
  'input_fsync_seconds','controller_CPU_seconds','consumer_CPU_seconds','trusted_render_host_wall_seconds',
  'actual_row_emission_to_owner_receive_P99','actual_publication_to_Consumer_applied_P99','consumer_audio_rollback_events']
 for (workload,method),rep in sorted(group.items()):
  assert set(rep)=={0,1,2};rs=[rep[i] for i in range(3)]
  out=dict(workload=workload,method=method,runs=3,sources=rs[0]['sources'],frontiers=rs[0]['whole_offered_frontiers'],
   whole_run_dual_P99_passes=sum(r['whole_run_dual_P99_pass'] for r in rs),
   infinite_display_P99_runs=sum(r['display_P99'] is None for r in rs),infinite_commit_P99_runs=sum(r['commit_view_P99'] is None for r in rs))
  for key in metrics:
   values=[(math.inf if r[key] is None and key.startswith(('display_','commit_')) else r[key]) for r in rs]
   out[key+'_each']=[exported(x) for x in values]
   out[key+'_median']=None if any(x is None for x in values) else exported(median(values))
  groups.append(out)
 ordinary=['fine_fair','dgft_original','standard_fair','queue_expiry']
 for workload in sorted({w for w,m in group}):
  best=max(ordinary,key=lambda m:median(group[workload,m][i]['all_offered_audio_goodput_2_8'] for i in range(3)))
  fair=max(['standard_fair','queue_expiry'],key=lambda m:median(group[workload,m][i]['all_offered_audio_goodput_2_8'] for i in range(3)))
  for control in ordinary+['cde_age','standard_cde']:
   xs=[group[workload,'cde_full'][i] for i in range(3)];ys=[group[workload,control][i] for i in range(3)]
   differences=[x['all_offered_audio_goodput_2_8']-y['all_offered_audio_goodput_2_8'] for x,y in zip(xs,ys)]
   relative=[100*(x['all_offered_audio_goodput_2_8']/y['all_offered_audio_goodput_2_8']-1) if y['all_offered_audio_goodput_2_8'] else None for x,y in zip(xs,ys)]
   q=[x['WER_errors']<=y['WER_errors'] and x['all_offered_character_error_percent']<=y['all_offered_character_error_percent']+1e-12 for x,y in zip(xs,ys)]
   comparisons.append(dict(workload=workload,comparison='cde_full vs '+control,control_is_best_ordinary_Goodput=control==best,
    control_is_best_same_budget_coarse_Goodput=control==fair,paired_Goodput_delta_each=differences,
    paired_Goodput_delta_median=median(differences),paired_Goodput_percent_each=relative,
    paired_Goodput_percent_median=None if any(v is None for v in relative) else median(relative),
    descriptive_n3_bootstrap_percentile95_Goodput_delta=descriptive_bootstrap(differences),
    quality_no_worse_each=q,all_three_Goodput_positive=all(d>0 for d in differences),
    all_three_WER_and_CER_no_worse=all(q),
    paired_energy_per_offered_audio_delta_each=[x['GPU_J_per_offered_audio_second']-y['GPU_J_per_offered_audio_second'] for x,y in zip(xs,ys)],
    paired_whole_run_SLO_pass_difference=sum(x['whole_run_dual_P99_pass']-y['whole_run_dual_P99_pass'] for x,y in zip(xs,ys))))
 result=dict(status='COMPLETE_ALL35_GROUPS_30_PAIRED_COMPARISONS_REQUIRES_SCIENTIFIC_REVIEW',groups=groups,comparisons=comparisons,
  limitations='three repeated whole runs on one frozen disjoint-speaker pool; range/descriptive bootstrap is not a significance p-value; no window pseudo-replication; null latency means infinity',
  no_automatic_promotion=True,original_contracts_preserved=True,
  primary_summary_sha256=hashlib.sha256((a.root/'postnormal_cpu_v1/primary/SUMMARY.json').read_bytes()).hexdigest(),
  aggregator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 (a.output/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 for name,records in [('GROUPS.csv',groups),('PAIRED.csv',comparisons)]:
  with (a.output/name).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows([{k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in records])
 print(json.dumps(dict(groups=35,paired_comparisons=30,no_automatic_promotion=True)))
if __name__=='__main__':main()

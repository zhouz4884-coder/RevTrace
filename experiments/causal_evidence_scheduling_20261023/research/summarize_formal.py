"""Frozen paired Mixed comparisons; retain every clean/high descriptive row."""
from pathlib import Path
import collections,csv,hashlib,json,statistics,sys
from row_stats_core import paired_bootstrap
W=Path(__file__).resolve().parent;B=Path(sys.argv[1]);O=B/'results/revtrace/ces_20261023';D=O/'FORMAL_RESULTS_v1';D.mkdir(exist_ok=False)
A=O/'formal_v1_independent_audit_final'
def csvread(p):return list(csv.DictReader(p.open()))
def write(p,rows):
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
cells=csvread(A/'SERVICE_CELLS.csv');fronts=csvread(A/'COMMON_FRONTIERS.csv');quality=csvread(A/'SOURCE_QUALITY.csv');costs=csvread(A/'PHYSICAL_COSTS.csv')
assert len(cells)==180
bycell={c['cell']:c for c in cells};grouped=collections.defaultdict(list)
for c in cells:
 c['candidate_wait_after_target_eligible_s']=c['candidate_wait_before_eligibility_seconds'] # legacy raw column misnomer; formula is post-eligibility wait
 c['commit_path_fsyncs']=c['physical_fsyncs'] # timed observer excludes initial genesis/directory setup
 pool,arrival,traffic,method,rep=c['cell'].split('-');c.update(pool=pool,arrival=arrival,repeat=int(rep[1:]))
 grouped[pool,arrival,traffic,method].append(c)
 for role in ['proposal','authority']:
  k=next(x for x in costs if x['cell']==c['cell'] and x['role']==role)
  c[role+'_physical_batches']=k['physical_batches'];c[role+'_physical_model_calls']=k['physical_model_calls'];c[role+'_service_s']=k['worker_service_s']
group_rows=[]
numeric=['Audio_Goodput_2_8','display_P50','display_P95','display_P99','commit_P50','commit_P95','commit_P99','GPU_J_audio_s','WER','CER','verified_rows','accepted_rows','rejected_rows','fallback_rows','fallback_physical_calls','fallback_executed_rows','physical_fsyncs','obsolete_private_jobs','obsolete_private_generated_tokens','associated_private_physical_calls','associated_private_phase_envelope_s_not_exclusive','planner_wall_s','feature_wall_s','direct_consumed_F2_jobs','candidate_wait_before_eligibility_seconds','verified_target_release_to_enqueue_seconds','proposal_physical_batches','authority_physical_batches','proposal_physical_model_calls','authority_physical_model_calls','proposal_service_s','authority_service_s','consumer_cpu_s','consumer_queue_max_depth','peak_sampled_GPU0_MiB','peak_sampled_GPU1_MiB']
numeric=[k for k in numeric if k not in ['physical_fsyncs','candidate_wait_before_eligibility_seconds']]+['commit_path_fsyncs','candidate_wait_after_target_eligible_s']
for key,cs in sorted(grouped.items()):
 expected=3 if key[2]=='mixed' else 1;assert len(cs)==expected
 group_rows.append(dict(zip(['pool','arrival','traffic','method'],key),repeats=len(cs),
  dual_P99_passes=sum(c['dual_P99_2_8_pass']=='True' for c in cs),
  **{k:statistics.median(float(c[k]) for c in cs) for k in numeric}))
write(D/'GROUPS.csv',group_rows)
fs=collections.defaultdict(list);qs=collections.defaultdict(dict)
for f in fronts:
 fs[f['cell']].append({'source_id':f['source_id'],**{k:(None if f[k]=='' else float(f[k])) for k in ['audio_seconds','display','commit']}})
for q in quality:qs[q['cell']][q['source_id']]={k:int(v) for k,v in q.items() if k not in ['cell','source_id']}
def arms(pool,arrival,method):
 runs={}
 for c in grouped[pool,arrival,'mixed',method]:
  sources={s:dict(q,frontiers=[f for f in fs[c['cell']] if f['source_id']==s]) for s,q in qs[c['cell']].items()}
  assert len(sources)==16
  runs[c['repeat']]={'wall':float(c['wall_seconds']),'energy':float(c['GPU_J_audio_s']),'sources':sources}
 return runs
comparisons=[];gates=[];baselines=['fine','strict','standard','readiness','ready_any','cost_gate','cost','causal_only']
for pool in ['development','validation']:
 for arrival in ['sync','staggered']:
  for baseline in baselines:
   a,b=arms(pool,arrival,baseline),arms(pool,arrival,'ces')
   effect=paired_bootstrap((a,b),samples=10000,seed=20261023)
   directions=[float(bycell[f'{pool}-{arrival}-mixed-ces-r{r}']['Audio_Goodput_2_8'])>float(bycell[f'{pool}-{arrival}-mixed-{baseline}-r{r}']['Audio_Goodput_2_8']) for r in range(3)]
   point=effect['paired_median'];ci=effect['paired_95_interval'];sim=effect['paired_99_84375_interval']
   quality_ok=all(point[k]<=0 and ci[k][1]<=.005 for k in ['WER','CER'])
   goodput=quality_ok and all(directions) and sim['goodput'][0]>0
   energy=quality_ok and point['energy']<=-.10 and sim['energy'][1]<0 and sim['goodput'][0]>=-.02
   comparisons.append({'pool':pool,'arrival':arrival,'traffic':'mixed','baseline':baseline,'new':'ces','effect':effect,
      'all3_goodput_positive':all(directions),'quality_point_not_worse_and_0_5pp_NI':quality_ok})
   gates.append({'pool':pool,'arrival':arrival,'baseline':baseline,'quality':quality_ok,'Goodput_GO':goodput,'energy_GO':energy,
     'Goodput_delta':point['goodput'],'Goodput_95_lo':ci['goodput'][0],'Goodput_95_hi':ci['goodput'][1],
     'Goodput_simultaneous_lo':sim['goodput'][0],'energy_delta':point['energy'],
     'WER_delta':point['WER'],'CER_delta':point['CER'],'all3_goodput_positive':all(directions)})
save(D/'PAIRED_MIXED_COMPARISONS.json',comparisons);write(D/'GATES.csv',gates)
strong=[]
for arrival in ['sync','staggered']:
 gs=[g for g in gates if g['pool']=='validation' and g['arrival']==arrival]
 strong.append({'arrival':arrival,'Goodput_all8':all(g['Goodput_GO'] for g in gs),'energy_all8':all(g['energy_GO'] for g in gs)})
go=any(s['Goodput_all8'] or s['energy_all8'] for s in strong)
out={'experiment_id':'REVTRACE-CES-FORMAL-v1','status':'ALL180_EXECUTED_AND_METRIC_AUDIT_PASS',
 'independent_new_C2_algorithm':'GO_CONDITIONAL_MEASURED_REGIME' if go else 'NO_GO_REQUIRED_INDEPENDENT_INCREMENT_NOT_ESTABLISHED',
 'independent_arrival_gates':strong,'formal_cells':180,'mixed_repeats':3,'clean_high_repeats':1,
 'clean_high_are_descriptive_not_repeatability_claims':True,'unique_sources':32,'independent_validation_sources':16,
 'statistical_scope':'same-source/repeat paired10k bootstrap conditional on actual schedules; no queue resimulation',
 'simultaneous_bands':'Bonferroni32 for8 baselines x2 validation arrivals x2 endpoint routes; pointwise quality NI separately reported',
 'no_Goodput_or_energy_success_from_shared_row_executor_alone':True,
 'all_original_C1_C2_C3_negative_boundaries_retained':True,'no_paper_edits':True,
 'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
save(D/'GO_NO_GO.json',out);print(json.dumps(out,indent=2))

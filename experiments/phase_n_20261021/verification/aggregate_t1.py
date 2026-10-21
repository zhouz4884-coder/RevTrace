"""Aggregate audited paired runs; bootstrap keeps repeated slots clustered by source."""
import argparse,csv,json,statistics
from collections import defaultdict
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
audit=json.loads(a.audit.read_text());cells=audit['cells'];assert len(cells)==18
rows={r['cell']:r for r in cells};groups=defaultdict(list);small=[]
for r in cells:
    mode,barrier,obs,repeat=r['cell'].split('-');groups[mode,barrier,obs].append(r)
    small.append({'cell':r['cell'],'mode':mode,'barrier':barrier,'observed':obs,'repeat':int(repeat[1:]),
        **{k:r[k] for k in ['xrt','display_p99','commit_p99','gpu_j_per_audio_second','wait_target_seconds','captured_worker_records']},
        'obsolete':r['counts'].get('obsolete_publication',0),
        'physical_self_exec_target_seconds':r['posthoc_physical_execution_target_seconds'],
        'physical_both_capacity_target_seconds':r['posthoc_both_execution_and_capacity_target_seconds'],
        'physical_fsync_target_seconds':r['posthoc_fsync_target_seconds']})
summary=[]
rng=np.random.default_rng(20261021)
for key,values in sorted(groups.items()):
    assert len(values)==3
    base={'mode':key[0],'barrier':key[1],'observed':key[2]}
    for metric in ['xrt','display_p99','commit_p99','gpu_j_per_audio_second']:
        data=[v[metric] for v in values];base[metric+'_median']=statistics.median(data);base[metric+'_range']=[min(data),max(data)]
    ci={};sources=sorted({p['source_id'] for v in values for p in v['common_frontiers']})
    for metric in ['ready_to_enqueue','ready_to_eligible','eligible_to_enqueue']:
        byrun=[{s:[p[metric] for p in v['common_frontiers'] if p['source_id']==s] for s in sources} for v in values]
        estimates=[]
        for _ in range(1000):
            chosen_runs=rng.integers(0,3,3);chosen_sources=rng.choice(sources,len(sources),replace=True)
            data=[x for run in chosen_runs for s in chosen_sources for x in byrun[run][s]]
            estimates.append(float(np.quantile(data,.5)))
        ci[metric]={'conditional_cluster_bootstrap_p50_95ci':np.quantile(estimates,[.025,.975]).tolist(),
            'per_run_quantiles':[v['common_frontier_stage_quantiles'][metric] for v in values]}
    base['stages']=ci;summary.append(base)
# Canonical exactness within rho, across all controls and repeats.
same_rho=[]
for mode in ['fine_certified','coarse']:
    matching=[r for r in cells if r['cell'].startswith(mode+'-')]
    exact=len({json.dumps(r['final_projection'],sort_keys=True) for r in matching})==1
    quality=len({json.dumps(r['quality'],sort_keys=True) for r in matching})==1
    same_rho.append({'mode':mode,'canonical_projection_exact':exact,'quality_exact':quality,'cells':len(matching)})
    assert exact and quality
pairs=[]
for mode in ['fine_certified','coarse']:
    for repeat in range(3):
        on=rows[f'{mode}-decoupled-obs1-r{repeat}'];off=rows[f'{mode}-decoupled-obs0-r{repeat}']
        pairs.append({'mode':mode,'repeat':repeat,'observed_over_control_xrt':on['xrt']/off['xrt'],
            'observed_over_control_commit_p99':on['commit_p99']/off['commit_p99'],
            'observed_over_control_display_p99':on['display_p99']/off['display_p99']})
a.out.mkdir(exist_ok=False)
for name,values in [('T1_CELLS.csv',small),('T1_INSTRUMENTATION_PAIRS.csv',pairs)]:
    with (a.out/name).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
result={'groups':summary,'same_rho_checks':same_rho,'instrumentation_pairs':pairs,
    'bootstrap_scope':'descriptive conditional run/source-cluster resampling; slots kept together; not independent population/speaker inference',
    'all_input_audits_pass':True}
(a.out/'T1_AGGREGATE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'same_rho':same_rho,'pairs':pairs},indent=2))

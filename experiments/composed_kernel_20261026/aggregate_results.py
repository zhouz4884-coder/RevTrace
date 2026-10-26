"""Post-freeze descriptive analysis. No validation-driven controller updates."""
from pathlib import Path
from collections import defaultdict
import argparse,json,csv,statistics
def read(p):return json.loads(p.read_text(encoding='utf8'))
def med(xs):return statistics.median(xs) if xs else None
def dumpcsv(p,rows):
    assert not p.exists()
    with p.open('w',newline='',encoding='utf8') as f:
        names=sorted(set().union(*(r.keys() for r in rows)))
        w=csv.DictWriter(f,fieldnames=names);w.writeheader()
        w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();source=read(a.root/'FINAL_RESOURCE_AND_SOURCE_v1.json')
    assert source['formal_service_episodes']==84 and source['development_service_episodes']==6
    groups=[];allruns={};decisions={}
    for stage,N in [('normal',24),('fault',36),('boundary',16),('post_sync',8)]:
        audit=read(a.root/(stage+'_AUDIT.json'));runs=audit['runs'];assert len(runs)==N
        assert read(a.root/(stage+'_ASSETS.json'))['status'].startswith('PASS_')
        for r in runs:
            for key in ['unauthorized_admissions','stale_publications','stale_as_fresh',
                'root_incompatible_actual_views','root_incompatible_views','certified_only_violations',
                'false_certified_mode_views','acknowledged_input_loss_samples']:
                if key in r:assert r[key]==0,(stage,r['episode'],key,r[key])
        allruns[stage]=runs;g=defaultdict(list)
        for r in runs:g[(r['adapter'],r['method'],r['readiness'],r['kernel'],r.get('synthetic_coherent_injections',0))].append(r)
        for k,rs in sorted(g.items()):
            ckey='commit_view_P99' if 'commit_view_P99' in rs[0] else 'commit_P99'
            groups.append(dict(stage=stage,adapter=k[0],method=k[1],readiness=k[2],kernel=k[3],synthetic_injections_per_run=k[4],repeats=len(rs),
                goodput_median=med([r['all_offered_audio_goodput_2_8'] for r in rs]),
                goodput_range=[min(r['all_offered_audio_goodput_2_8'] for r in rs),max(r['all_offered_audio_goodput_2_8'] for r in rs)],
                display_P99_median=med([r['display_P99'] for r in rs]),commit_P99_median=med([r[ckey] for r in rs]),
                GPU_J_per_offered_audio_second_median=med([r['GPU_J_per_offered_audio_second'] for r in rs]),
                WER_median=med([r['all_offered_WER_percent'] for r in rs]),
                WER_range=[min(r['all_offered_WER_percent'] for r in rs),max(r['all_offered_WER_percent'] for r in rs)],
                reference_words_per_run=sorted(set(r['WER_reference_words'] for r in rs)),
                whole_dual_P99_passes=sum(r['whole_run_dual_P99_pass'] for r in rs),
                scope='controlled interleaving; not normal capacity' if stage=='boundary' else 'same stage frozen workload'))
        decisions[stage]=dict(runs=N,all_recorded_safety_checks='PASS',whole_dual_P99_passes=sum(r['whole_run_dual_P99_pass'] for r in runs))
    clocks=read(a.root/'RECOVERY_CLOCKS_v2.json')['runs'];cg=defaultdict(list)
    for r in clocks:
        if r['stage'] in ['fault','post_sync']:cg[(r['stage'],r['adapter'],r['method'],r['readiness'],r['kernel'])].append(r)
    recovery=[]
    for k,rs in sorted(cg.items()):
        recovery.append(dict(stage=k[0],adapter=k[1],method=k[2],readiness=k[3],kernel=k[4],repeats=len(rs),
            RTO_view_median=med([r['RTO_view_all_previous_durable_facts'] for r in rs if r['RTO_view_all_previous_durable_facts'] is not None]),
            RTO_new_median=med([r['RTO_new_first_fresh_certified_consumption'] for r in rs if r['RTO_new_first_fresh_certified_consumption'] is not None]),
            precrash_debt_drain_median=med([r['RTO_precrash_accepted_debt'] for r in rs if r['RTO_precrash_accepted_debt'] is not None]),
            final_offered_consumption_median=med([r['RTO_final_offered_certified_consumption'] for r in rs]),
            old_facts_before_worker_ready=sum(r['all_previous_durable_facts_consumed_before_executors_ready'] for r in rs)))
    paired=[]
    for model in ['qwen','whisper']:
        for method in ['dgft_original','standard_fair']:
            rs=[r for r in clocks if r['stage']=='fault' and r['adapter']==model and r['method']==method]
            by={(r['repeat'],r['readiness'],r['kernel']):r for r in rs}
            assert len(by)==9
            for rep in range(3):
                old=by[rep,'legacy',False];early=by[rep,'early',False];kernel=by[rep,'early',True]
                paired.append(dict(adapter=model,method=method,repeat=rep,
                    startup_view_saved_seconds=old['RTO_view_all_previous_durable_facts']-early['RTO_view_all_previous_durable_facts'],
                    startup_view_change_percent=100*(early['RTO_view_all_previous_durable_facts']/old['RTO_view_all_previous_durable_facts']-1),
                    startup_new_output_change_seconds=early['RTO_new_first_fresh_certified_consumption']-old['RTO_new_first_fresh_certified_consumption'],
                    kernel_extra_view_seconds=kernel['RTO_view_all_previous_durable_facts']-early['RTO_view_all_previous_durable_facts'],
                    kernel_extra_new_seconds=kernel['RTO_new_first_fresh_certified_consumption']-early['RTO_new_first_fresh_certified_consumption']))
    normal_cost=[]
    for model in ['qwen','whisper']:
        for method in ['dgft_original','standard_fair']:
            by={(r['repeat'],r['readiness'],r['kernel']):r for r in allruns['normal'] if r['adapter']==model and r['method']==method}
            for rep in range(2):
                base=by[rep,'early',False];k=by[rep,'early',True]
                normal_cost.append(dict(adapter=model,method=method,repeat=rep,
                    goodput_change_percent=100*(k['all_offered_audio_goodput_2_8']/base['all_offered_audio_goodput_2_8']-1),
                    energy_change_percent=100*(k['GPU_J_per_offered_audio_second']/base['GPU_J_per_offered_audio_second']-1),
                    display_P99_change_seconds=k['display_P99']-base['display_P99'],
                    commit_P99_change_seconds=k['commit_view_P99']-base['commit_view_P99'],
                    WER_change_percentage_points=k['all_offered_WER_percent']-base['all_offered_WER_percent']))
    history=read(a.root/'HISTORY_COMPARISON_v1.json');assert history['unique_source_count']==8
    result=dict(status='COMPLETE_DESCRIPTIVE84_FORMAL_SERVICE_ANALYSIS',source=source['source'],
        stage_decisions=decisions,groups=groups,recovery_groups=recovery,paired_recovery=paired,paired_normal_kernel_cost=normal_cost,
        actual_unique_sources=8,source_tier='reused frozen N5 pool, not newly unseen validation; rows/repeats are not independent sources',
        history_equal_groups=sum(c['exact_canonical_histories_equal'] for c in history['comparisons']),history_groups=len(history['comparisons']),
        no_manuscript_edits=True,not_claimed='exclusive Standard superiority, population P99/CI, universal quality or full-stack proof')
    a.output.mkdir();(a.output/'ANALYSIS_v1.json').write_text(json.dumps(result,indent=2)+'\n')
    dumpcsv(a.output/'GROUPS_v1.csv',groups);dumpcsv(a.output/'RECOVERY_GROUPS_v1.csv',recovery)
    dumpcsv(a.output/'PAIRED_RECOVERY_v1.csv',paired);dumpcsv(a.output/'PAIRED_NORMAL_COST_v1.csv',normal_cost)
    print(json.dumps(dict(status=result['status'],stage_decisions=decisions,recovery_groups=recovery)))
if __name__=='__main__':main()

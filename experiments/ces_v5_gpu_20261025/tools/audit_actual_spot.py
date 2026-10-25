"""Small independent read-only audit of collected actual V5 events.

The only output is a new audit artifact; collected evidence and runtime are
never modified. This checks observed scheduling, not an alternative GPU run.
"""
from pathlib import Path
import argparse
import csv
import gzip
import hashlib
import json
import statistics

HERE=Path(__file__).resolve().parent
B=HERE/'collected'


def rows(path):
    with gzip.open(path,'rt',encoding='utf8') as stream:return [json.loads(x) for x in stream]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def csvrows(path):
    with path.open(newline='',encoding='utf8') as stream:return list(csv.DictReader(stream))
def quantile(values,p):
    values=sorted(values);rank=(len(values)-1)*p;i=int(rank);f=rank-i
    return values[i] if not f else values[i]+f*(values[i+1]-values[i])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=HERE/'ACTUAL_TRACE_SPOT_AUDIT.json')
    args=ap.parse_args()
    if args.output.exists():raise FileExistsError('Keep earlier audit artifacts')
    sources={};counts={};late_records=[]
    for method in ('progress','progress_joint'):
        byrun=[];source_frontier_sets=[]
        for rep in range(3):
            cell=f'validation-staggered-mixed-{method}-r{rep}';prefix='pilot_v1-'+cell
            path=B/'traces'/(prefix+'-events.jsonl.gz');sources[str(path.relative_to(HERE))]=sha(path)
            events=rows(path);t0=next(e['t0_perf'] for e in events if e['kind']=='run-start')
            enqueue={e['job_id']:e for e in events if e['kind']=='enqueue'}
            commits=[e for e in events if e['kind']=='commit']
            assert len(commits)==135
            unique=set();late=[]
            for c in commits:
                j=enqueue[c['job_id']]
                assert j['role']=='authority' and j['parent']==c['parent']
                assert j['audio_start_sample']==c['audio_start_sample'] and j['audio_end_sample']==c['audio_end_sample']
                key=j['source_id'],c['audio_end_sample'];assert key not in unique;unique.add(key)
                latency=(t0+c['installed'])-j['audio_ready_perf']
                assert abs(latency-c['latency_seconds'])<1e-7
                if latency>8.:
                    enq_lag=j['enqueue_perf']-j['audio_ready_perf']
                    rec={'cell':cell,'method':method,'repeat':rep,'job_id':j['job_id'],
                        'session':j['session_id'],'source_id':j['source_id'],'window':j['end_window'],
                        'parent':j['parent'],'audio_end_sample':j['audio_end_sample'],
                        'commit_latency_s':latency,'release_to_enqueue_s':enq_lag,
                        'commit_deadline_missed_before_enqueue':enq_lag>8.,
                        'release_to_parent_eligible_s':j['eligible_perf']-j['audio_ready_perf'],
                        'eligible_to_enqueue_s':j['enqueue_perf']-j['eligible_perf']}
                    late.append(rec);late_records.append(rec)
            source_frontier_sets.append(unique)
            byrun.append({'repeat':rep,'requested_frontiers':len(commits),'commit_over_8_count':len(late),
                'deadline_already_missed_at_enqueue':sum(r['commit_deadline_missed_before_enqueue'] for r in late),
                'deadline_crossed_after_enqueue':sum(not r['commit_deadline_missed_before_enqueue'] for r in late),
                'actual_commit_P99_s':quantile([c['installed']-c['audio_ready'] for c in commits],.99)})
        assert source_frontier_sets[0]==source_frontier_sets[1]==source_frontier_sets[2]
        counts[method]={'runs':byrun,'commit_over_8_count':sum(x['commit_over_8_count'] for x in byrun),
            'requested_frontier_observations':405,'unique_source_frontier_pairs':135,
            'deadline_already_missed_at_enqueue':sum(x['deadline_already_missed_at_enqueue'] for x in byrun),
            'late_targets_parent_eligibility_itself_after_deadline':sum(r['release_to_parent_eligible_s']>=8 for r in late_records if r['method']==method),
            'late_targets_eligible_queue_wait_over_8_s':sum(r['eligible_to_enqueue_s']>8 for r in late_records if r['method']==method),
            'group_median_commit_P99_s':statistics.median(r['actual_commit_P99_s'] for r in byrun),
            'denominator_note':'The same 135 source/frontier pairs repeated in three runs; not 405 independent samples.'}
    assert counts['progress']['commit_over_8_count']==41
    assert counts['progress_joint']['commit_over_8_count']==56

    cell='validation-staggered-mixed-progress_joint-r0';prefix='pilot_v1-'+cell;jobid='authority-4-249'
    names={'events':B/'traces'/(prefix+'-events.jsonl.gz'),
        'witness':B/'canonical_witnesses'/(prefix+'.jsonl.gz'),
        'batches':B/'traces'/(prefix+'-worker_batch_accounting.jsonl.gz')}
    for p in names.values():sources[str(p.relative_to(HERE))]=sha(p)
    events=rows(names['events']);witness=next(w for w in rows(names['witness']) if w['job']['job_id']==jobid)
    j=witness['job'];receipt=witness['selected']['_row_receipt'];batches=rows(names['batches'])
    t0=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    e=next(x for x in events if x['kind']=='enqueue' and x['job_id']==jobid)
    c=next(x for x in events if x['kind']=='commit' and x['job_id']==jobid)
    done=next(x for x in events if x['kind']=='executor-complete' and x['job_id']==jobid)
    assert e['declared_prompt_tokens']==j['prompt_tokens']
    assert c['parent']==j['parent']==5 and c['version']==6 and j['end_window']==6
    assert j['audio_start_sample']==160000 and j['audio_end_sample']==192000
    previous=next(x for x in events if x['kind']=='commit' and x['session_id']==4 and x['version']==5)
    assert previous['audio_end_sample']==j['audio_start_sample']
    assert previous['next_prompt_tokens']==j['prompt_tokens']
    assert t0+previous['installed']<j['audio_ready_perf']
    timeline=[]
    for decision in events:
        if decision['kind']!='ces-decision':continue
        candidates=[f for f in decision['features'] if f['sid']==4 and f['window']==6]
        if not candidates:continue
        assert len(candidates)==1
        f=candidates[0];now=decision['observed_perf']
        installed=[x for x in events if x['kind']=='commit' and x['session_id']==4 and t0+x['installed']<=now]
        parent=max(installed,key=lambda x:x['version'])
        assert parent['version']==5 and parent['audio_end_sample']==160000
        assert parent['next_prompt_tokens']==j['prompt_tokens']
        assert f['ready']==j['audio_ready_perf'] and f['deadline']==j['audio_ready_perf']+8.
        assert f['audio_seconds']==12. and f['interval_seconds']==2. and f['audio_weight']==2.
        assert f['prompt_tokens']==len(j['prompt_tokens'])
        assert now>=j['audio_ready_perf']
        prior_enqueues=[x for x in events if x['kind']=='enqueue' and x['role']=='authority'
            and x['session_id']==4 and x['parent']==5 and x['enqueue_perf']<now]
        assert not prior_enqueues,'Target was already dispatched when claimed eligible'
        live_leases=[x for x in batches if x['worker']=='authority-1'
            and x['worker_started_perf']<=now<x['batch_drained_perf']]
        assert not live_leases,'Physical authority lease occupied at the decision'
        plan_positions=[i for i,part in enumerate(decision['plan']) if 4 in part['sids']]
        assert len(plan_positions)==1
        selected=4 in decision['sids']
        timeline.append({'relative_decision_time':now-t0,'release_to_decision_s':now-j['audio_ready_perf'],
            'same_parent_version':parent['version'],'same_parent_frontier':parent['audio_end_sample'],
            'same_target_frontier':j['audio_end_sample'],'same_prompt_tokens':True,
            'authority_worker_idle':True,'candidate_ready':f['candidate_ready'],
            'display_met':f['display_met'],'display_expired':f['display_expired'],
            'chosen_first_operation':decision['operation'],'chosen_first_sids':decision['sids'],
            'target_plan_position':plan_positions[0],'selected':selected,
            'recorded_plan':decision['plan']})
    assert len(timeline)==14 and sum(not x['selected'] for x in timeline)==13
    assert not any(x['selected'] for x in timeline[:-1]) and timeline[-1]['selected']
    assert witness['verification']['candidate_accepted'] and not witness['verification']['fallback_used']
    assert witness['selected']['token_ids']==j['candidate_token_ids']
    segments={
        'release_to_parent_eligible_s':e['eligible_perf']-j['audio_ready_perf'],
        'eligible_to_enqueue_s':j['enqueue_perf']-e['eligible_perf'],
        'enqueue_to_worker_start_s':t0+done['started']-j['enqueue_perf'],
        'worker_start_to_complete_row_s':receipt['terminal_perf']-(t0+done['started']),
        'row_to_trusted_render_s':receipt['rendered_perf']-receipt['terminal_perf'],
        'render_to_emit_s':receipt['emitted_perf']-receipt['rendered_perf'],
        'emit_to_owner_receive_s':t0+done['received']-receipt['emitted_perf'],
        'owner_receive_to_install_s':c['installed']-done['received']}
    assert all(v>=0 for v in segments.values())
    assert abs(sum(segments.values())-c['latency_seconds'])<1e-7
    paths_path=HERE/'local_review/AUTHORITY_CRITICAL_PATHS.csv'
    defers_path=HERE/'local_review/TARGET_DEFERRALS.csv'
    groups_path=HERE/'local_review/GROUPS.csv'
    for p in (paths_path,defers_path,groups_path):sources[str(p.relative_to(HERE))]=sha(p)
    for method,count in counts.items():
        group=next(r for r in csvrows(groups_path) if r['arrival']=='staggered' and r['method']==method)
        assert int(group['runs'])==3
        assert abs(float(group['commit_P99'])-count['group_median_commit_P99_s'])<1e-7
    published=next(x for x in csvrows(paths_path) if x['cell']==cell and x['job_id']==jobid)
    for key,value in segments.items():assert abs(float(published[key])-value)<1e-7,(key,published[key],value)
    defer=next(x for x in csvrows(defers_path) if x['cell']==cell and x['job_id']==jobid)
    assert int(defer['first_batch_deferrals'])==13 and int(defer['eligible_decision_observations'])==14
    report={'status':'PASS_RAW_EVENT_AND_CANONICAL_WITNESS_SPOT_AUDIT',
        'scope':'Actual collected trace verification; no counterfactual policy speedup is inferred',
        'case':{'cell':cell,'job_id':jobid,'source_id':j['source_id'],
            'stable_parent':5,'audio_interval_samples':[160000,192000],
            'parent_installed_relative':previous['installed'],'audio_release_relative':j['audio_ready_perf']-t0,
            'commit_latency_s':c['latency_seconds'],'segments':segments,
            'eligible_decision_observations':len(timeline),'first_batch_deferrals':13,
            'eventual_verify_accepted':True,'fallback_used':False,'timeline':timeline},
        'late_commit_counts':counts,'late_records':late_records,'sources_sha256':sources,
        'csv_disagreements':[],'script_sha256':sha(Path(__file__)),'new_GPU_calls':0}
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({'status':report['status'],'case_segments':segments,
        'case_decisions':len(timeline),'case_deferrals':13,'late_commit_counts':counts},indent=2))


if __name__=='__main__':main()

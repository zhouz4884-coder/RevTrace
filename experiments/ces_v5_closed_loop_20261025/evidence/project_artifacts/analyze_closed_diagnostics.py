"""Independent observed-history diagnostics for the frozen closed-loop stage.

No neural model, GPU, SSH, policy mutation or counterfactual execution occurs.
Repeated forecasts and repeated frontiers are not independent observations.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,itertools,json,math,statistics
from collections import defaultdict
from pathlib import Path

CLOSED={'service_cost','reserved_progress','inherit','causal'}

def read(path):return json.loads(path.read_text(encoding='utf8'))
def lines(path):
    op=gzip.open if path.suffix=='.gz' else open
    with op(path,'rt',encoding='utf8') as f:return [json.loads(s) for s in f]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def quantile(xs,q):
    xs=sorted(math.inf if x is None else float(x) for x in xs)
    if not xs:return math.inf
    pos=(len(xs)-1)*q;i=int(pos);f=pos-i
    if f==0 or i==len(xs)-1:return xs[i]
    if math.isinf(xs[i+1]):return math.inf
    return xs[i]+f*(xs[i+1]-xs[i])
def clean(x):
    if isinstance(x,float) and not math.isfinite(x):return None
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [clean(v) for v in x]
    return x
def csvsave(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf8') as f:
        if fields:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def qkey(sid,window):return int(sid),int(window)
def identity_key(sid,epoch,parent,start,end):return int(sid),int(epoch),int(parent),int(start),int(end)
def name_for(item):return f"{item['pool']}-{item['arrival']}-{item['traffic']}-{item['label']}-r{item['repeat']}"


def safety_audit_complete(report,expected):
    return (report.get('status')=='PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT'
        and not report.get('failures',[None]) and report.get('cells')==expected
        and report.get('expected_cells')==expected)


def stable_visible(views,frontier):
    """Last uninterrupted legal-visibility interval through certification."""
    first=cert=stable=None;withdrawn=False;ever=False
    for v in sorted(views,key=lambda r:r['observed']):
        covers=v['valid_visible_frontier']>=frontier
        if covers:
            if first is None:first=v['observed']
            if stable is None:stable=v['observed']
            ever=True
        else:
            withdrawn|=ever;stable=None
        if v['certified_frontier']>=frontier:
            cert=v['observed'];break
    return first,cert,stable if cert is not None else None,withdrawn


def merged_overlap(left,right,intervals):
    clipped=sorted((max(left,a),min(right,b)) for a,b in intervals if min(right,b)>max(left,a))
    total=0.;end=left
    for a,b in clipped:
        a=max(a,end)
        if b>a:total+=b-a
        end=max(end,b)
    return total


def energy(samples,start,wall):
    total=0.;coverage=[]
    for gpu in (0,1):
        xs=sorted((r for r in samples if r['gpu']==gpu),key=lambda r:r['t'])
        if len(xs)<2:return None,0.
        finish=start+wall
        coverage.append(max(0.,min(finish,xs[-1]['t'])-max(start,xs[0]['t']))/wall)
        for a,b in zip(xs,xs[1:]):
            lo,hi=max(start,a['t']),min(finish,b['t'])
            if hi<=lo:continue
            assert b['t']>a['t']
            p=lambda t:a['power_w']+(b['power_w']-a['power_w'])*(t-a['t'])/(b['t']-a['t'])
            total+=(p(lo)+p(hi))*(hi-lo)/2.
    return total,min(coverage)


def actual_decision_dispatches(events,byid):
    """Link logged decisions to real issued jobs without a simulated queue."""
    pending=None;mapping={};index=-1
    for event in events:
        if event['kind']=='ces-decision':
            index+=1
            if event['operation'] is not None:
                assert pending is None
                pending=(index,event,[])
        elif event['kind']=='enqueue' and event['role']=='authority':
            assert pending is not None and event['session_id'] in pending[1]['sids']
            pending[2].append(event['job_id'])
        elif event['kind']=='batch-dispatched' and event['role']=='authority':
            assert pending is not None
            idx,decision,jobs=pending
            assert set(jobs)==set(event['job_ids'])
            assert {byid[j]['job']['session_id'] for j in jobs}==set(decision['sids'])
            mapping[idx]={'job_ids':jobs,'first_enqueue_perf':min(byid[j]['job']['enqueue_perf'] for j in jobs),
                'last_enqueue_perf':max(byid[j]['job']['enqueue_perf'] for j in jobs),
                'observed_perf':decision['observed_perf']}
            pending=None
    assert pending is None
    return mapping


def paired(a,b,key):
    repeats=sorted(a)
    if not repeats or set(a)!=set(b):return {'status':'INCOMPLETE_PAIRS_NO_CLAIM'}
    deltas=[]
    for r in repeats:
        x,y=a[r].get(key),b[r].get(key)
        if x is None or y is None:return {'status':'MISSING_METRIC_NO_CLAIM'}
        if key in ('WER','CER'):v=y-x
        elif x:v=y/x-1.
        else:v=0. if y==0 else math.inf
        if not math.isfinite(v):return {'status':'NONFINITE_RATIO_NO_CLAIM'}
        deltas.append(v)
    result={'status':'PAIRED_OBSERVED_RUNS','runs':len(repeats),
        'baseline_group_median':statistics.median(a[r][key] for r in repeats),
        'treatment_group_median':statistics.median(b[r][key] for r in repeats),
        'paired_effects':deltas,'paired_median':statistics.median(deltas)}
    if len(repeats)>=3:
        draws=[statistics.median(deltas[i] for i in inds) for inds in itertools.product(range(len(repeats)),repeat=len(repeats))]
        result.update(paired_run_bootstrap_95=[quantile(draws,.025),quantile(draws,.975)],
            resamples=len(draws),interval_scope='Exact paired-run bootstrap distribution; descriptive for three runs, no per-frontier IID assumption')
    return result


def analyze_cell(C,spec,quality=None):
    cfg=read(C/'config.json');result=read(C/'result.json')
    assert result['fine_window_accounting_complete'] is True
    assert result['decision'] in ('PASS_PROTOCOL_COMPLETENESS','TOKEN_LIMIT_BOUNDARY')
    assert cfg['rho']==1 and cfg['fine_seconds']==2
    events=lines(C/'events.jsonl');records=lines(C/'worker_records.jsonl')
    views=lines(C/'consumer.jsonl');accounts=lines(C/'worker_batch_accounting.jsonl')
    sessions=read(C/'sessions.json');initial=read(C/'initial_states.json')
    assert all(x['state']['audio_frontier_window']==0 for x in initial),'Fresh serving stage required'
    t0=next(e['t0_perf'] for e in events if e['kind']=='run-start')
    label=spec['label'];method=cfg['ces_study']['method'];cell=C.name
    byid={r['job']['job_id']:r for r in records};assert len(byid)==len(records)
    real_dispatches=actual_decision_dispatches(events,byid)
    scheduler_intervals=[(d['observed_perf'],d['first_enqueue_perf']) for d in real_dispatches.values()]
    enqueue={e['job_id']:e for e in events if e['kind']=='enqueue'}
    done={e['job_id']:e for e in events if e['kind']=='executor-complete'}
    commits={e['job_id']:e for e in events if e['kind']=='commit'}
    assert len(commits)==result['certified_commits']
    auth={identity_key(j['session_id'],j['contract_epoch'],j['parent'],j['audio_start_sample'],j['audio_end_sample']):jid
          for jid,e in enqueue.items() if (j:=byid[jid]['job'])['role']=='authority'}
    assert len(auth)==len(commits)
    current={x['session_id']:{'version':x['state']['checkpoint_id'],'frontier':x['state']['audio_frontier_window'],
                            'epoch':x['state']['contract_epoch']} for x in initial}
    commit_by_window={qkey(e['session_id'],byid[jid]['job']['end_window']):e for jid,e in commits.items()}
    view_by_session=defaultdict(list)
    for v in views:view_by_session[v['session_id']].append(v)
    atoms={};front_rows=[]
    for session in sessions:
        sid=session['session_id'];total=round(session['duration']*16000);previous=0
        for window,frontier in enumerate(list(range(32000,total,32000))+[total],1):
            release=session['offset']+frontier/16000
            d,certified,stable,withdrawn=stable_visible(view_by_session[sid],frontier)
            cc=[e['installed'] for e in commits.values() if e['session_id']==sid and e['audio_end_sample']>=frontier]
            committed=min(cc) if cc else None
            item={'cell':cell,'label':label,'source_id':session['source_id'],'session':sid,'window':window,
                'frontier_sample':frontier,'audio_seconds':(frontier-previous)/16000,'release':release,
                'display':None if d is None else d-release,'commit':None if committed is None else committed-release,
                'certified_consumer':None if certified is None else certified-release,
                'stable_display':None if stable is None else stable-release,'withdrawn_before_certification':withdrawn}
            item['earned_audio']=item['audio_seconds'] if item['display'] is not None and item['commit'] is not None and item['display']<=2 and item['commit']<=8 else 0.
            item['stable_earned_audio']=item['audio_seconds'] if item['stable_display'] is not None and item['certified_consumer'] is not None and item['stable_display']<=2 and item['certified_consumer']<=8 else 0.
            atoms[sid,window]=item;front_rows.append(item);previous=frontier
    assert len(front_rows)==sum(math.ceil(s['duration']/2) for s in sessions)
    assert len(commits)==len(front_rows),'Do not silently drop uncompleted requested frontiers'
    wall=max(result['wall_seconds_including_arrival_and_drain'],max(v['observed'] for v in views))
    audio=sum(s['duration'] for s in sessions)
    physical=[];role_lease=defaultdict(float);role_calls=CounterLike();lease_intervals=[]
    for a in accounts:
        batch_records=[byid[j] for j in a['job_ids']];roles={r['job']['role'] for r in batch_records};assert len(roles)==1
        role=roles.pop();lease=a['batch_drained_perf']-a['worker_started_perf'];assert lease>=0
        role_lease[role]+=lease;role_calls[role]+=len(a['phases'])
        if role=='authority':lease_intervals.append((a['worker_started_perf'],a['batch_drained_perf']))
        physical.append({'cell':cell,'label':label,'role':role,'batch_id':a['batch_id'],'rows':len(batch_records),
            'physical_lease_s':lease,'actual_model_calls':len(a['phases']),
            'actual_model_phase_s':sum(p['completed_perf']-p['started_perf'] for p in a['phases']),
            'actual_fallback_calls':sum(p['phase']=='fresh-FP32-fallback' for p in a['phases'])})
    paths=[]
    for jid,commit in commits.items():
        j=byid[jid]['job'];r=byid[jid]['result'];enq=enqueue[jid];receipt=r['_row_receipt'];ev=done[jid]
        eligible=enq['eligible_perf'];install=t0+commit['installed'];release=j['audio_ready_perf']
        path={'cell':cell,'label':label,'job_id':jid,'session':j['session_id'],'window':j['end_window'],'parent':j['parent'],
            'operation':j['ces_operation'],'release_to_parent_eligible_s':eligible-release,
            'eligible_to_enqueue_s':j['enqueue_perf']-eligible,
            'enqueue_to_worker_start_s':r['started_perf']-j['enqueue_perf'],
            'worker_start_to_terminal_s':receipt['terminal_perf']-r['started_perf'],
            'terminal_to_render_s':receipt['rendered_perf']-receipt['terminal_perf'],
            'render_to_emission_s':receipt['emitted_perf']-receipt['rendered_perf'],
            'emission_to_owner_receive_s':r['received_perf']-receipt['emitted_perf'],
            'owner_receive_to_install_s':install-r['received_perf']}
        pieces=[path[k] for k in path if k.endswith('_s')]
        assert min(pieces)>=-1e-7 and abs(sum(pieces)-commit['latency_seconds'])<1e-7
        busy=merged_overlap(eligible,j['enqueue_perf'],lease_intervals)
        path.update(commit_latency_s=commit['latency_seconds'],commit_over_8=commit['latency_seconds']>8,
            already_over_8_at_enqueue=j['enqueue_perf']>release+8,
            eligible_queue_other_authority_lease_overlap_s=busy,
            eligible_queue_outside_authority_lease_s=path['eligible_to_enqueue_s']-busy,
            eligible_queue_overlap_observed_authority_scheduling_s=merged_overlap(eligible,j['enqueue_perf'],scheduler_intervals))
        paths.append(path)
    observations={};decision_rows=[];deferrals=defaultdict(list);retirements=[];forecast_rows=[];private_rows=[]
    for event in events:
        if event['kind']=='commit':
            current[event['session_id']].update(version=event['version'],frontier=event['audio_end_sample'])
        elif event['kind']=='closed-loop-observation':observations[event['observed_perf']]=event
        elif event['kind']=='closed-loop-service-retired':
            for rec in event['retired']:
                promise=rec.get('promised_finish');actual=event['installed_perf']
                assert rec['actual_install_time']==actual
                assert rec['actual_promise_late']==bool(promise is not None and actual>promise)
                retirements.append({'cell':cell,'label':label,**{f'identity_{k}':v for k,v in rec['identity'].items()},
                    'first_seen':rec['first_seen'],'actual_install_perf':actual,'deferrals_at_retirement':rec['deferrals'],
                    'promised_finish':promise,'actual_promise_late':rec['actual_promise_late'],
                    'promise_lateness_s':None if promise is None else actual-promise,
                    'recorded_promise_breach_events':rec['promise_breaches']})
        elif event['kind']=='ces-decision':
            idx=len(decision_rows);now=event['observed_perf'];obs=observations.get(now)
            contexts={} if obs is None else obs['contexts'];targets=[];successors=[]
            for f in event['features']:
                sid=f['sid'];window=f['window'];state=current[sid]
                atom=atoms[sid,window]
                key=identity_key(sid,state['epoch'],state['version'],state['frontier'],atom['frontier_sample'])
                assert key in auth,'Decision target must resolve to its actual eventual authority job'
                jid=auth[key];selected=sid in event['sids'];plan_position=next((i for i,b in enumerate(event.get('plan',[])) if sid in b['sids']),None)
                if sid in event.get('common_cut_sids',[]) and event.get('plan'):assert plan_position is not None
                deferrals[key].append({'decision':idx,'observed_perf':now,'selected':selected,'plan_position':plan_position,
                    'display_met':f.get('display_met'),'display_expired':f.get('display_expired')})
                targets.append((sid,window))
                if str(sid) in contexts:
                    c=contexts[str(sid)];identity=c['identity']
                    assert identity_key(identity['sid'],identity['epoch'],identity['parent_version'],identity['frontier_start'],identity['frontier_end'])==key
                    for u in c['released_successors']:
                        assert u['release']<=now
                        successors.append((sid,u['window']))
                    for kind,window,priv in [('current',window,c['target_context'])]+[
                            ('successor',u['window'],u) for u in c['released_successors']]:
                        distribution=priv.get('private_delay_distribution',[])
                        if not distribution:continue
                        source=c['private_path'];pending=source.get('job_id')
                        a=atoms[sid,window];due=t0+a['release']+2.
                        delivery=0. if priv.get('private_delay_includes_delivery') else cfg['ces_study']['calibration']['v5_risk_model'].get('owner_delivery_seconds',0.)
                        p=sum(w for w,d in distribution if now+d+delivery<=due)/sum(w for w,d in distribution)
                        ds=[e for e in events if e['kind']=='display' and e.get('job_id')==pending]
                        actual_views=[v for d in ds for v in view_by_session[sid]
                            if v['source_kind']=='display' and v['server_time']==d['displayed']]
                        legal=[v['observed_perf'] for v in actual_views if v['valid_visible_frontier']>=a['frontier_sample']]
                        private_rows.append({'cell':cell,'label':label,'decision':idx,'kind':kind,'session':sid,'window':window,
                            'pending_job_id':pending,'observed_perf':now,'pending_delivery_CDF_probability_by_D':p,
                            'path_currently_legal':priv['private_path_currently_legal'],
                            'conditional_verify_chain':priv.get('verify_private_compatible'),
                            'actual_this_job_legal_cover_observation':min(legal) if legal else None,
                            'actual_this_job_legal_cover_by_D':bool(legal and min(legal)<=due),
                            'scope':'Repeated pending-delivery forecast; CDF is not a standalone legality probability or a counterfactual action outcome'})
            actual_current=sum(atoms[k]['earned_audio'] for k in set(targets))
            actual_successors=sum(atoms[k]['earned_audio'] for k in set(successors))
            if targets or successors:
                assert not set(targets)&set(successors),'Do not count an audio atom twice'
                forecast_rows.append({'cell':cell,'label':label,'decision':idx,'observed_perf':now,
                    'current_targets':len(set(targets)),'successor_targets':len(set(successors)),
                    'predicted_current_credit':event.get('expected_current_credit_audio'),
                    'predicted_successor_credit':event.get('expected_successor_credit_audio'),
                    'predicted_private_additional_credit':event.get('expected_private_additional_credit_audio'),
                    'actual_current_credit_in_eventual_history':actual_current,
                    'actual_successor_credit_in_eventual_history':actual_successors,
                    'predicted_paid_complete_cut_lease_s':event.get('expected_lease_seconds'),
                    'predicted_paid_complete_cut_wall_s':event.get('expected_cut_wall_seconds'),
                    'scope':'Actual continuation was replanned; these are observational forecast residuals, not execution of the forecast suffix'})
            inherited={int(sid) for sid,v in event.get('effective_deadlines',{}).items() if v['inherited_from_windows']}
            issued=real_dispatches.get(idx)
            dispatch_delay=None if issued is None else issued['first_enqueue_perf']-now
            decision_rows.append({'cell':cell,'label':label,'decision':idx,'observed_perf':now,
                'operation':event['operation'],'selected_sids':json.dumps(event['sids']),
                'current_targets':len(event['features']),'released_successor_observations':len(successors),
                'inherited_deadline_targets':len(inherited),'selected_targets_with_inherited_deadline':len(inherited&set(event['sids'])),
                'successor_reward_used':event.get('successor_reward_used',False),
                'positive_successor_credit_forecast':event.get('expected_successor_credit_audio',0.)>0,
                'positive_private_additional_credit_forecast':event.get('expected_private_additional_credit_audio',0.)>0,
                'service_guard_active':event.get('service_guard_active',False),
                'forced_targets':len(event.get('forced_sids',[])),
                'forced_not_selected':len(set(event.get('forced_sids',[]))-set(event['sids'])),
                'predicted_promise_violation_mass':event.get('promise_violation_mass'),
                'authority_planner_wall_s':event['planner_wall_seconds'],'base_feature_wall_s':event['feature_wall_seconds'],
                'actual_snapshot_to_first_enqueue_s':dispatch_delay,
                'snapshot_to_first_enqueue_minus_feature_and_planner_s':None if dispatch_delay is None else dispatch_delay-event['feature_wall_seconds']-event['planner_wall_seconds'],
                'plans_evaluated':event.get('plans_evaluated',event.get('partitions_evaluated')),
                'scope':'Activation and observed selection, not proof the feature caused a counterfactual gain'})
    defer_rows=[]
    for key,obs in deferrals.items():
        jid=auth[key];j=byid[jid]['job'];c=commits[jid]
        assert all(o['observed_perf']<=j['enqueue_perf']+1e-7 for o in obs)
        defer_rows.append({'cell':cell,'label':label,'job_id':jid,'session':key[0],'epoch':key[1],'parent':key[2],
            'frontier_start':key[3],'frontier_end':key[4],'window':j['end_window'],
            'eligible_decision_observations':len(obs),'actual_first_batch_deferrals':sum(not o['selected'] for o in obs),
            'last_observation_selected':obs[-1]['selected'],'first_observation_display_met':obs[0]['display_met'],
            'first_observation_display_expired':obs[0]['display_expired'],
            'first_observed_to_enqueue_s':j['enqueue_perf']-obs[0]['observed_perf'],
            'commit_latency_s':c['latency_seconds'],'same_parent_frontier_identity':True,
            'scope':'Only decisions with explicit target snapshots; absent baseline features do not imply zero deferrals'})
    power_path=C/'power_samples.json';joules=coverage=None
    if power_path.exists():joules,coverage=energy(read(power_path)['samples'],t0,wall)
    metrics={'cell':cell,'label':label,'runtime_method':method,**{k:spec[k] for k in ('arrival','traffic','repeat','pool')},
        'status':'COMPLETE_OBSERVED_HISTORY','result_boundary':result['decision'],'requested_frontiers':len(front_rows),
        'requested_audio_seconds':audio,'wall_seconds':wall,
        'Audio_Goodput_2_8':sum(a['earned_audio'] for a in front_rows)/wall,
        'Audio_Goodput_stable_2_8':sum(a['stable_earned_audio'] for a in front_rows)/wall,
        'display_P50':quantile([a['display'] for a in front_rows],.5),'display_P95':quantile([a['display'] for a in front_rows],.95),
        'display_P99':quantile([a['display'] for a in front_rows],.99),
        'commit_P50':quantile([a['commit'] for a in front_rows],.5),'commit_P95':quantile([a['commit'] for a in front_rows],.95),
        'commit_P99':quantile([a['commit'] for a in front_rows],.99),
        'commit_over_8':sum(a['commit'] is None or a['commit']>8 for a in front_rows),
        'missed_before_enqueue':sum(p['commit_over_8'] and p['already_over_8_at_enqueue'] for p in paths),
        'authority_eligible_queue_P99':quantile([p['eligible_to_enqueue_s'] for p in paths],.99),
        'release_to_parent_P99':quantile([p['release_to_parent_eligible_s'] for p in paths],.99),
        'authority_planner_wall_s':sum(d['authority_planner_wall_s'] for d in decision_rows),
        'authority_planner_wall_fraction_of_run':sum(d['authority_planner_wall_s'] for d in decision_rows)/wall,
        'authority_planner_per_decision_P50_s':quantile([d['authority_planner_wall_s'] for d in decision_rows],.5),
        'authority_planner_per_decision_P99_s':quantile([d['authority_planner_wall_s'] for d in decision_rows],.99),
        'base_feature_wall_s':sum(d['base_feature_wall_s'] for d in decision_rows),
        'authority_snapshot_to_first_enqueue_total_s':sum(d['actual_snapshot_to_first_enqueue_s'] or 0. for d in decision_rows),
        'ack_wall_s':result.get('CES_consumer_ack',{}).get('owner_ack_wall_seconds'),
        'GPU0_selector_CPU_separate_measurement':None,
        'GPU0_selector_CPU_scope':'Included in actual full wall; no separate timer in frozen runtime',
        'proposal_physical_lease_s':role_lease['proposal'],'authority_physical_lease_s':role_lease['authority'],
        'authority_lease_coverage_in_actual_run_s':merged_overlap(t0,t0+wall,lease_intervals),
        'authority_snapshot_to_enqueue_overlap_lease_s':sum(merged_overlap(a,b,lease_intervals) for a,b in scheduler_intervals),
        'proposal_model_calls':role_calls['proposal'],'authority_model_calls':role_calls['authority'],
        'actual_fallback_calls':sum(r['actual_fallback_calls'] for r in physical),
        'GPU_J_audio_s':None if joules is None or coverage<.995 else joules/audio,
        'recorded_energy_J_audio_s_unfilled':None if joules is None else joules/audio,
        'power_coverage':coverage,'strict_energy_comparison_eligible':coverage is not None and coverage>=.995,
        'physical_fsyncs':sum(e['kind']=='wal-physical-timing' and e['phase']=='fsync' for e in events),
        'successor_active_decisions':sum(d['successor_reward_used'] and d['released_successor_observations']>0 for d in decision_rows),
        'positive_private_forecast_decisions':sum(d['positive_private_additional_credit_forecast'] for d in decision_rows),
        'forced_service_decisions':sum(d['forced_targets']>0 for d in decision_rows),
        'guard_active_decisions':sum(d['service_guard_active'] for d in decision_rows),
        'maximum_observed_target_deferrals':max((r['actual_first_batch_deferrals'] for r in defer_rows),default=None),
        'targets_with_at_least_3_deferrals':sum(r['actual_first_batch_deferrals']>=3 for r in defer_rows) if defer_rows else None,
        'retired_promised_records':sum(r['promised_finish'] is not None for r in retirements),
        'retired_actual_promise_late':sum(r['actual_promise_late'] for r in retirements),
        'retired_reported_promise_breaches':sum(r['recorded_promise_breach_events'] for r in retirements),
        'consumer_audio_rollback_samples':sum(v['audio_rollback_samples'] for v in views),
        'consumer_erased_characters':sum(v['erased_characters'] for v in views),
        'withdrawn_frontiers':sum(a['withdrawn_before_certification'] for a in front_rows),
        'capped_proposal_rows':sum(r['job']['role']=='proposal' and r['result']['hit_token_limit'] for r in records),
        'capped_authority_rows':sum(r['job']['role']=='authority' and r['result']['hit_token_limit'] for r in records),
        'WER':None if quality is None else quality.get('WER'), 'CER':None if quality is None else quality.get('CER'),
        'quality_scope':'Retained independently audited final-reference counts, not recomputed tokens by this timing script'}
    assert abs(metrics['authority_planner_wall_s']-result['CES_host_cost']['planner_wall_seconds'])<1e-7
    metrics['dual_P99_pass']=metrics['display_P99']<=2 and metrics['commit_P99']<=8
    proposer=[dict(cell=cell,label=label,**{k:v for k,v in e.items() if k not in ('kind','candidates')})
              for e in events if e['kind']=='closed-loop-proposer-choice']
    for e in proposer:
        for key,value in list(e.items()):
            if isinstance(value,(dict,list)):e[key]=json.dumps(value,separators=(',',':'))
    return {'CELL_METRICS': [metrics],'FRONTIERS':front_rows,'CRITICAL_PATHS':paths,
        'TARGET_DEFERRALS':defer_rows,'DECISION_ACTIVATION':decision_rows,
        'SERVICE_PROMISES':retirements,'CUT_FORECAST_VS_ACTUAL':forecast_rows,
        'PRIVATE_FORECAST_VS_ACTUAL':private_rows,'PAID_PHYSICAL_BATCHES':physical,'PROPOSER_CHOICES':proposer}


class CounterLike(defaultdict):
    def __init__(self):super().__init__(int)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--stage',required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--plan',type=Path,default=Path(__file__).with_name('PLAN.smoke.json'))
    ap.add_argument('--audit-dir',type=Path,help='Explicit matching completed safety-audit directory, e.g. smoke_audit_v2')
    args=ap.parse_args();plan=read(args.plan);specs=plan['stages'][args.stage]['cells']
    if args.output.exists():raise FileExistsError('Choose a new diagnostics directory; preserve previous results')
    args.output.mkdir(parents=True)
    expected={name_for(s):s for s in specs};assert len(expected)==len(specs)
    audit_dir=args.audit_dir or args.root/(args.stage+'_audit');quality={};audited=False
    if (audit_dir/'SUMMARY.json').exists():
        a=read(audit_dir/'SUMMARY.json');audited=safety_audit_complete(a,len(expected))
    if (audit_dir/'SERVICE_CELLS.csv').exists():
        with (audit_dir/'SERVICE_CELLS.csv').open(newline='',encoding='utf8') as f:
            for r in csv.DictReader(f):quality[r['cell']]={k:float(r[k]) for k in ('WER','CER')}
    tables=defaultdict(list);requested=[];failures=[];inputs=[]
    for cell,spec in expected.items():
        C=args.root/args.stage/cell
        files=[C/n for n in ('config.json','result.json','sessions.json','initial_states.json','events.jsonl',
            'worker_records.jsonl','consumer.jsonl','worker_batch_accounting.jsonl')]
        available=[p for p in files+[C/'power_samples.json'] if p.exists()]
        inputs.extend({'cell':cell,'path':str(p.relative_to(args.root)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in available)
        if any(not p.exists() for p in files):
            error={'cell':cell,'label':spec['label'],'status':'MISSING_OR_FAILED_REQUEST_RETAINED',
                'missing_files':[p.name for p in files if not p.exists()]}
            if (C/'sessions.json').exists():
                ss=read(C/'sessions.json');error['requested_audio_seconds']=sum(s['duration'] for s in ss)
                error['requested_frontiers']=sum(math.ceil(s['duration']/2) for s in ss)
            if (C/'worker_batch_accounting.jsonl').exists():
                paid=lines(C/'worker_batch_accounting.jsonl')
                error['recorded_completed_physical_batches']=len(paid)
                error['recorded_physical_lease_s_lower_bound']=sum(a['batch_drained_perf']-a['worker_started_perf'] for a in paid)
                error['cost_scope']='Completed recorded leases only; unfinished/unflushed work remains unquantified, never treated as zero'
            failures.append(error);requested.append(error);continue
        try:
            result=analyze_cell(C,spec,quality.get(cell))
            for name,rs in result.items():tables[name].extend(rs)
            requested.append({'cell':cell,'label':spec['label'],'status':'COMPLETE_OBSERVED_HISTORY'})
            print('DIAGNOSED',cell,flush=True)
        except Exception as e:
            error={'cell':cell,'label':spec['label'],'status':'DIAGNOSTIC_CHECK_FAILED_RAW_RETAINED','error':repr(e)}
            failures.append(error);requested.append(error)
    actual={p.name for p in (args.root/args.stage).iterdir() if p.is_dir()} if (args.root/args.stage).exists() else set()
    extras=sorted(actual-set(expected))
    if extras:failures.append({'status':'UNPLANNED_CELL_DIRECTORIES_RETAINED','cells':extras})
    for name,rs in tables.items():csvsave(args.output/(name+'.csv'),rs)
    csvsave(args.output/'REQUESTED_CELLS.csv',requested)
    groups=defaultdict(dict)
    for r in tables['CELL_METRICS']:groups[r['pool'],r['arrival'],r['traffic'],r['label']][r['repeat']]=r
    grouped=[]
    for (pool,arrival,traffic,label),runs in sorted(groups.items()):
        row={'pool':pool,'arrival':arrival,'traffic':traffic,'label':label,'completed_runs':len(runs),
            'requested_frontier_observations':sum(r['requested_frontiers'] for r in runs.values()),
            'commit_over_8_observations':sum(r['commit_over_8'] for r in runs.values()),
            'missed_before_enqueue_observations':sum(r['missed_before_enqueue'] for r in runs.values()),
            'dual_P99_passes':sum(r['dual_P99_pass'] for r in runs.values()),
            'source_frontier_observations_not_IID':True}
        for key in ('Audio_Goodput_2_8','Audio_Goodput_stable_2_8','display_P99','commit_P99','GPU_J_audio_s',
            'WER','CER','authority_eligible_queue_P99','release_to_parent_P99','authority_planner_wall_s',
            'authority_planner_wall_fraction_of_run','authority_planner_per_decision_P99_s',
            'authority_snapshot_to_first_enqueue_total_s','wall_seconds','maximum_observed_target_deferrals',
            'successor_active_decisions','positive_private_forecast_decisions','retired_actual_promise_late'):
            values=[r[key] for r in runs.values()]
            row[key+'_run_median']=None if any(v is None for v in values) else statistics.median(values)
        grouped.append(row)
    csvsave(args.output/'GROUPS.csv',grouped)
    pairs=[]
    labels=sorted({s['label'] for s in specs});repeats=plan['stages'][args.stage].get('expected_repeats',3)
    for key,treatment in groups.items():
        pool,arrival,traffic,label=key
        if label not in ('causal','causal_joint','inherit','reserved_progress','service_cost'):continue
        for base in labels:
            if base==label:continue
            control=groups.get((pool,arrival,traffic,base),{})
            meta={'pool':pool,'arrival':arrival,'traffic':traffic,'treatment':label,'baseline':base}
            if len(control)!=repeats or len(treatment)!=repeats or set(control)!=set(treatment):
                pairs.append(dict(meta,status='INCOMPLETE_NO_COMPARATIVE_CLAIM'));continue
            measures={k:paired(control,treatment,k) for k in ('Audio_Goodput_2_8','Audio_Goodput_stable_2_8',
                'commit_P99','display_P99','GPU_J_audio_s','WER','CER','wall_seconds','authority_eligible_queue_P99','authority_planner_wall_s')}
            pairs.append(dict(meta,status='DESCRIPTIVE_PAIRED_RUN_COMPARISON',metrics=measures,
                baseline_dual_P99_passes=sum(r['dual_P99_pass'] for r in control.values()),
                treatment_dual_P99_passes=sum(r['dual_P99_pass'] for r in treatment.values())))
    report={'status':'PASS_COMPLETE_OBSERVED_DIAGNOSTICS' if not failures and audited else 'INCOMPLETE_OR_NOT_YET_SAFETY_AUDITED',
        'expected_cells':len(expected),'complete_cells':len(tables['CELL_METRICS']),'failures':failures,
        'original_safety_audit_complete':audited,'performance_claim_eligible':not failures and audited,
        'comparisons_include_cost_joint_and_shared_proposer_controls':True,
        'independent_confirmation':False,'scope':'Reused-source diagnostic; actual traces, not counterfactual model execution',
        'activation_is_not_causal_attribution':True,'frontiers_are_not_IID_samples':True,
        'prediction_residuals_include_future_replanning':True,
        'host_timing_scope':'Actual observed Authority planner elapsed wall and snapshot-to-enqueue intervals; not GPU-active time or separately metered Owner CPU energy',
        'guard_ablation_scope':'No same-new-model no-guard arm in the 72-cell plan; old48 only historical diagnosis',
        'new_GPU_calls':0,'plan_sha256':sha(args.plan),'script_sha256':sha(Path(__file__)),
        'safety_audit_summary_sha256':sha(audit_dir/'SUMMARY.json') if (audit_dir/'SUMMARY.json').exists() else None,
        'quality_input_sha256':sha(audit_dir/'SERVICE_CELLS.csv') if (audit_dir/'SERVICE_CELLS.csv').exists() else None,
        'outputs':{name:len(rs) for name,rs in tables.items()}}
    (args.output/'SUMMARY.json').write_text(json.dumps(clean(report),indent=2,allow_nan=False)+'\n',encoding='utf8')
    (args.output/'INDEPENDENT_PAIRS.json').write_text(json.dumps(clean(pairs),indent=2,allow_nan=False)+'\n',encoding='utf8')
    (args.output/'INPUT_MANIFEST.json').write_text(json.dumps(inputs,indent=2)+'\n',encoding='utf8')
    print(json.dumps(clean(report),indent=2))


if __name__=='__main__':main()

"""Owner actual-state opportunity ledger. No rescheduling or neural replay."""
from collections import Counter,defaultdict
import math
from definitions import input_profile,execution_state,ready_before,sha_state,final_outcome

def profile_owner(epoch,dispatches,owner_events,worker_rows,audits,initial_roots,facts,consumer_applied_jobs=(),source_frames=None):
    from feedback_contract import FeedbackCut
    from resilience_inbound import parse_job_id
    jobs={r['job']['job_id']:r['job'] for r in dispatches}
    if len(jobs)!=len(dispatches):raise ValueError('duplicate dispatch ID')
    for row in dispatches:
        j=row['job']
        if parse_job_id(j['job_id']) is None or parse_job_id(j['job_id'])[0]!=epoch:raise ValueError('dispatch job ID is not in its actual Owner namespace')
        if row['owner_epoch']!=epoch or row['physical_slot']!=j['worker'] or row['physical_incarnation']!=j['worker_incarnation']:
            raise ValueError('dispatch physical identity changed')
        if j['dispatch_epoch']!=0:raise ValueError('PILOT24 scope has no session-reset intervention')
        start=FeedbackCut(j['start'])
        for dep in j['frozen_dependencies']:
            if FeedbackCut(dep).state['contract']!=start.state['contract']:raise ValueError('frozen dependency contract differs')
        if source_frames is not None and j['end']!=min(source_frames[j['source_id']],start.frontier+8000):raise ValueError('dispatched job changed original500ms/EOS target')
    installs=[r for r in owner_events if r['kind']=='canonical_install']
    selected={f['body']['job']['job_id']:f for f in facts}
    byseq={f['sequence']:f for f in facts}
    complete={};early={};terminal={};duplicate_receipts=0
    for row in worker_rows:
        e=row['event'];kind=e.get('kind');jid=e.get('job_id')
        if kind not in ('asr_early','completed','abandoned'):continue
        if jid not in jobs:raise ValueError('worker message lacks actual dispatch')
        j=jobs[jid]
        if (e['source_id']!=j['source_id'] or e['worker']!=j['worker'] or
            e['dispatch_epoch']!=j['dispatch_epoch'] or row['physical_slot']!=j['worker'] or
            row['physical_incarnation']!=j['worker_incarnation'] or e['worker_incarnation']!=j['worker_incarnation']):
            raise ValueError('worker event changed job/role/channel identity')
        start=e['start_state'] if kind=='asr_early' else e['start']
        if sha_state(start)!=sha_state(j['start']):raise ValueError('worker event changed complete frozen start')
        if kind=='asr_early':early.setdefault(jid,row)
        else:
            if jid in terminal:
                old=terminal[jid]['event']
                for key in ('kind','start','end','record','proof'):
                    if old.get(key)!=e.get(key):raise ValueError('changed duplicate terminal receipt')
                duplicate_receipts+=1
            terminal.setdefault(jid,row)
            if kind=='completed':
                r=e['record']
                if r['role']!='authority' or r['candidate_handoff'] is not False or sha_state(e['end'])!=r['end_state'] or r['start_state']!=sha_state(j['start']):
                    raise ValueError('completed result is not owned original full C/U')
                fields=('worker_job_begin_perf','model_start','model_end','worker_job_end_perf')
                if all(r.get(k) is not None for k in fields):
                    values=[r[k] for k in fields]
                    if not all(math.isfinite(x) for x in values) or values!=sorted(values):raise ValueError('invalid original execution clocks')
                    if abs(r['model_seconds']-(r['model_end']-r['model_start']))>1e-8:raise ValueError('original infer timer changed')
                    if e.get('sent_perf') is not None and e['sent_perf']<r['worker_job_end_perf']:raise ValueError('terminal sent before worker end')
                    if row.get('channel_received_perf') is not None and e.get('sent_perf') is not None and row['channel_received_perf']<e['sent_perf']:raise ValueError('terminal channel clock changed')
                    if row.get('owner_dequeued_perf') is not None and row.get('channel_received_perf') is not None and row['owner_dequeued_perf']<row['channel_received_perf']:raise ValueError('Owner dequeue clock changed')
                complete.setdefault(jid,row)
    discarded={};abandoned={};lifecycle={};removal_times={};promotions=[]
    for row in audits:
        kind=row['kind'];b=row.get('body',{});observed=row.get('observed')
        if kind=='promotion':
            jid=b['job_id'];j=jobs[jid]
            if sha_state(b['owned_job']['start'])!=sha_state(j['start']) or b['actual_parent_sha']!=sha_state(b['actual_parent_state']):
                raise ValueError('promotion binding changed')
            promotions.append(dict(row))
        elif kind in ('discarded_full','abandoned_full'):
            jid=b['job']['job_id'];j=jobs[jid]
            if sha_state(b['job']['start'])!=sha_state(j['start']):raise ValueError('terminal proof changed frozen job')
            target=discarded if kind=='discarded_full' else abandoned
            if jid in target:raise ValueError('duplicate disposition')
            target[jid]=row;removal_times[jid]=observed
        elif kind=='worker_lost':
            for jid in b['retired_live_jobs']:lifecycle[jid]=row;removal_times[jid]=observed
        elif kind=='inbound_disposition' and b.get('outcome',{}).get('kind')=='fenced_terminal':
            jid=b['outcome']['job']['job_id'];lifecycle[jid]=row;removal_times[jid]=observed
    receipts={r['job_id']:r for r in owner_events if r['kind']=='validated_full_receipt'}
    buffered={jid for jid,r in receipts.items() if r['outcome_kind']=='buffered_full'}
    events=[]
    for j in jobs.values():events.append((j['owner_dispatch_order']['sequence'],'dispatch',j))
    for r in receipts.values():events.append((r['complete_receipt_order']['sequence'],'receipt',r))
    for r in installs:events.append((r['canonical_install_order']['sequence'],'install',r))
    sequences=[r[0] for r in events]
    if len(sequences)!=len(set(sequences)):raise ValueError('ambiguous actual policy execution sequence')
    roots=dict(initial_roots);witnesses={sid:{s['frontier']:s} for sid,s in roots.items()}
    tracked={};sticky={};decisions=[];counts=Counter();job_summaries={}
    for order,kind,payload in sorted(events):
        if kind=='dispatch':
            j=payload;sid=j['source_id']
            if sha_state(roots[sid])!=j['birth_canonical_sha'] or not j.get('frozen_dependencies') or sha_state(j['frozen_dependencies'][0])!=j['birth_canonical_sha'] or sha_state(j['frozen_dependencies'][-1])!=sha_state(j['start']):
                raise ValueError('actual dispatch frozen chain/birth root mismatch')
            tracked[j['job_id']]='live';continue
        if kind=='receipt':
            jid=payload['job_id']
            if payload['outcome_kind']=='buffered_full':tracked[jid]='ready'
            else:tracked.pop(jid,None)
            continue
        r=payload;sid=r['source_id'];instant=r['canonical_install_order']['observed_perf'];selected_id=r['job_id']
        fact=byseq[r['receipt']['sequence']];body=fact['body']
        if body['job']['job_id']!=selected_id or body['source_id']!=sid or sha_state(body['parent_state'])!=sha_state(roots[sid]):
            raise ValueError('actual install does not bind the selected durable parent chain')
        if r['next_state_sha']!=sha_state(body['next_state']) or r['parent_state_sha']!=sha_state(body['parent_state']):raise ValueError('install state digest mismatch')
        roots[sid]=body['next_state'];witnesses[sid][roots[sid]['frontier']]=roots[sid];tracked.pop(selected_id,None)
        counts['actual_canonical_install_events']+=1
        other_ready={x['job_id']:x for x in r['other_ready_full_receipts_before_install']}
        for jid,item in other_ready.items():
            if jid not in jobs or item['start_sha']!=sha_state(jobs[jid]['start']) or item['end']!=jobs[jid]['end'] or item.get('complete_receipt_order') is None or item['complete_receipt_order']['sequence']>=order:
                raise ValueError('actual ready-bank snapshot has unbound/unready full receipt')
        counts['install_boundaries_with_other_ready_bank']+=bool(other_ready)
        counts['other_ready_bank_occupancy_events']+=len(other_ready)
        if ready_before(r.get('complete_receipt_order'),r['canonical_install_order'],selected_id in buffered):counts['actual_owner_ready_reuse']+=1
        for jid,state in list(tracked.items()):
            j=jobs[jid]
            if j['source_id']!=sid:continue
            remove=removal_times.get(jid)
            if remove is not None and remove<instant:tracked.pop(jid,None);continue
            if remove is not None and remove==instant:
                counts['ambiguous_equal_clock_terminal_boundaries']+=1;continue
            if (state=='ready')!=(jid in other_ready):raise ValueError('reconstructed Owner ready bank disagrees with actual install snapshot')
            p=input_profile(j,roots[sid],witnesses[sid],0,sticky.get(jid))
            if p['treatment_disagreement'] and jid not in sticky:
                sticky[jid]=dict(p['ancestor_fence'],first_install_order=order,
                    first_install_observed=instant,first_input_status=p['input_status'])
                p['ancestor_fence']=sticky[jid]
            e=terminal.get(jid,{}).get('event',{});record=e.get('record')
            execution=execution_state(record,e,instant,state=='ready')
            speculative=not j.get('started_on_canonical',j['birth_canonical_sha']==sha_state(j['start']))
            confirmed=speculative and p['input_status']=='currently_confirmed' and p['fullcall_retains']
            active=confirmed and execution=='native_model_active'
            parent_receipt_time=r.get('complete_receipt_order',{}).get('observed_perf')
            active_through_bound=bool(active and parent_receipt_time is not None and record['model_start']<=parent_receipt_time and record['model_end']>instant)
            outcome=final_outcome(jid,selected,discarded,abandoned,lifecycle,
                {x['job_id'] for x in installs},consumer_applied_jobs)
            row=dict(owner_epoch=epoch,install_sequence=order,install_observed=instant,
                source_id=sid,job_id=jid,worker=j['worker'],worker_incarnation=j['worker_incarnation'],
                dispatch_epoch=j['dispatch_epoch'],frozen_start_sha=sha_state(j['start']),
                frozen_start_frontier=j['start']['frontier'],target=j['end'],originally_speculative=speculative,
                execution_state=execution,model_active_compatible_confirmation=active,
                model_active_through_parent_receipt_install_interval=active_through_bound,
                complete_receipt_before_install=state=='ready',later_actual_outcome=outcome,**p)
            decisions.append(row);counts['tracked_job_install_decisions']+=1
            counts['tracked_execution_'+execution+'_decisions']+=1
            if confirmed:counts['confirmed_input_'+execution+'_events']+=1
            if active:counts['model_active_compatible_confirmation_events']+=1
            if active_through_bound:counts['model_active_guaranteed_interval_events']+=1
            if p['direct_compatible_retained_by_both']:counts['ordinary_direct_compatible_both_retain_events']+=1
            if p['pending_retained_by_both']:counts['ordinary_pending_both_retain_events']+=1
            if p['treatment_disagreement']:
                counts['ancestor_disagreement_events']+=1
                counts['ancestor_disagreement_'+p['input_status']+'_events']+=1
            key=job_summaries.setdefault(jid,dict(job_id=jid,source_id=sid,owner_epoch=epoch,
                model_active_compatible_confirmation_events=0,ancestor_disagreement_events=0,
                model_active_guaranteed_interval_events=0,ordinary_direct_both_retain_events=0,
                ever_currently_confirmed=False,ever_complete_start_refuted_while_tracked=False,
                first_disagreement_input_status=None,later_actual_outcome=outcome))
            key['model_active_compatible_confirmation_events']+=int(active)
            key['model_active_guaranteed_interval_events']+=int(active_through_bound)
            key['ancestor_disagreement_events']+=int(p['treatment_disagreement'])
            key['ordinary_direct_both_retain_events']+=int(p['direct_compatible_retained_by_both'])
            key['ever_currently_confirmed']|=p['input_status']=='currently_confirmed'
            key['ever_complete_start_refuted_while_tracked']|=p['input_status']=='complete_start_refuted'
            key['last_observed_input_status']=p['input_status']
            if p['treatment_disagreement'] and key['first_disagreement_input_status'] is None:key['first_disagreement_input_status']=p['input_status']
    for jid,profile in job_summaries.items():
        j=jobs[jid]
        actual=next((f['body']['next_state'] for f in facts if f['body']['source_id']==j['source_id'] and f['body']['next_state']['frontier']==j['start']['frontier']),None)
        profile['retrospective_eventual_actual_start_status']=('actual_same_frontier_matches' if sha_state(actual)==sha_state(j['start']) else 'actual_same_frontier_refutes') if actual is not None else 'same_frontier_not_observed'
        profile['retrospective_outcomes_not_used_in_decision_predicate']=True
    counts['unique_model_active_compatible_confirmation_jobs']=sum(r['model_active_compatible_confirmation_events']>0 for r in job_summaries.values())
    counts['unique_model_active_guaranteed_interval_jobs']=sum(r['model_active_guaranteed_interval_events']>0 for r in job_summaries.values())
    counts['unique_ancestor_disagreement_jobs']=sum(r['ancestor_disagreement_events']>0 for r in job_summaries.values())
    counts['unique_ordinary_direct_both_retain_jobs']=sum(r['ordinary_direct_both_retain_events']>0 for r in job_summaries.values())
    counts['ancestor_disagreement_later_legally_applied_jobs']=sum(r['ancestor_disagreement_events']>0 and r['later_actual_outcome'] in ('later_selected_original_full_result_owner_installed','later_selected_durable_fact_consumer_applied') for r in job_summaries.values())
    counts['ancestor_disagreement_durable_selected_application_unobserved_jobs']=sum(r['ancestor_disagreement_events']>0 and r['later_actual_outcome']=='later_durable_selected_application_unobserved' for r in job_summaries.values())
    for state in ('actual_same_frontier_matches','actual_same_frontier_refutes','same_frontier_not_observed'):
        counts['ancestor_disagreement_eventual_'+state+'_jobs']=sum(r['ancestor_disagreement_events']>0 and r['retrospective_eventual_actual_start_status']==state for r in job_summaries.values())
    counts['ancestor_disagreement_later_full_refused_jobs']=sum(r['ancestor_disagreement_events']>0 and r['later_actual_outcome']=='later_full_result_refused' for r in job_summaries.values())
    counts['recorded_promotion_events']=len(promotions);counts['recorded_unique_promoted_jobs']=len({r['body']['job_id'] for r in promotions})
    hints=[r for r in owner_events if r['kind'] in ('known_invalid_C_skip_hint','policy_C_entry_skip_hint','input_or_coverage_reason_observed_without_C_entry_skip')]
    for h in hints:
        counts['UIR_suppressed_hint_observations' if h.get('c_entry_skip_hint_sent') is False else 'sent_C_entry_hint_observations']+=1
        counts['hint_reason_'+h['proof']['kind']]+=1
    before_c=[];late=[];work=[]
    for jid,j in jobs.items():
        e=terminal.get(jid,{}).get('event',{});rec=e.get('record',{})
        if rec:worker=rec.get('worker_job_wall_seconds');infer=rec.get('model_seconds')
        elif e.get('worker_job_begin_perf') is not None and e.get('worker_job_end_perf') is not None:
            worker=e['worker_job_end_perf']-e['worker_job_begin_perf'];infer=None
        else:worker=infer=None
        work.append(dict(job_id=jid,source_id=j['source_id'],worker=j['worker'],worker_incarnation=j['worker_incarnation'],
            start_sha=sha_state(j['start']),target=j['end'],dispatch_perf=j['dispatched_perf'],
            worker_wall_seconds=worker,observed_infer_wall_seconds=infer,
            terminal_kind=e.get('kind'),selected_durable=jid in selected,
            before_C_exit=jid in abandoned,full_result_refused=jid in discarded))
        if jid in selected and jid in early:
            work[-1]['own_ASR_prediction_differs_from_selected_full_end']=sha_state(early[jid]['event']['projection']['end'])!=sha_state(selected[jid]['body']['next_state'])
        if jid in abandoned:
            b=abandoned[jid]['body'];t=b.get('worker_terminal_event',e);proof=b['proof']
            if not (t.get('asr_prefix_executed') is True and t.get('learned_C_executed') is False and t.get('C_U_completed') is False and t.get('feedback_cut_emitted') is False):raise ValueError('before-C exit terminal is incomplete')
            successors=sorted((q for q in jobs.values() if q['worker']==j['worker'] and q['worker_incarnation']==j['worker_incarnation'] and q['dispatched_perf']>t['worker_job_end_perf']),key=lambda q:q['dispatched_perf'])
            before_c.append(dict(job_id=jid,source_id=j['source_id'],proof=proof,worker_wall_seconds=worker,infer_wall_seconds=None,
                actual_successor_job=successors[0]['job_id'] if successors else None,
                observed_end_to_successor_dispatch_gap_s=successors[0]['dispatched_perf']-t['worker_job_end_perf'] if successors else None,
                scope='Actual checkpoint exit and successor; gap is not a causal delay saving'))
        if jid in discarded and rec:
            proof=discarded[jid]['body']['proof'];a=early.get(jid,{}).get('event',{})
            witness=next((f for f in facts if f['body']['next_state_sha256']==proof.get('actual_cut_sha')),None)
            pe=witness['body']['record'].get('model_end') if witness else None;upper=a.get('produced_perf')
            late.append(dict(job_id=jid,source_id=j['source_id'],proof=proof,
                original_before_C_checkpoint_upper_bound=upper,parent_original_infer_end=pe,
                parent_result_unfinished_at_original_checkpoint_upper_bound=(pe>upper) if pe is not None and upper is not None else None,
                scope='produced_perf is after original check and before publication/C entry; a new later recheck is not assessed'))
    counts['actual_before_C_exits']=len(before_c)
    counts['known_invalid_or_covered_before_C_exits']=sum(r['proof']['kind'] in ('actual_canonical_disagrees_with_complete_start','covered_by_actual_canonical') for r in before_c)
    counts['before_C_exits_with_actual_successor_dispatch']=sum(r['actual_successor_job'] is not None for r in before_c)
    counts['late_full_result_refusals']=len(late)
    counts['worker_interval_missing_jobs']=sum(r['worker_wall_seconds'] is None for r in work)
    counts['infer_interval_missing_jobs']=sum(r['observed_infer_wall_seconds'] is None for r in work)
    counts['observed_worker_wall_seconds']=sum(r['worker_wall_seconds'] for r in work if r['worker_wall_seconds'] is not None)
    counts['observed_infer_wall_seconds']=sum(r['observed_infer_wall_seconds'] for r in work if r['observed_infer_wall_seconds'] is not None)
    groups=defaultdict(list)
    for w in work:groups[w['source_id'],w['start_sha'],w['target']].append(w)
    redispatch=[dict(source_id=k[0],start_sha=k[1],target=k[2],actual_jobs=[r['job_id'] for r in sorted(v,key=lambda r:r['dispatch_perf'])],
        reissues=len(v)-1,observed_worker_wall_seconds=sum(r['worker_wall_seconds'] for r in v if r['worker_wall_seconds'] is not None)) for k,v in groups.items() if len(v)>1]
    counts['same_complete_input_target_redispatches']=sum(r['reissues'] for r in redispatch)
    counts['duplicate_terminal_receipts_not_double_billed']=duplicate_receipts
    counts['selected_original_own_prediction_changed_jobs']=sum(r.get('own_ASR_prediction_differs_from_selected_full_end') is True for r in work)
    return dict(counts=dict(counts),decisions=decisions,job_summaries=list(job_summaries.values()),
                before_C_exits=before_c,late_refusals=late,work=work,redispatch=redispatch)

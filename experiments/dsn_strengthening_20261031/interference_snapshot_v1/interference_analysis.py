"""Independent two-client ledger, actual-dispatch, worker-life and result audit.

No global-origin shortcut is used for endpoint metrics. Instrumented proposals
alone never count as executed interference. Raw logs remain on the experiment
disk; summaries explicitly retain all A/B requests and all offered EOS.
"""
from __future__ import annotations
import hashlib,math,pathlib
from common import need,read,lines,sha,canonical,verified_facts
from interference_contract import validate_contract,CLIENTS,A,B,ORDER,OFFSET
from endpoints import recount
from audit_results import selected_trace

PASS='PASS_TWO_CLIENT_COMPLETE_TASK_CLOCK_REFERENCE_AND_OBSERVATION'

def audit_clocks(config,origin,origins,ledger,ingress,consumer):
    partition=validate_contract(config);sources={s['source_id']:s for s in config['settings']['sources']}
    admitted={};completed={};last=-math.inf
    for row in ledger:
        need(row['kind'] in ('request_admitted','request_complete'),'unknown request ledger event')
        sid=row['source_id'];need(sid in partition,'foreign request in ledger');client,index=partition[sid]
        need(row['client_id']==client and row['client_request_index']==index,'client partition/index differs')
        need(math.isfinite(row['observed']) and row['observed']>=last,'request ledger clock reordered');last=row['observed']
        target=admitted if row['kind']=='request_admitted' else completed;need(sid not in target,'duplicate admission/completion');target[sid]=row
        if row['kind']=='request_complete':need(sid in admitted,'completion before admission')
    need(set(origins)==set(admitted)==set(completed)==set(sources),'incomplete request partition or ledger')
    need(origins[A[0]]==origin and origins[B[0]]==origin+OFFSET,'first-client phase changed or origin rebased')
    count=0
    for client,order in CLIENTS.items():
        for index,sid in enumerate(order):
            entry=admitted[sid];finish=completed[sid]
            need(math.isfinite(origins[sid]) and entry['request_origin_perf']==origins[sid] and entry['observed']>=origins[sid],'admission/origin binding differs')
            if index==0:
                expected=origin+(OFFSET if client=='B' else 0.)
                need(entry['planned_first_origin_perf']==expected and entry['previous_source_id'] is None and entry['previous_complete_perf'] is None,'first request acquired invented predecessor/phase')
            else:
                previous=order[index-1];need(entry['previous_source_id']==previous and entry['previous_complete_perf']==completed[previous]['consumer_observed_perf'],'cross-client/incorrect EOS release')
                need(entry['observed']==origins[sid] and origins[sid]>=completed[previous]['consumer_observed_perf'] and entry['planned_first_origin_perf'] is None,'next request began before its actual client EOS')
            need(finish['EOS_frontier']==finish['certified_frontier']==sources[sid]['frames'] and finish['request_origin_perf']==origins[sid] and finish['consumer_observed_perf']==finish['observed'],'completion is not original request EOS')
            need(finish['completion_callback_perf']>=finish['observed']>=entry['observed'],'completion callback clock differs')
            need(any(r['kind']=='canonical' and r['source_id']==sid and r['observed']==finish['observed'] and r['certified_frontier']==sources[sid]['frames'] for r in consumer),'completion lacks actual canonical Consumer EOS')
            own=[r for r in ingress if r['source_id']==sid];expected=list(range(8000,sources[sid]['frames'],8000))+[sources[sid]['frames']]
            need([r['frontier'] for r in own]==expected,'missing/duplicate/reordered ingress obligation including EOS')
            need(finish['observed']>=own[-1]['observed'],'certified EOS preceded actual EOS ingress')
            for row in own:
                need(abs(row['original_offer']-(origins[sid]+row['frontier']/16000))<=1e-6,'global-origin shortcut/rebased offer')
                need(row['observed']>=max(row['original_offer'],entry['observed']) and row['audio_sha256']==sources[sid]['audio_sha256'],'unadmitted/early/foreign accepted input');count+=1
    need(all(r['source_id'] in sources for r in ingress),'foreign ingress sid')
    for row in consumer:need(row['source_id'] in admitted and row['observed']>=admitted[row['source_id']]['observed'],'future sid borrowed Consumer work')
    return dict(status='PASS_TWO_INDEPENDENT_CLIENTS_ACTUAL_EOS_ALL_OFFERS',requests=4,clients=2,first_phase_seconds=OFFSET,accepted_frontiers_checked=count,EOS_included=True,first_admission_lag_seconds={c:admitted[o[0]]['observed']-origins[o[0]] for c,o in CLIENTS.items()},next_release_lag_seconds={c:origins[o[1]]-completed[o[0]]['consumer_observed_perf'] for c,o in CLIENTS.items()})

def audit_continuity(config,ready,events,dispatch):
    need(len(ready)==2 and len({r['pid'] for r in ready})==2 and {r['gpu'] for r in ready}=={0,1},'not two unique READY model PIDs/boards')
    slots={r['worker']:r['pid'] for r in ready};need(set(slots)=={'full0','full1'},'foreign model slot')
    starts=[r for r in events if r['kind']=='worker_started']
    need(len(starts)==2 and all(r['incarnation']==0 and slots.get(r['slot'])==r['pid'] for r in starts),'model reload/replacement during finite client requests')
    need(not any(r['kind']=='worker_death_confirmed' for r in events),'normal opportunity trial lost a worker')
    by={sid:set() for sid in ORDER}
    for row in dispatch:
        need(row['owner_epoch']==0 and row['physical_incarnation']==0 and row['pid']==slots[row['physical_slot']],'foreign/replaced Owner or worker PID dispatched')
        need(row['job']['source_id'] in by,'foreign dispatch sid');by[row['job']['source_id']].add(row['pid'])
    need(all(by.values()),'request has no real model dispatch')
    return dict(status='PASS_TWO_CONTINUOUS_ORIGINAL_MODEL_PIDS',model_loads=2,owner_epochs=1,worker_PIDs=sorted(slots.values()),per_request_executing_PIDs={sid:sorted(pids) for sid,pids in by.items()})

def digest(state):return hashlib.sha256(canonical(state)).hexdigest()

def audit_dispatch(config,observations,dispatch,worker_results,owner_events,genesis,ingress,canonical_facts=()):
    partition=validate_contract(config);sources={s['source_id']:s for s in config['settings']['sources']}
    actual={r['job']['job_id']:r for r in dispatch};need(len(actual)==len(dispatch)==len(observations),'registration/actual dispatch cardinality differs')
    need(len({r['job_id'] for r in observations})==len(observations) and {r['job_id'] for r in observations}==set(actual),'proposal-only/unobserved/duplicate dispatch')
    terminals={}
    for row in worker_results:
        event=row['event']
        if event['kind'] in ('completed','abandoned'):
            jid=event['job_id'];need(jid not in terminals,'duplicate physical terminal in normal trial');terminals[jid]=row
    need(set(actual)==set(terminals),'actual dispatch lacks complete physical worker terminal witness')
    installs=[r for r in owner_events if r['kind']=='canonical_install'];inversions=[];checked=0;held=[]
    selected={r['body']['job']['job_id']:r for r in canonical_facts}
    need(len(selected)==len(canonical_facts)==len(installs),'actual install/durable selection cardinality differs')
    for event in installs:
        need(event['job_id'] in selected,'install lacks durable selection');fact=selected[event['job_id']]
        need(event['source_id']==fact['body']['source_id'] and event['next_state_sha']==digest(fact['body']['next_state']) and event['parent_state_sha']==digest(fact['body']['parent_state']) and event['receipt']['sequence']==fact['sequence'],'actual install does not bind original durable state')
    for slot in ('full0','full1'):
        work=[]
        for jid,row in actual.items():
            if row['physical_slot']!=slot:continue
            event=terminals[jid]['event'];record=event['record'] if event['kind']=='completed' else event
            work.append((record['worker_job_begin_perf'],record['worker_job_end_perf']))
        work.sort();need(all(left[1]<=right[0] for left,right in zip(work,work[1:])),'physical worker calls overlap on one leased slot')
    for obs in observations:
        jid=obs['job_id'];row=actual[jid];job=row['job'];terminal=terminals[jid];event=terminal['event']
        need(obs['owner_epoch']==row['owner_epoch']==0 and obs['worker']==row['physical_slot'] and obs['worker_incarnation']==row['physical_incarnation']==0,'observation physical namespace differs')
        for key in ('source_id','start','end','dispatch_epoch'):need(obs[key]==job[key],'observation/actual UID input binding differs: '+key)
        need(obs['original_dispatched_perf']==job['dispatched_perf'],'observation is not original dispatch clock')
        need(terminal['physical_slot']==row['physical_slot'] and terminal['physical_incarnation']==row['physical_incarnation'] and event['worker']==row['physical_slot'] and event['source_id']==job['source_id'] and event['dispatch_epoch']==job['dispatch_epoch'] and event['start']==job['start'],'physical result did not execute the observed actual UID/input')
        record=event['record'] if event['kind']=='completed' else event
        need(job['dispatched_perf']<=record['worker_job_begin_perf']<=record['worker_job_end_perf']<=event['sent_perf'],'physical execution clock differs')
        if config['arm']=='fullcall':
            need(obs['proposal_id'] is not None and obs['proposal_before_perf']<=obs['proposal_after_perf']<=job['dispatched_perf']<=obs['registration_before_perf']<=obs['registration_after_perf'],'original proposal/register clock binding differs')
            need(job['end']<=obs['accepted_argument'] and obs['decision_snapshot_perf']==obs['proposal_before_perf'],'proposal dispatched beyond original accepted argument/snapshot');decision=obs['decision_snapshot_perf']
        else:
            need(obs['proposal_id'] is None and obs['started_on_current_canonical'],'Conservative became speculative');decision=obs['decision_snapshot_perf']
        need(set(obs['canonical_cuts'])==set(obs['accepted_before'])==set(obs['session_epochs'])==set(sources),'incomplete snapshot session partition')
        need(job['end']<=obs['accepted_before'][job['source_id']],'actual dispatch exceeded accepted input at observation')
        for sid in sources:
            previous=[r for r in installs if r['source_id']==sid and r['observed']<=decision]
            expected=previous[-1]['next_state_sha'] if previous else digest(genesis[sid])
            need(digest(obs['canonical_cuts'][sid])==expected,'observed Canonical snapshot differs from actual install prefix')
            seen=[r['frontier'] for r in ingress if r['source_id']==sid and r['observed']<=decision]
            need(0<=obs['accepted_before'][sid]<=max(seen,default=0),'snapshot invented future accepted input')
        prior=obs['live_jobs_before']+obs['completed_jobs_before'];need(len({r['job_id'] for r in prior})==len(prior),'snapshot duplicates live/completed work')
        for old in prior:
            need(old['job_id'] in actual and actual[old['job_id']]['job']['dispatched_perf']<job['dispatched_perf'],'snapshot references unknown/future work')
            for key in ('source_id','start','end','dispatch_epoch'):need(old[key]==actual[old['job_id']]['job'][key],'snapshot changed an existing owned input')
        need(not any(actual[j['job_id']]['physical_slot']==row['physical_slot'] for j in obs['live_jobs_before']),'dispatch stole a still-live physical lease')
        current=(job['start']==obs['canonical_cuts'][job['source_id']]);need(current==obs['started_on_current_canonical'],'conditional classification differs from whole input')
        ready=[]
        for sid,cut in obs['canonical_cuts'].items():
            target=min(sources[sid]['frames'],cut['frontier']+8000)
            exists=any(j['source_id']==sid and j['dispatch_epoch']==obs['session_epochs'][sid] and j['start']==cut and j['end']==target for j in prior)
            if target>cut['frontier'] and target<=obs['accepted_before'][sid] and not exists:ready.append(sid)
        if not current:
            for sid in ready:
                if partition[sid][0]==partition[job['source_id']][0]:continue
                inversions.append(dict(job_id=jid,physical_slot=row['physical_slot'],pid=row['pid'],dispatch_perf=job['dispatched_perf'],proposal_before_perf=decision,speculative_source_id=job['source_id'],speculative_client=partition[job['source_id']][0],ready_Canonical_source_id=sid,ready_Canonical_client=partition[sid][0],ready_Canonical_frontier=obs['canonical_cuts'][sid]['frontier'],ready_Canonical_sha=digest(obs['canonical_cuts'][sid]),accepted_frontier=obs['accepted_before'][sid],actual_worker_begin_perf=record['worker_job_begin_perf'],actual_worker_end_perf=record['worker_job_end_perf'],actual_terminal_kind=event['kind']))
        held.append(dict(job_id=jid,started_on_current_canonical=current,all_ready_current_Canonical_sids=ready));checked+=1
    return dict(status='PASS_OBSERVED_ORIGINAL_PROPOSALS_BOUND_TO_ACTUAL_DISPATCH_AND_WORKER_LIFE',actual_dispatches_checked=checked,dispatch_boundary_inversions=len(inversions),B_current_ready_inversions=sum(r['ready_Canonical_client']=='B' for r in inversions),inversions=inversions,dispatch_classification=held,observation_boundary='Trusted read-only coordinator snapshot checked against raw dispatch, actual worker terminal, ingress and installed Canonical prefix. No proposal-only count, no hardware/capacity guarantee, no inference that future arrivals were ready earlier.')

def held_views(rows,service_end):
    result=[]
    for sid in ORDER:
        own=[r for r in rows if r['source_id']==sid];duration=0.
        for index,row in enumerate(own):
            end=own[index+1]['observed'] if index+1<len(own) else service_end
            if row['visible_frontier']>row['certified_frontier']:duration+=max(0.,end-row['observed'])
        result.append(dict(source_id=sid,actual_Consumer_rows=len(own),provisional_rows=sum(r['visible_frontier']>r['certified_frontier'] for r in own),provisional_view_held_seconds=duration,actual_last_held_view=own[-1],scope='Actual Consumer-held whole view; provisional frontier is distinct from durable C/U authority and human correctness.'))
    return result

def complete_metrics(rows,sources,origins):
    metric=recount(rows,sources,origins);frontiers=metric['frontiers']
    metric.update(EOS_C8_misses=sum(r['is_EOS'] and not r['C8'] for r in frontiers),nonEOS_D2_misses=sum(not r['is_EOS'] and not r['D2'] for r in frontiers),nonEOS_C8_misses=sum(not r['is_EOS'] and not r['C8'] for r in frontiers))
    return metric

def analyze_interference(out):
    out=pathlib.Path(out);config=read(out/'CONFIG.json');validate_contract(config);sources={s['source_id']:s for s in config['settings']['sources']};origins=read(out/'REQUEST_ORIGINS.json');origin=read(out/'ORIGIN.json')['origin_perf'];end=read(out/'SERVICE_END.json')['service_end_perf']
    rows=lines(out/'consumer.jsonl');ledger=lines(out/'request_ledger.jsonl');ingress=lines(out/'ingress.jsonl')
    need(config['require_reference'] is True and sha(config['reference_details'])==config['reference_details_sha256'] and sha(config['reference_gate'])==config['reference_gate_sha256'] and read(config['reference_gate'])['status'].startswith('PASS'),'legal original reference changed/missing')
    clocks=audit_clocks(config,origin,origins,ledger,ingress,rows);semantic=selected_trace(out,config,read(config['reference_details']),config['settings']['source_commit'])
    attempts=list(out.glob('owner_e*'));need(len(attempts)==1 and attempts[0].name=='owner_e0','normal opportunity trial restarted Owner')
    dispatch=lines(out/'owner_e0/dispatch.jsonl');worker=lines(out/'owner_e0/worker_results.jsonl');events=lines(out/'owner_e0/owner_events.jsonl');ready=[r['event'] for r in worker if r['event']['kind']=='ready']
    continuity=audit_continuity(config,ready,events,dispatch);selected_facts=[r for r in verified_facts(out/'facts.wal') if r['kind']=='canonical'];observed=audit_dispatch(config,lines(out/'OWNER_OBSERVATIONS_e0.jsonl'),dispatch,worker,events,read(out/'GENESIS.json'),ingress,selected_facts)
    complete={r['source_id']:r for r in ledger if r['kind']=='request_complete'};per=[];clients={}
    for sid in ORDER:per.append(dict(source_id=sid,client_id='A' if sid in A else 'B',request_origin_perf=origins[sid],actual_Consumer_EOS_perf=complete[sid]['consumer_observed_perf'],primary=complete_metrics([r for r in rows if r['source_id']==sid],{sid:sources[sid]},{sid:origins[sid]})))
    for client,order in CLIENTS.items():
        metrics=[r['primary'] for r in per if r['source_id'] in order]
        clients[client]=dict(requests=list(order),worst_request_D99=max(r['primary_linear_all_offered_D99'] for r in metrics),worst_request_C99=max(r['primary_linear_all_offered_C99'] for r in metrics),D2_misses_all_offered=sum(r['D2_misses_all_offered'] for r in metrics),C8_misses_all_offered=sum(r['C8_misses_all_offered'] for r in metrics),EOS_D2_misses=sum(r['EOS_D2_misses'] for r in metrics),EOS_C8_misses=sum(r['EOS_C8_misses'] for r in metrics),nonEOS_D2_misses=sum(r['nonEOS_D2_misses'] for r in metrics),nonEOS_C8_misses=sum(r['nonEOS_C8_misses'] for r in metrics),dual_deadline_audio_credit_seconds=sum(r['dual_deadline_audio_credit_seconds'] for r in metrics))
    from resilience_metrics import fact_audit,consumer_audit,power_metrics,history_metrics
    roots,facts,processed=fact_audit(out/'facts.wal',sources);authority=consumer_audit(rows,facts)
    need(authority['durable_facts_not_yet_consumed']==0,'durable selected fact not actually consumed')
    return dict(gate=PASS,experiment_id=config['experiment_id'],cell_id=config['cell_id'],arm=config['arm'],repeat=config['repeat'],harness_source_commit=config['harness_source']['source_commit'],actual_NN_source_commit=config['settings']['source_commit'],request_contract=config['request_contract'],primary=complete_metrics(rows,sources,origins),per_request=per,per_client=clients,original_model_continuity=continuity,dispatch_observation=observed,actual_held_views=held_views(rows,end),authority=authority,energy=power_metrics(out,origin,end),history=history_metrics(out),integrity=dict(original_reference=semantic,request_clock=clocks,all_original_obligations_eventually_processed=True),scope='Two preregistered closed-loop clients, four distinct original EOS requests, fixed2s first phase. Original NN59, scheduling proposals and protected C/U unchanged. No open-arrival capacity, fairness, D2 guarantee, online VAD or natural prevalence claim.')

def opportunity_decision(results,*,final=False):
    expected=4 if final else 2;need(len(results)==expected,'opportunity decision requires frozen pair/repeats')
    by={(r['arm'],r['repeat']):r['summary'] for r in results};need(len(by)==expected,'duplicate strategy/repeat')
    checks=[]
    for rep in range(2 if final else 1):
        control=by[('conservative',rep)];full=by[('fullcall',rep)]
        need(control['gate']==full['gate']==PASS,'opportunity input lacks full semantic/clock/observation integrity')
        feasible=all(r['primary']['C8_misses_all_offered']==0 and r['primary']['missing_C_frontiers']==r['primary']['missing_D_frontiers']==0 for r in control['per_request'])
        c=control['per_client']['B']['worst_request_C99'];f=full['per_client']['B']['worst_request_C99'];need(math.isfinite(c) and math.isfinite(f),'B worst-request C99 not finite')
        extra=full['per_client']['B']['C8_misses_all_offered']-control['per_client']['B']['C8_misses_all_offered'];latency=f-c>=max(1.,.2*c);inversion=full['dispatch_observation']['B_current_ready_inversions']>0
        checks.append(dict(repeat=rep,Conservative_all_four_requests_C8_no_miss=feasible,AlwaysFull_actual_B_current_ready_inversion=inversion,B_worst_request_C99_conservative=c,B_worst_request_C99_AlwaysFull=f,B_C99_difference_seconds=f-c,B_extra_C8_frontier_misses=extra,B_C99_regression_ge_1s_and20percent=latency,B_extra_C8_frontier_misses_ge4=extra>=4,repeat_GO=feasible and inversion and (latency or extra>=4)))
    passed=all(r['repeat_GO'] for r in checks)
    status=('GO_REAL_SHARED_RESOURCE_ADMISSION_OPPORTUNITY' if final else 'CONTINUE_PREWRITTEN_SECOND_OPPORTUNITY_PAIR') if passed else 'NO_GO_FIXED_TWO_CLIENT_ADMISSION_OPPORTUNITY'
    return dict(status=status,checks=checks,shared_credit_gain_required=False,all_A_B_metrics_and_energy_retained=True,maximum_actual_trials=4,scope='Preregisitered engineering opportunity gate. Observed inversion plus paired B service regression; no causal proof of all latency, no scheduler benefit measured, no result-dependent source/phase/threshold repair.')

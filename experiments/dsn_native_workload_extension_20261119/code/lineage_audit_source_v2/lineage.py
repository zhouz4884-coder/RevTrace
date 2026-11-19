"""Independent full-JSON lineage/time classifier. No model or tensor decoding."""
from collections import Counter
import hashlib,json,math,re

NN='11453433c154aeffbff703c4c8dc9697421430e1'
FIELDS=frozenset(('audio_segments','tokens','context','last_attend_frame','detected_language',
 'initial_tokens','initial_token_length','sot_index','decoder_type','contract','frontier','transcript'))
class AuditError(ValueError):pass
def need(x,message):
    if not x:raise AuditError(message)
def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def fingerprint(value):return hashlib.sha256(encoded(value)).hexdigest()
def cut_key(state):
    need(isinstance(state,dict)and set(state)==FIELDS,'incomplete/unknown full-cut fields')
    need(type(state['frontier'])is int and state['frontier']>=0,'invalid full-cut frontier')
    return encoded(state)
def same(a,b):return cut_key(a)==cut_key(b)
def order(row,key):
    x=row[key];need(type(x['sequence'])is int and x['sequence']>0,'missing explicit Owner event order')
    need(isinstance(x['observed_perf'],(float,int))and math.isfinite(x['observed_perf']),'invalid Owner event clock')
    return x['sequence'],x['observed_perf']
def execution_state(record,terminal,instant,ready):
    if ready:return 'owner_admitted_ready'
    if record and record.get('native_model_evaluated')is True:
        begin,end=record.get('model_start'),record.get('model_end')
        if isinstance(begin,(float,int))and isinstance(end,(float,int)):
            need(math.isfinite(begin)and math.isfinite(end)and begin<=end,'invalid original neural-stage clocks')
            if begin<=instant<end:return 'native_model_active'
            if instant<begin:return 'before_observed_neural_stage'
            return 'after_observed_neural_stage_owner_unready'
    if record and record.get('native_model_evaluated')is False:return 'original_buffer_only_or_no_native_evaluation'
    return 'neural_clock_unknown_owner_inflight'

def classify_owner(*,jobs,installs,receipts,workers,audits,facts,initials,source_frames,audio_float32_hash,policy_hints=()):
    """Classify every dispatch, not only promotions or sampled decisions.

    Canonical witnesses enter only at actual install orders. A physically
    completed buffered result remains logically owned. Same-frontier eventual
    equality after logical retirement is reported but never survivor benefit.
    """
    by={j['job_id']:j for j in jobs};need(len(by)==len(jobs),'duplicate physical job identity')
    full={};early={};terminal={}
    for row in workers:
        event=row.get('event',{});kind=event.get('kind');jid=event.get('job_id')
        if kind not in('asr_early','completed','abandoned'):continue
        need(jid in by,'worker result lacks original dispatch')
        job=by[jid]
        need(event['source_id']==job['source_id']and event['worker']==job['worker']and
             event['worker_incarnation']==row['physical_incarnation']==job['worker_incarnation']and
             row['physical_slot']==job['worker']and event['dispatch_epoch']==job['dispatch_epoch'],'worker/source/incarnation changed')
        start=event['start_state']if kind=='asr_early'else event['start']
        need(same(start,job['start']),'worker result changed complete frozen start')
        target=early if kind=='asr_early'else terminal
        if jid in target:
            need(encoded(target[jid]['event'])==encoded(event),'contradictory duplicate physical receipt')
            continue
        target[jid]=row
        if kind=='asr_early':
            p=event['projection'];need(p['kind']=='typed_ASR_stage_identity_feedback_projection'and
                p['learned_C_executed']is False and p['original_full_infer_completed']is False,'forecast masquerades as original result')
            need(event['end_frontier']==job['end']==p['end']['frontier']and fingerprint(p['end'])==p['end_state_sha'],'forecast target/state differs')
        if kind=='completed':
            r=event['record'];need(r['role']=='authority'and r['candidate_handoff']is False and
                r['start_state']==fingerprint(job['start'])and r['end_state']==fingerprint(event['end'])and
                event['end']['frontier']==job['end'],'full original result binding failed')
            full[jid]=row
    receipt_by={r['job_id']:r for r in receipts};need(len(receipt_by)==len(receipts),'duplicate validated receipt event')
    fact_by={f['sequence']:f for f in facts};need(len(fact_by)==len(facts),'duplicate durable journal sequence')
    selected={};actual={sid:{}for sid in initials};roots=dict(initials)
    events=[]
    for job in jobs:
        seq,when=order(job,'owner_dispatch_order');events.append((seq,'dispatch',job))
        deps=job['frozen_dependencies'];need(deps and same(deps[-1],job['start'])and
            fingerprint(deps[0])==job['birth_canonical_sha'],'frozen ancestry/root/start changed')
        need(all(a['frontier']<b['frontier']for a,b in zip(deps,deps[1:])),'nonadvancing frozen ancestry')
        need(all(d['contract']==job['start']['contract']for d in deps),'frozen ancestor contract changed')
        key=json.loads(job['key']);sid=job['source_id'];F=job['start']['frontier']
        need(key['complete_start_cut']==job['start']and key['source_sha256']==job['start']['contract']['source_sha']and
            key['target_frontier']==job['end']==min(source_frames[sid],F+8000)and
            key['is_last']==(job['end']==source_frames[sid])and key['runtime_identity']['source_commit']==NN,'complete input key/target/EOS/contract differs')
        need(key['added_audio_float32_sha256']==audio_float32_hash(sid,F,job['end']),'frozen added-audio bytes differ')
    for r in receipts:
        need(r['job_id']in full,'validated full receipt lacks actual physical complete result')
        seq,when=order(r,'complete_receipt_order');events.append((seq,'receipt',r))
    for r in installs:
        need(r['job_id']in by and r['job_id']not in selected,'unknown/duplicate selected original job')
        seq,when=order(r,'canonical_install_order');events.append((seq,'install',r));selected[r['job_id']]=r
        fact=fact_by[r['receipt']['sequence']];body=fact['body'];j=by[r['job_id']]
        need(body['job']['job_id']==r['job_id']and body['source_id']==j['source_id']and
            same(body['parent_state'],j['start'])and body['parent_state_sha256']==fingerprint(j['start'])and
            body['next_state_sha256']==fingerprint(body['next_state'])and
            r['parent_state_sha']==fingerprint(body['parent_state'])and r['next_state_sha']==fingerprint(body['next_state']),
            'actual installation/durable original-parent binding differs')
        need(r['job_id']in full and same(full[r['job_id']]['event']['end'],body['next_state']),
             'selected result is not original same-job full result')
    need(len({x[0]for x in events})==len(events),'ambiguous Owner execution sequence')
    if events:need(sorted(x[0]for x in events)==list(range(1,max(x[0]for x in events)+1)),'missing recorded Owner execution order')
    # Every adjacent frozen dependency must have a same-source, same-full-cut
    # physical forecast/original-result witness received before this dispatch.
    edges=[]
    for jid,row in early.items():
        event=row['event'];available=row.get('owner_dequeued_perf')
        if available is not None:edges.append((by[jid]['source_id'],by[jid]['start'],event['projection']['end'],available,jid,'typed_forecast'))
    for jid,row in full.items():
        rr=receipt_by.get(jid)
        if rr and rr['outcome_kind']in('canonical','buffered_full'):
            edges.append((by[jid]['source_id'],by[jid]['start'],row['event']['end'],order(rr,'complete_receipt_order')[1],jid,'owned_original_full_result'))
    for job in jobs:
        when=order(job,'owner_dispatch_order')[1]
        for a,b in zip(job['frozen_dependencies'],job['frozen_dependencies'][1:]):
            need(any(sid==job['source_id']and t<when and same(a,start)and same(b,end)
                 for sid,start,end,t,jid,kind in edges),'frozen dependency edge lacks prior physical original/forecast witness')
    # Bind dispatch birth roots to actual earlier installs, not to eventual references.
    for seq,kind,payload in sorted(events):
        sid=payload['source_id']
        if kind=='dispatch':
            need(same(roots[sid],payload['frozen_dependencies'][0]),'dispatch ancestry is not actual current root')
            need(payload['started_on_canonical']==same(roots[sid],payload['start']),'started-on-canonical flag differs from actual full cut')
        elif kind=='install':
            b=fact_by[payload['receipt']['sequence']]['body']
            need(same(roots[sid],b['parent_state']),'selected installed prefix has a gap')
            roots[sid]=b['next_state'];F=roots[sid]['frontier']
            need(F not in actual[sid],'same-session actual frontier selected twice')
            actual[sid][F]=dict(state=roots[sid],row=payload,sequence=seq,perf=order(payload,'canonical_install_order')[1])
    # Non-selected logical retirement does not erase a surviving ready result on worker death.
    retired={}
    for row in audits:
        kind=row['kind'];b=row.get('body',{});items=[]
        if kind in('discarded_full','abandoned_full'):items=[(b['job']['job_id'],kind)]
        elif kind=='worker_lost':items=[(jid,'worker_lifecycle_terminated')for jid in b['retired_live_jobs']]
        elif kind=='inbound_disposition'and b.get('outcome',{}).get('kind')=='fenced_terminal':items=[(b['outcome']['job']['job_id'],'fenced_terminal')]
        for jid,reason in items:
            need(jid in by,'retirement lacks original job')
            value=dict(perf=row['observed'],reason=reason)
            need(jid not in retired or retired[jid]==value,'duplicate logical retirement')
            retired[jid]=value
    need(not(set(selected)&set(retired)),'same original job both logically retired and selected')
    policy_fences={}
    for hint in policy_hints:
        proof=hint.get('proof',{});kind=proof.get('kind')
        if kind not in('inflight_at_install_policy_fence','birth_root_policy_fence','dependency_version_policy_fence'):continue
        jid=hint['job_id'];need(jid in by and proof['job_id']==jid,'policy fence lacks original job')
        exact=proof.get('fence_canonical_install_order')
        boundary=order({'order':exact},'order')if exact is not None else(None,None)
        if exact is not None:
            install=next((r for r in installs if order(r,'canonical_install_order')[0]==boundary[0]),None)
            need(install is not None and order(install,'canonical_install_order')[1]==boundary[1]and
                 install['source_id']==by[jid]['source_id'],'policy fence not bound to actual same-source install')
            if 'fence_canonical_sha'in proof:need(proof['fence_canonical_sha']==install['next_state_sha'],'policy fence changed actual selected cut')
        if 'source_id'in proof:need(proof['source_id']==by[jid]['source_id'],'policy fence changed original source')
        if 'dispatch_epoch'in proof:need(proof['dispatch_epoch']==by[jid]['dispatch_epoch'],'policy fence changed session epoch')
        value=dict(kind=kind,boundary_order=boundary[0],boundary_perf=boundary[1],
            hint_observed_perf=hint['observed'],exact_fence_boundary=exact is not None)
        old=policy_fences.get(jid)
        if old is None or value['hint_observed_perf']<old['hint_observed_perf']:policy_fences[jid]=value
    def policy_allowed(jid,witness):
        if witness is None:return None
        fence=policy_fences.get(jid)
        if fence is None:return True
        if fence['boundary_order'] is not None:return fence['boundary_order']>witness['sequence']
        # An emitted hint upper-bounds onset; an earlier event is unknown, not
        # evidence that a permanent policy fence had not already been created.
        return False if fence['hint_observed_perf']<=witness['perf']else None
    rows=[];counts=Counter()
    for jid,job in by.items():
        sid=job['source_id'];F=job['start']['frontier'];dseq,dtime=order(job,'owner_dispatch_order')
        self_witness=actual[sid].get(F)
        self_status=('actual_installed_same_F_matches'if same(self_witness['state'],job['start'])else
            'actual_installed_same_F_refutes')if self_witness else'own_F_not_installed_in_this_owner_namespace'
        confirm=self_witness if self_status=='actual_installed_same_F_matches'and self_witness['sequence']>dseq else None
        if self_witness and self_witness['sequence']<dseq:
            need(self_status=='actual_installed_same_F_matches','job started after its own input was already actually refuted')
        mismatches=[]
        for dep in job['frozen_dependencies']:
            if dep['frontier']>=F:continue
            witness=actual[sid].get(dep['frontier'])
            if witness and not same(dep,witness['state']):
                need(witness['sequence']>dseq,'frozen ancestor was already actually refuted before dispatch')
                mismatches.append(dict(frontier=dep['frontier'],expected_sha256=fingerprint(dep),actual_sha256=fingerprint(witness['state']),
                    sequence=witness['sequence'],perf=witness['perf'],actual_job_id=witness['row']['job_id'],
                    journal_sequence=witness['row']['receipt']['sequence']))
        mismatches.sort(key=lambda x:x['sequence']);first=mismatches[0]if mismatches else None
        selected_row=selected.get(jid);sseq,sperf=order(selected_row,'canonical_install_order')if selected_row else(None,None)
        retirement=retired.get(jid);logical_alive=False;ambiguous=False
        if first:
            ambiguous=bool(retirement and retirement['perf']==first['perf'])
            logical_alive=(sseq is None or sseq>first['sequence'])and(not retirement or retirement['perf']>first['perf'])and not ambiguous
        if first and confirm:need(first['sequence']<confirm['sequence'],'ancestor refutation did not precede own-input confirmation')
        alive_at_confirm=bool(confirm and(not retirement or retirement['perf']>confirm['perf'])and(sseq is None or sseq>=confirm['sequence']))
        record_survivor=bool(first and logical_alive and confirm and alive_at_confirm)
        allowed_at_refutation=policy_allowed(jid,first);allowed_at_confirmation=policy_allowed(jid,confirm)
        survivor=bool(record_survivor and allowed_at_refutation is True and allowed_at_confirmation is True)
        selected_survivor=bool(survivor and selected_row and sseq>confirm['sequence'])
        fence=policy_fences.get(jid)
        need(not(selected_row and fence and fence['boundary_order']is not None and fence['boundary_order']<=sseq),
             'permanently policy-fenced original job was selected')
        rec=full.get(jid,{}).get('event',{}).get('record')
        rr=receipt_by.get(jid)
        def phase(witness):
            if witness is None:return None
            ready=bool(rr and rr['outcome_kind']=='buffered_full'and order(rr,'complete_receipt_order')[0]<witness['sequence'])
            return execution_state(rec,terminal.get(jid,{}).get('event'),witness['perf'],ready)
        forecast=early.get(jid,{}).get('event',{}).get('projection',{}).get('end')
        changed=(not same(forecast,full[jid]['event']['end']))if forecast is not None and jid in full else None
        input_confirmed=bool((self_witness and self_status=='actual_installed_same_F_matches')or job['started_on_canonical'])
        row=dict(job_id=jid,source_id=sid,worker=job['worker'],worker_incarnation=job['worker_incarnation'],
            dispatch_order=dseq,dispatch_perf=dtime,start_frontier=F,target=job['end'],start_sha256=fingerprint(job['start']),
            frozen_ancestor_count=max(0,len(job['frozen_dependencies'])-1),ancestor_refutations=mismatches,
            actual_ancestor_refuted=bool(first),registered_job_or_ready_record_at_first_refutation=logical_alive,
            policy_selection_allowed_at_first_refutation=allowed_at_refutation,
            policy_selection_allowed_at_own_confirmation=allowed_at_confirmation,
            actual_policy_fence=fence,record_survives_through_own_confirmation=record_survivor,
            ambiguous_equal_clock_retirement=ambiguous,own_input_actual_status=self_status,
            own_input_later_confirm_order=confirm['sequence']if confirm else None,
            own_input_later_confirm_perf=confirm['perf']if confirm else None,
            original_job_owned_through_confirmation=survivor,
            actual_same_original_job_selected_after_reconfirmation=selected_survivor,
            first_refutation_execution_phase=phase(first),own_confirmation_execution_phase=phase(confirm),
            selected_order=sseq,logical_retirement=retirement,
            own_input_confirmed=input_confirmed,own_forecast_changed=changed,
            own_input_confirmed_and_forecast_changed=bool(input_confirmed and changed),
            original_full_result_present=jid in full,original_result_selected=selected_row is not None,
            birth_root_difference_is_not_ancestor_refutation=True,
            worker_record_native_model_evaluated=rec.get('native_model_evaluated')if rec else None)
        rows.append(row);counts['all_dispatched_jobs']+=1
        counts['actual_ancestor_refuted_jobs']+=bool(first)
        counts['ancestor_refuted_while_registered_job_or_ready_record_present']+=bool(first and logical_alive)
        counts['ancestor_refuted_while_policy_selectable_jobs']+=bool(first and logical_alive and allowed_at_refutation is True)
        counts['ancestor_refuted_record_present_but_policy_fenced_jobs']+=bool(first and logical_alive and allowed_at_refutation is False)
        counts['ancestor_refuted_policy_admission_unknown_jobs']+=bool(first and allowed_at_refutation is None)
        counts['ancestor_refuted_then_own_input_matches_jobs_including_retired']+=bool(first and confirm)
        counts['ancestor_refuted_original_job_survives_to_input_confirmation']+=survivor
        counts['ancestor_refuted_record_survives_to_confirmation_policy_unchecked']+=record_survivor
        counts['ancestor_refuted_original_job_later_selected_installed']+=selected_survivor
        counts['ancestor_refuted_own_input_actually_refuted_jobs']+=bool(first and self_status=='actual_installed_same_F_refutes')
        counts['ancestor_refuted_own_F_not_observed_jobs']+=bool(first and self_witness is None)
        counts['ancestor_refuted_eventual_match_but_original_job_not_surviving']+=bool(first and confirm and not survivor)
        counts['own_input_confirmed_and_own_forecast_changed_jobs']+=row['own_input_confirmed_and_forecast_changed']
        counts['survivor_and_own_forecast_changed_jobs']+=bool(survivor and changed)
        counts['ambiguous_retirement_refutation_clocks']+=ambiguous
        if survivor:counts['survivor_refutation_phase_'+row['first_refutation_execution_phase']]+=1
    need(counts['all_dispatched_jobs']==len(jobs),'dispatch denominator changed')
    return dict(counts=dict(counts),jobs=rows,
        axes='Ancestor refutation/later actual own-input confirmation and own-result forecast change are independent, overlapping axes',
        scope='Actual recorded schedule and actual same-job survival/use only; no alternate-schedule credit or saved-GPU-time claim')

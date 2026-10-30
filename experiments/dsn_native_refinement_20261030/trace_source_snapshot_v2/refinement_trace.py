"""Independent structural refinement check of actual native runtime journals.

Reads complete cuts and actual original full-call receipts. It does not invoke,
replay, emulate or attest neural arithmetic. Execution-integrity is an explicit
premise. Predicted whole hypotheses never become Canonical just by being shown.
"""
import hashlib,json,math,pathlib,re,struct
FIELDS=frozenset(('audio_segments','tokens','context','last_attend_frame','detected_language',
'initial_tokens','initial_token_length','sot_index','decoder_type','contract','frontier','transcript'))
MAGIC=b'RVN1';MAX_FRAME=16*1024*1024
class TraceViolation(AssertionError):pass
def need(ok,why):
    if not ok:raise TraceViolation(why)
def wire(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(wire(x)).hexdigest()
def same(a,b):return wire(a)==wire(b)
def cut(c):
    need(isinstance(c,dict) and set(c)==FIELDS,'incomplete_or_projected_complete_cut')
    need(type(c['frontier']) is int and c['frontier']>=0,'invalid_state_frontier')
    need(isinstance(c['transcript'],str),'unbound_display_text')
    wire(c);return c
def namespace(jobid):
    m=re.fullmatch(r'e(0|[1-9][0-9]*)-j([0-9]{9})',jobid or '')
    need(m is not None and int(m[2])>0,'invalid_owned_job_namespace')
    return int(m[1]),int(m[2])
def lines(path):
    with pathlib.Path(path).open(encoding='utf8') as f:
        for i,line in enumerate(f,1):
            if line.strip():
                try:yield json.loads(line)
                except Exception as e:raise TraceViolation(f'partial_or_invalid_complete_JSONL:{path}:{i}') from e

def read_frames(path,allow_incomplete_tail=False):
    """Independent reader; never imports runtime scan() and never repairs data."""
    frames=[];previous='0'*64;sequence=0;valid=0;total=pathlib.Path(path).stat().st_size
    with pathlib.Path(path).open('rb') as f:
        while True:
            offset=f.tell();header=f.read(8)
            if not header:break
            if len(header)<8:
                need(allow_incomplete_tail,'incomplete_tail_header');break
            need(header[:4]==MAGIC,'complete_frame_magic_changed')
            size=struct.unpack('>I',header[4:])[0];need(size<=MAX_FRAME,'complete_frame_size_corruption')
            payload=f.read(size);checksum=f.read(32)
            if len(payload)!=size or len(checksum)!=32:
                need(allow_incomplete_tail,'incomplete_tail_body');break
            need(hashlib.sha256(payload).digest()==checksum,'complete_frame_checksum_changed')
            try:obj=json.loads(payload)
            except Exception as e:raise TraceViolation('complete_frame_JSON_corruption') from e
            need(wire(obj)==payload,'noncanonical_frame_encoding')
            need(obj['sequence']==sequence+1 and obj['previous']==previous,'durable_frame_chain_or_identity_changed')
            sequence+=1;previous=checksum.hex();valid=f.tell()
            frames.append((obj,dict(sequence=sequence,record_sha256=previous,offset=offset,end_offset=valid)))
    need(bool(frames) and frames[0][0]['kind']=='genesis','missing_original_genesis')
    return frames,dict(valid_bytes=valid,total_bytes=total,ignored_incomplete_tail_bytes=total-valid)

def wrapped_publication(row):
    if 'bound_owner_epoch' in row:
        if 'owner_epoch' in row:need(row['owner_epoch']==row['bound_owner_epoch'],'publication_owner_binding_conflicts')
        return row['bound_owner_epoch'],row['event']
    if row.get('kind')=='publication':
        return row['owner_epoch'],row['event']
    # Explicit normalized fixture/adapter shape, not a projection of state.
    need(set(('owner_epoch','event'))<=set(row),'publication_physical_owner_binding_missing')
    return row['owner_epoch'],row['event']

def audit(*,frames,dispatch_rows,completion_rows,publication_rows,consumer_rows,expected_runtime_commit=None,
          expected_final_frontiers=None):
    """Verify every durable fact and every actual Consumer application."""
    genesis,first_receipt=frames[0];initials=genesis['body']['initials'];metadata=genesis['body']['metadata']
    roots={sid:cut(c) for sid,c in initials.items()}
    need(first_receipt['sequence']==1,'genesis_sequence')
    if expected_runtime_commit is not None:
        need(metadata['actual_source_commit']==expected_runtime_commit,'actual_runtime_source_commit_changed')
    dispatch={};highwater={};all_complete={};owned_complete={};early={};duplicates=0;fenced_observations=0
    declared_frames=expected_final_frontiers or {s['source_id']:s['frames'] for s in metadata.get('sources',[])}
    for row in dispatch_rows:
        job=row['job'];jid=job['job_id'];owner,serial=namespace(jid)
        need(owner==row['owner_epoch'],'dispatch_owner_namespace_conflated_with_session_epoch')
        need(jid not in dispatch,'owned_job_identity_reissued')
        need(serial>highwater.get(owner,0),'owner_issue_serial_reused_or_regressed');highwater[owner]=serial
        start=cut(job['start']);need(job['end']>start['frontier'],'nonadvancing_full_call')
        if declared_frames:
            need(job['source_id'] in declared_frames and job['end']==min(declared_frames[job['source_id']],start['frontier']+8000),
                 'full_call_changed_original_500ms_or_EOS_target')
        need(job['worker']==row['physical_slot'] and job['worker_incarnation']==row['physical_incarnation'],'dispatch_physical_owner_mismatch')
        need(type(job['dispatch_epoch']) is int,'missing_session_epoch')
        need(isinstance(job['birth_canonical_sha'],str),'missing_immutable_birth')
        dispatch[jid]=row
    for row in completion_rows:
        e=row['event'];kind=e.get('kind')
        if kind not in ('asr_early','completed','abandoned'):continue
        jid=e['job_id'];job_owner,_=namespace(jid)
        # A replayed old-namespace message is not a newly owned full result.
        observed_owner=row.get('owner_epoch',job_owner)
        if observed_owner!=job_owner:
            fenced_observations+=1;continue
        need(jid in dispatch,'neural_receipt_has_no_actual_dispatch')
        d=dispatch[jid];j=d['job']
        need(e['worker']==row['physical_slot']==j['worker'] and row['physical_incarnation']==j['worker_incarnation'],
             'completion_changed_physical_channel_or_incarnation')
        need(e.get('worker_incarnation',row['physical_incarnation'])==row['physical_incarnation'],'message_incarnation_forged')
        need(e['source_id']==j['source_id'] and e['dispatch_epoch']==j['dispatch_epoch'],'completion_session_or_source_changed')
        if kind=='completed':
            start,end=cut(e['start']),cut(e['end']);r=e['record']
            need(same(start,j['start']) and end['frontier']==j['end'],'full_receipt_changed_frozen_input_or_target')
            need(start['contract']==end['contract'],'full_receipt_changed_contract')
            need(r['start_state']==digest(start) and r['end_state']==digest(end),'full_receipt_hash_binding_changed')
            need(r['role']=='authority' and r['candidate_handoff'] is False,'receipt_not_original_full_C_U')
            need(isinstance(r['token_ids'],list) and 'selected_correction' in r,'missing_original_C_and_IDs')
            need(math.isfinite(r['model_start']) and math.isfinite(r['model_end']) and r['model_end']>=r['model_start'],
                 'no_actual_complete_model_interval')
            if jid in all_complete:
                need(same(all_complete[jid],e),'same_full_receipt_identity_changed_contents');duplicates+=1
            else:all_complete[jid]=e
            owned_complete[jid]=e
        elif kind=='asr_early':
            start=cut(e['start_state']);p=e['projection'];end=cut(p['end'])
            need(same(start,j['start']) and e['start_state_sha']==digest(start) and e['end_frontier']==j['end'],
                 'ASR_receipt_changed_frozen_input')
            need(p['kind']=='typed_ASR_stage_identity_feedback_projection' and p['learned_C_executed'] is False
                 and p['original_full_infer_completed'] is False,'projection_forged_original_C_U_completion')
            need(end['frontier']==j['end'] and digest(end)==p['end_state_sha'] and start['contract']==end['contract'],
                 'ASR_projection_changed_complete_cut_or_contract')
            if jid in early:need(same(early[jid],e),'same_ASR_identity_changed_contents')
            early[jid]=e
        else:
            need(e.get('C_U_completed') is False and e.get('feedback_cut_emitted') is False,'cancelled_prefix_claimed_complete_fact')
    facts={};transition_ids=set();used_jobs=set();fact_roots=dict(roots);processed={sid:0 for sid in roots};after_processed={}
    for obj,receipt in frames[1:]:
        need(obj['kind']=='canonical','unknown_privileged_durable_frame')
        b=obj['body'];sid=b['source_id'];j=b['job'];jid=j['job_id'];owner,_=namespace(jid)
        need(sid in fact_roots and jid in dispatch and jid in owned_complete,'fact_lacks_owned_original_full_call')
        d=dispatch[jid]['job'];e=owned_complete[jid];r=e['record'];parent,end=cut(b['parent_state']),cut(b['next_state'])
        need(owner==b['owner_epoch'] and j['dispatch_epoch']==b['session_epoch'],'Owner_namespace_or_session_epoch_reassigned')
        for field in ('job_id','worker','worker_incarnation','source_id','start','end','birth_canonical_sha','dispatch_epoch'):
            need(same(j[field],d[field]),'fact_relabelled_dispatch_'+field)
        if 'key' in d:need(j.get('key')==d['key'],'fact_changed_remaining_frozen_inputs')
        need(same(parent,fact_roots[sid]) and same(parent,e['start']) and same(end,e['end']),'new_fact_not_original_transition_from_previous_actual_cut')
        need(same(b['record'],r),'fact_changed_original_selected_C_or_IDs')
        need(end['contract']==parent['contract'] and end['frontier']>parent['frontier'],'fact_order_or_contract')
        need(jid not in used_jobs and b['transition_id'] not in transition_ids,'original_transition_was_installed_twice')
        transition_ids.add(b['transition_id']);used_jobs.add(jid);fact_roots[sid]=end
        if r['native_model_evaluated']:processed[sid]=end['frontier']
        after_processed[receipt['sequence']]=dict(processed)
        facts[receipt['sequence']]=(b,receipt)
    pubs={};pub_serials={}
    for row in publication_rows:
        owner,e=wrapped_publication(row);key=(owner,e['publication_id'])
        need(type(e['publication_id']) is int and e['publication_id']>0,'invalid_publication_identity')
        if key in pubs:need(same(pubs[key],e),'same_publication_identity_changed_contents')
        else:pubs[key]=e
        pub_serials.setdefault(owner,set()).add(e['publication_id'])
    for owner,serials in pub_serials.items():
        need(serials==set(range(1,max(serials)+1)),'publication_journal_dropped_FIFO_prefix')
    current={sid:dict(canonical=c,steps=[],processed=0) for sid,c in roots.items()}
    durable_highwater=1;last_owner=-1;last_pub={};counts=dict(canonical_applications=0,private_applications=0,recovery_fact_applications=0,
        compatible_ahead_applications=0,compatible_ahead_preserved=0,incompatible_ahead_withdrawals=0)
    chain_links=0;case_rows=[]
    for index,row in enumerate(consumer_rows):
        sid=row['source_id'];s=current[sid];owner=row['owner_epoch']
        need(owner>=last_owner,'actual_Consumer_owner_namespace_regressed');last_owner=owner
        before_tip=s['steps'][-1]['end'] if s['steps'] else s['canonical']
        if row.get('recovery_replay',False):
            need(row['kind']=='canonical','replay_promoted_private_prediction')
            seq=row['journal_sequence'];need(seq in facts,'replay_has_no_durable_original_fact');b,receipt=facts[seq]
            need(row['transition_id']==b['transition_id'] and row['original_fact_owner_epoch']==b['owner_epoch'],
                 'replay_relabelled_original_fact_identity')
            event=None;counts['recovery_fact_applications']+=1
        else:
            key=(owner,row['publication_id']);need(key in pubs,'Consumer_application_lacks_actual_publication')
            need(row['publication_id']>last_pub.get(owner,0),'applied_duplicate_or_regressing_publication')
            last_pub[owner]=row['publication_id'];event=pubs[key]
            need(event['kind']==row['kind'] and event['source_id']==sid,'publication_application_role_changed')
            if row['kind']=='canonical':
                seq=event['durable_receipt']['sequence'];need(seq in facts,'Canonical_publication_has_no_fact')
                b,receipt=facts[seq]
                for k in ('sequence','record_sha256','offset','end_offset'):
                    need(event['durable_receipt'][k]==receipt[k],'publication_changed_durable_receipt')
                need(b['owner_epoch']==owner and same(event['state'],b['next_state']),'new_publication_adopted_old_or_changed_fact')
                need(row['transition_id']==b['transition_id'] and row['journal_sequence']==seq,'actual_application_fact_identity_changed')
            else:seq=None;b=None
        if row['kind']=='canonical':
            need(seq==durable_highwater+1,'actual_Consumer_fact_prefix_gap_or_duplicate')
            need(same(b['parent_state'],s['canonical']),'actual_Consumer_original_parent_changed')
            new=b['next_state'];boundary=next((i for i,x in enumerate(s['steps']) if x['end']['frontier']==new['frontier']),None)
            compatible=boundary is not None and same(s['steps'][boundary]['end'],new)
            ahead=before_tip['frontier']>new['frontier']
            s['steps']=s['steps'][boundary+1:] if compatible else []
            s['canonical']=new;s['processed']=after_processed[seq][sid];durable_highwater=seq
            counts['canonical_applications']+=1
            if compatible and ahead:
                counts['compatible_ahead_applications']+=1;counts['compatible_ahead_preserved']+=1
                case_rows.append(dict(row_index=index,source_id=sid,kind='compatible_actual_whole_view_preserved',
                    visible_before=before_tip['frontier'],certified_processing_after=new['frontier']))
            elif ahead:
                counts['incompatible_ahead_withdrawals']+=1
                case_rows.append(dict(row_index=index,source_id=sid,kind='necessary_complete_input_incompatibility',
                    visible_before=before_tip['frontier'],certified_processing_after=new['frontier']))
        elif row['kind']=='private':
            need(event is not None and event['canonical_sha']==digest(s['canonical']),'applied_private_view_wrong_actual_root')
            previous=s['canonical'];steps=[]
            for step in event['steps']:
                start,end=cut(step['start']),cut(step['end']);jid=step['job_id']
                need(same(start,previous) and end['frontier']>start['frontier'],'gapped_actual_whole_view_path')
                need(jid in dispatch and same(start,dispatch[jid]['job']['start']),'Private_node_frozen_input_not_dispatched')
                if step['kind']=='typed_ASR_projection':
                    need(jid in early and same(end,early[jid]['projection']['end']),'Private_projection_not_actual_ASR_receipt')
                    need(step.get('actual_full_C_U_completed') is not True,'typed_prediction_claimed_C_U')
                elif step['kind']=='actual_original_full_conditional_closed_node':
                    need(jid in owned_complete and same(end,owned_complete[jid]['end']),'Private_full_node_lacks_original_C_U')
                    need(step.get('actual_full_C_U_completed') is True,'full_node_completion_kind_changed')
                else:raise TraceViolation('undeclared_private_node_kind')
                need(start['contract']==end['contract'],'Private_path_contract_changed')
                previous=end;steps.append(step);chain_links+=1
            current_tip=s['steps'][-1]['end'] if s['steps'] else s['canonical']
            if previous['frontier']>=current_tip['frontier']:s['steps']=steps
            counts['private_applications']+=1
        else:raise TraceViolation('unknown_actual_Consumer_application')
        tip=s['steps'][-1]['end'] if s['steps'] else s['canonical']
        expected=dict(canonical_sha=digest(s['canonical']),certified_frontier=s['processed'],
            visible_frontier=tip['frontier'] if tip['transcript'] else 0,text=tip['transcript'],
            private_job=s['steps'][-1]['job_id'] if s['steps'] else None)
        for key,value in expected.items():need(row[key]==value,'actual_Consumer_snapshot_or_certification_changed:'+key)
    need(durable_highwater==max([1,*facts]),'terminal_actual_Consumer_did_not_apply_all_durable_facts')
    if expected_final_frontiers is not None:
        need(set(expected_final_frontiers)==set(fact_roots),'source_obligation_set_changed')
        for sid,target in expected_final_frontiers.items():
            need(fact_roots[sid]['frontier']==target,'accepted_input_not_Canonical_processed_to_final_boundary')
            need(current[sid]['processed']==target,'accepted_input_not_actually_certified_to_final_boundary')
    return dict(status='PASS_ACTUAL_ORIGINAL_FULLCALL_DURABLE_AND_CONSUMER_REFINEMENT',
        durable_original_transitions=len(facts),unique_original_C_U_jobs_used=len(used_jobs),dispatches=len(dispatch),
        complete_original_receipts=len(owned_complete),duplicate_exact_full_receipts=duplicates,
        observed_old_namespace_full_messages_not_new_authority=fenced_observations,
        actual_Consumer_rows=len(consumer_rows),verified_complete_Private_path_links=chain_links,
        counts=counts,natural_cases=case_rows,final_Canonical_frontiers={k:v['frontier'] for k,v in fact_roots.items()},
        premise='host/source execution integrity and complete adapter state; this is structural trace refinement, not GPU arithmetic attestation or a fixed replay-equality theorem',
        new_model_calls=0,scope='every supplied complete durable frame, actual full-call receipt and actual Consumer row; not natural prevalence or an unbounded proof')

def check_original_ingress(*,origin,sources,ingress_rows):
    """Supervisor owns arrival clocks; recovery must not silently rebase them."""
    need(math.isfinite(origin) and origin>0,'missing_original_service_ORIGIN')
    source_map={s['source_id']:s for s in sources};accepted={sid:0 for sid in source_map}
    duplicates=0
    for row in ingress_rows:
        sid=row['source_id'];need(sid in source_map,'unknown_ingress_source')
        if 'accepted' in row:
            F=row['accepted']
            if 'frontier' in row:need(row['frontier']==F,'conflicting_accepted_input_frontier_fields')
        else:
            need(row.get('kind')=='accepted_input' and 'frontier' in row,'undeclared_ingress_schema')
            F=row['frontier']
        need(type(F) is int and accepted[sid]<=F<=source_map[sid]['frames'],'accepted_frontier_regressed_or_escaped')
        need(row['audio_sha256']==source_map[sid]['audio_sha256'],'accepted_audio_identity_changed')
        need(abs(row['original_offer']-(origin+F/16000))<1e-7,'original_input_clock_rebased')
        need(row['observed']>=row['original_offer'],'input_accepted_before_original_offer')
        duplicates+=int(F==accepted[sid]);accepted[sid]=F
    need(all(accepted[sid]==s['frames'] for sid,s in source_map.items()),'accepted_input_final_obligation_missing')
    return dict(original_clocks_preserved=True,source_count=len(source_map),accepted_final_frontiers=accepted,
        idempotent_prefix_reacknowledgments=duplicates,offered_boundaries='Original 500ms/EOS clocks reconstructed independently of acknowledgment batching')

def check_dispatch_arrivals(origin,dispatch_rows):
    for row in dispatch_rows:
        j=row['job']
        need(j['dispatched_perf']>=origin+j['end']/16000,'full_call_read_unoffered_future_audio')
    return dict(dispatches_checked=len(dispatch_rows),no_dispatch_before_original_target_offer=True,
        scope='logical frozen target/input arrival binding; not GPU memory-read attestation')

def event_fingerprint(event):
    transport={'received_perf','received_owner_perf','physical_channel_worker','channel_incarnation','sent_perf','wire_complete_perf'}
    return digest({k:v for k,v in event.items() if k not in transport})

def wellformed_progress_phase(event,job):
    """First ASR/full receipt eligibility, separate from original output quality."""
    try:
        if event['worker']!=job['worker'] or event['worker_incarnation']!=job['worker_incarnation']:
            return False
        if event['source_id']!=job['source_id'] or event['dispatch_epoch']!=job['dispatch_epoch']:
            return False
        if event['kind']=='completed':
            return (same(event['start'],job['start']) and event['end']['frontier']==job['end']
                and event['record']['start_state']==digest(job['start'])
                and event['record']['end_state']==digest(event['end'])
                and event['record']['role']=='authority' and event['record']['candidate_handoff'] is False)
        if event['kind']=='asr_early':
            p=event['projection']
            return (same(event['start_state'],job['start']) and event['start_state_sha']==digest(job['start'])
                and event['end_frontier']==job['end'] and p['end']['frontier']==job['end']
                and p['end_state_sha']==digest(p['end'])
                and event.get('producer_role')=='authority' and p['kind']=='typed_ASR_stage_identity_feedback_projection'
                and p['learned_C_executed'] is False and p['original_full_infer_completed'] is False)
    except (KeyError,TypeError,ValueError):return False
    return False

def audit_local_rejections(*,dispatch_rows,owner_event_groups,policy_audit_groups):
    """Do not infer zero false rejection from a final successful task alone."""
    dispatch={r['job']['job_id']:r for r in dispatch_rows};checked=0;insufficient=0;physical_retirements=0;wrong=[]
    for owner,events in owner_event_groups.items():
        local=[e for e in events if e['kind']=='local_message_disposition']
        audits=[e for e in policy_audit_groups.get(owner,[]) if e['kind']=='inbound_disposition']
        need(len(local)==len(audits),'local_rejection_audit_or_Owner_snapshot_omitted')
        for row,entry in zip(local,audits):
            r=row['result'];body=entry['body'];event=body['event'];jid=event.get('job_id')
            for k in ('disposition','reason','job_id','physical_terminal'):
                need(r.get(k)==body.get(k),'rejection_actor_audit_join_changed')
            before,after=row['before'],row['after']
            need(same(before['canon'],after['canon']),'local_reject_changed_Canonical_facts')
            required={'busy','canon','session_epochs','physical_incarnations','inbound_seen'}
            if not required<=set(before) or not required<=set(after):
                insufficient+=1;continue
            need(same(before['session_epochs'],after['session_epochs'])
                and same(before['physical_incarnations'],after['physical_incarnations']),'local_reject_changed_authority_domains')
            if r['physical_terminal']:
                need(r['disposition']=='retire_fenced_terminal' and jid in dispatch,'unvalidated_local_drop_released_physical_owner')
                slot=dispatch[jid]['job']['worker']
                need(before['busy'].get(slot)==jid and after['busy'].get(slot) is None,'fenced_terminal_cleared_another_busy_job')
                expected=cp_dict(before['busy']);expected[slot]=None
                need(same(expected,after['busy']),'fenced_terminal_released_other_slot')
                seen=cp_dict(before['inbound_seen']);seen.pop(jid,None)
                need(same(seen,after['inbound_seen']),'fenced_terminal_changed_other_phase_authority')
                physical_retirements+=1
            else:
                need(same(before['busy'],after['busy']) and same(before['inbound_seen'],after['inbound_seen']),
                    'ordinary_local_reject_released_or_relabelled_owned_work')
            if jid in dispatch:
                job=dispatch[jid]['job'];slot=job['worker'];sid=job['source_id'];namespace_owner,_=namespace(jid)
                prior=before['inbound_seen'].get(jid,{})
                first_phase=event.get('kind') not in prior
                if event.get('kind') in ('completed','abandoned') and any(p in prior for p in ('completed','abandoned')):
                    first_phase=False
                current_owned=(namespace_owner==owner and before['busy'].get(slot)==jid
                    and before['session_epochs'].get(sid)==job['dispatch_epoch']
                    and before['physical_incarnations'].get(slot)==job['worker_incarnation'])
                if current_owned and first_phase and wellformed_progress_phase(event,job):
                    wrong.append(dict(owner_epoch=owner,job_id=jid,phase=event['kind'],reason=r['reason']))
            checked+=1
    need(not wrong,'current_owned_first_wellformed_progress_phase_was_locally_rejected')
    return dict(local_rejections_with_complete_ownership_evidence=checked,
        insufficient_rejection_snapshots=insufficient,validated_old_physical_terminal_retirements=physical_retirements,
        legal_progress_wrong_rejections=0 if not insufficient else None,
        scope='current owned first wellformed ASR/full phase under matching Owner/session/physical domains; duplicates and unowned stale channels are not new progress; missing evidence remains unknown')

def cp_dict(value):
    return json.loads(json.dumps(value,ensure_ascii=False,allow_nan=False))

def audit_worker_replacements(*,owner_event_groups,dispatch_rows):
    registered={};replacements=0;deaths=0
    for owner,events in owner_event_groups.items():
        active={};released={}
        for row in events:
            if row['kind']=='worker_started':
                slot,inc,pid=row['slot'],row['incarnation'],row['pid']
                if slot in active:
                    old=active[slot]
                    need((slot,old['incarnation']) in released and inc==old['incarnation']+1,
                         'worker_incarnation_reused_before_confirmed_physical_exit')
                    need(row['observed']>=released[(slot,old['incarnation'])],
                         'new_worker_started_before_actual_CUDA_release')
                    replacements+=1
                else:need(inc==0,'first_physical_incarnation_not_declared')
                active[slot]=row;registered[(owner,slot,inc)]=row
            elif row['kind']=='worker_death_confirmed':
                p=row['proof'];slot=p['slot'];need(slot in active,'worker_death_has_no_registered_PID')
                old=active[slot]
                need(p['incarnation']==old['incarnation'] and p['pid']==old['pid'] and p['start_ticks']==old['start_ticks'],
                     'worker_exit_proof_changed_physical_identity')
                need(p['confirmed_exit'] is True and p['confirmed_dead'] is True and type(p['exitcode']) is int,
                     'physical_exit_not_confirmed')
                need(p['partial_frame_thread_blocked'] is False,'retired_receiver_still_blocks_Owner')
                release=p['cuda_release']
                need(release['gpu_context_released'] is True and release['old_pid']==old['pid']
                    and release['observed_perf']>=p['confirmed_perf'],'CUDA_owner_reused_before_release')
                released[(slot,p['incarnation'])]=release['observed_perf'];deaths+=1
    for row in dispatch_rows:
        key=(row['owner_epoch'],row['physical_slot'],row['physical_incarnation'])
        need(key in registered,'dispatch_has_no_registered_physical_incarnation')
        if 'pid' in row:need(row['pid']==registered[key]['pid'],'dispatch_PID_not_its_physical_incarnation')
    return dict(registered_physical_incarnations=len(registered),worker_only_confirmed_deaths=deaths,
        observed_safe_worker_replacements=replacements,all_dispatch_physical_origins_bound=True,
        scope='per-Owner worker-only replacements; independent Supervisor whole-group termination receipts are separate evidence')



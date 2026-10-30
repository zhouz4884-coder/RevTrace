"""Synthetic structural controls; no model outputs or serving measurements."""
import copy,tempfile,pathlib,unittest
from refinement_trace import *

def state(F,p=0):
    return dict(audio_segments=[],tokens=[[p]],context=dict(p=p),last_attend_frame=p,
        detected_language='zh',initial_tokens=[[1]],initial_token_length=1,sot_index=0,
        decoder_type='beam',contract=dict(source_sha='a'*64,dtype='float32'),
        frontier=F,transcript='' if F==0 else f'whole@{F}')
def cp(x):return copy.deepcopy(x)

def pack(objs):
    frames=[];previous='0'*64;offset=0;raw=b''
    for index,obj in enumerate(objs,1):
        obj=dict(sequence=index,previous=previous,**obj);payload=wire(obj);checksum=hashlib.sha256(payload).digest()
        data=MAGIC+struct.pack('>I',len(payload))+payload+checksum
        receipt=dict(sequence=index,record_sha256=checksum.hex(),offset=offset,end_offset=offset+len(data))
        frames.append((obj,receipt));offset+=len(data);previous=checksum.hex();raw+=data
    return frames,raw

def bundle():
    c=[state(i*8000) for i in range(3)];dispatch=[];completions=[];objs=[dict(kind='genesis',body=dict(initials={'s':cp(c[0])},metadata=dict(actual_source_commit='b'*40)))]
    jobs=[];early=[]
    for i in (1,2):
        jid=f'e0-j{i:09d}';slot=f'full{i-1}'
        j=dict(job_id=jid,worker=slot,worker_incarnation=0,source_id='s',start=cp(c[i-1]),end=i*8000,birth_canonical_sha=digest(c[0]),dispatch_epoch=0,key=f'frozen-full-input-{i}')
        dispatch.append(dict(owner_epoch=0,physical_slot=slot,physical_incarnation=0,job=cp(j)));jobs.append(j)
        proj=dict(kind='typed_ASR_stage_identity_feedback_projection',learned_C_executed=False,
            original_full_infer_completed=False,end=cp(c[i]),end_state_sha=digest(c[i]),token_ids=[i])
        a=dict(kind='asr_early',worker=slot,worker_incarnation=0,job_id=jid,source_id='s',dispatch_epoch=0,
            start_state=cp(c[i-1]),start_state_sha=digest(c[i-1]),end_frontier=i*8000,projection=proj,producer_role='authority')
        early.append(a);completions.append(dict(owner_epoch=0,physical_slot=slot,physical_incarnation=0,event=cp(a)))
        r=dict(start_state=digest(c[i-1]),end_state=digest(c[i]),role='authority',candidate_handoff=False,
            selected_correction=dict(synthetic_choice=0),token_ids=[i],native_model_evaluated=True,model_start=100+i*.5,model_end=100+i*.5+.1)
        e=dict(kind='completed',worker=slot,worker_incarnation=0,job_id=jid,source_id='s',dispatch_epoch=0,
            start=cp(c[i-1]),end=cp(c[i]),record=cp(r))
        completions.append(dict(owner_epoch=0,physical_slot=slot,physical_incarnation=0,event=cp(e)))
        objs.append(dict(kind='canonical',body=dict(source_id='s',parent_state=cp(c[i-1]),next_state=cp(c[i]),
            record=cp(r),job=cp(j),owner_epoch=0,session_epoch=0,transition_id=f'original-transition-{i}')))
    frames,raw=pack(objs)
    steps=[dict(job_id=j['job_id'],start=cp(c[i]),end=cp(c[i+1]),kind='typed_ASR_projection',
        actual_identity_full_step_completed=False,actual_full_C_U_completed=False) for i,j in enumerate(jobs)]
    e=[
        dict(kind='private',source_id='s',canonical_sha=digest(c[0]),steps=cp(steps[:1])),
        dict(kind='private',source_id='s',canonical_sha=digest(c[0]),steps=cp(steps)),
        dict(kind='canonical',source_id='s',state=cp(c[1]),durable_receipt=cp(frames[1][1])),
        dict(kind='private',source_id='s',canonical_sha=digest(c[1]),steps=cp(steps[1:])),
        dict(kind='canonical',source_id='s',state=cp(c[2]),durable_receipt=cp(frames[2][1])),
        dict(kind='private',source_id='s',canonical_sha=digest(c[2]),steps=[])]
    pubs=[];rows=[]
    for i,event in enumerate(e,1):
        event['publication_id']=i;pubs.append(dict(kind='publication',owner_epoch=0,event=cp(event)))
        canonical=0 if i<3 else (1 if i<5 else 2);visible=1 if i==1 else 2
        job='e0-j000000001' if i==1 else ('e0-j000000002' if i<5 else None)
        row=dict(kind=event['kind'],source_id='s',observed=102+i*.1,owner_epoch=0,publication_id=i,
            canonical_sha=digest(c[canonical]),certified_frontier=canonical*8000,
            visible_frontier=visible*8000,text=c[visible]['transcript'],private_job=job,recovery_replay=False)
        if event['kind']=='canonical':
            seq=event['durable_receipt']['sequence'];row.update(transition_id=frames[seq-1][0]['body']['transition_id'],journal_sequence=seq)
        rows.append(row)
    return dict(frames=frames,dispatch_rows=dispatch,completion_rows=completions,publication_rows=pubs,
        consumer_rows=rows,expected_runtime_commit='b'*40,expected_final_frontiers={'s':16000}),raw

class ActualTraceControls(unittest.TestCase):
    def test_valid_complete_original_task_and_whole_ahead_application(self):
        data,_=bundle();r=audit(**data)
        self.assertEqual(r['durable_original_transitions'],2)
        self.assertEqual(r['counts']['compatible_ahead_preserved'],1)
        self.assertEqual(r['actual_Consumer_rows'],6)

    def test_independent_binary_reader_checks_frame_bytes(self):
        data,raw=bundle()
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'facts.wal';p.write_bytes(raw)
            f,meta=read_frames(p);self.assertEqual(f,data['frames']);self.assertEqual(meta['ignored_incomplete_tail_bytes'],0)

    def test_torn_tail_never_becomes_a_fact_and_no_repair_is_performed(self):
        _,raw=bundle()
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'facts.wal';torn=raw+b'RVN1\x00';p.write_bytes(torn)
            with self.assertRaisesRegex(TraceViolation,'incomplete_tail'):read_frames(p)
            f,meta=read_frames(p,True);self.assertEqual(len(f),3)
            self.assertEqual(meta['ignored_incomplete_tail_bytes'],5);self.assertEqual(p.read_bytes(),torn)

    def test_complete_frame_corruption_is_not_treated_as_torn_tail(self):
        _,raw=bundle();bad=bytearray(raw);bad[-1]^=1
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'facts.wal';p.write_bytes(bad)
            with self.assertRaisesRegex(TraceViolation,'checksum'):read_frames(p,True)

    def test_unknown_complete_cut_field_is_not_silently_projected(self):
        data,_=bundle();data['frames'][1][0]['body']['next_state']['hidden_cache']='different'
        with self.assertRaisesRegex(TraceViolation,'incomplete_or_projected'):audit(**data)

    def test_same_text_hidden_complete_state_does_not_authorize_an_input(self):
        data,_=bundle();data['frames'][2][0]['body']['parent_state']['last_attend_frame']=17
        self.assertEqual(data['frames'][2][0]['body']['parent_state']['transcript'],state(8000)['transcript'])
        with self.assertRaisesRegex(TraceViolation,'previous_actual_cut'):audit(**data)

    def test_selected_C_and_returned_IDs_are_not_ignored(self):
        data,_=bundle();data['frames'][1][0]['body']['record']['token_ids']=[999]
        with self.assertRaisesRegex(TraceViolation,'selected_C_or_IDs'):audit(**data)

    def test_provisional_projection_cannot_masquerade_as_complete_C_U(self):
        data,_=bundle()
        data['completion_rows'][0]['event']['projection']['learned_C_executed']=True
        with self.assertRaisesRegex(TraceViolation,'projection_forged'):audit(**data)

    def test_fact_requires_actual_complete_original_call_not_a_matching_text(self):
        data,_=bundle();data['completion_rows']=[r for r in data['completion_rows'] if r['event']['kind']!='completed']
        with self.assertRaisesRegex(TraceViolation,'lacks_owned'):audit(**data)

    def test_new_owner_cannot_reauthorize_old_job_with_same_session_number(self):
        data,_=bundle();data['frames'][1][0]['body']['owner_epoch']=1
        self.assertEqual(data['frames'][1][0]['body']['session_epoch'],0)
        with self.assertRaisesRegex(TraceViolation,'namespace_or_session'):audit(**data)

    def test_closed_original_buffer_keeps_its_physical_birth_identity(self):
        data,_=bundle();data['frames'][2][0]['body']['job']['worker_incarnation']=1
        with self.assertRaisesRegex(TraceViolation,'relabelled_dispatch_worker_incarnation'):audit(**data)

    def test_input_key_birth_and_source_are_immutable(self):
        for field in ('key','birth_canonical_sha','source_id'):
            data,_=bundle();data['frames'][1][0]['body']['job'][field]='changed'
            with self.assertRaises(TraceViolation):audit(**data)

    def test_exact_duplicate_full_receipts_are_idempotent(self):
        data,_=bundle();data['completion_rows'].append(cp(data['completion_rows'][1]))
        r=audit(**data);self.assertEqual(r['duplicate_exact_full_receipts'],1)

    def test_conflicting_repeated_full_identity_is_not_accepted(self):
        data,_=bundle();bad=cp(data['completion_rows'][1]);bad['event']['record']['selected_correction']={'changed':True}
        data['completion_rows'].append(bad)
        with self.assertRaisesRegex(TraceViolation,'changed_contents'):audit(**data)

    def test_old_namespace_message_is_stuttering_not_new_authority(self):
        data,_=bundle();bad=cp(data['completion_rows'][1]);bad['owner_epoch']=1;data['completion_rows'].append(bad)
        r=audit(**data);self.assertEqual(r['observed_old_namespace_full_messages_not_new_authority'],1)

    def test_only_durable_actual_facts_advance_certification(self):
        data,_=bundle();data['consumer_rows'][0]['certified_frontier']=8000
        with self.assertRaisesRegex(TraceViolation,'certified_frontier'):audit(**data)

    def test_snapshot_only_consumer_counterexample_is_detected(self):
        data,_=bundle();row=data['consumer_rows'][2]
        row.update(visible_frontier=8000,text=state(8000)['transcript'],private_job=None)
        with self.assertRaisesRegex(TraceViolation,'snapshot_or_certification'):audit(**data)

    def test_per_commit_publication_cannot_use_a_later_final_root(self):
        data,_=bundle();data['publication_rows'][3]['event']['canonical_sha']=digest(state(16000))
        with self.assertRaisesRegex(TraceViolation,'wrong_actual_root'):audit(**data)

    def test_missing_Consumer_tail_is_not_a_complete_run(self):
        data,_=bundle();data['consumer_rows']=data['consumer_rows'][:4]
        with self.assertRaisesRegex(TraceViolation,'did_not_apply_all'):audit(**data)

    def test_all_accepted_input_must_finish_even_if_durable_prefix_is_valid(self):
        data,_=bundle();data['expected_final_frontiers']={'s':24000}
        with self.assertRaisesRegex(TraceViolation,'final_boundary'):audit(**data)

    def test_replay_old_durable_fact_uses_original_identity_without_new_C_U(self):
        data,_=bundle();data['frames']=data['frames'][:2];data['dispatch_rows']=data['dispatch_rows'][:1]
        data['completion_rows']=data['completion_rows'][:2];data['publication_rows']=[]
        b=data['frames'][1][0]['body']
        data['consumer_rows']=[dict(kind='canonical',source_id='s',observed=200.,owner_epoch=1,recovery_replay=True,
            transition_id=b['transition_id'],original_fact_owner_epoch=0,journal_sequence=2,
            canonical_sha=digest(state(8000)),certified_frontier=8000,visible_frontier=8000,
            text=state(8000)['transcript'],private_job=None)]
        data['expected_final_frontiers']={'s':8000}
        r=audit(**data);self.assertEqual(r['counts']['recovery_fact_applications'],1)
        self.assertEqual(r['unique_original_C_U_jobs_used'],1)

    def test_ingress_keeps_original_origin_across_recovery(self):
        sources=[dict(source_id='s',frames=16000,audio_sha256='a'*64)]
        rows=[dict(source_id='s',accepted=F,original_offer=100+F/16000,observed=100+F/16000+.01,audio_sha256='a'*64) for F in (8000,16000)]
        r=check_original_ingress(origin=100,sources=sources,ingress_rows=rows)
        self.assertTrue(r['original_clocks_preserved'])
        rows[-1]['original_offer']+=10;rows[-1]['observed']+=10
        with self.assertRaisesRegex(TraceViolation,'clock_rebased'):
            check_original_ingress(origin=100,sources=sources,ingress_rows=rows)

    def test_ingress_duplicate_ack_does_not_duplicate_an_obligation(self):
        sources=[dict(source_id='s',frames=8000,audio_sha256='a'*64)]
        row=dict(source_id='s',accepted=8000,original_offer=100.5,observed=100.6,audio_sha256='a'*64)
        r=check_original_ingress(origin=100,sources=sources,ingress_rows=[row,cp(row)])
        self.assertEqual(r['idempotent_prefix_reacknowledgments'],1)

    def test_acknowledged_input_cannot_disappear_at_recovery(self):
        with self.assertRaisesRegex(TraceViolation,'obligation_missing'):
            check_original_ingress(origin=100,sources=[dict(source_id='s',frames=16000,audio_sha256='a'*64)],
                ingress_rows=[dict(source_id='s',accepted=8000,original_offer=100.5,observed=100.6,audio_sha256='a'*64)])

    def test_actual_Supervisor_bound_owner_publication_schema(self):
        data,_=bundle()
        data['publication_rows']=[dict(bound_owner_epoch=r['owner_epoch'],received_perf=101.,event=r['event']) for r in data['publication_rows']]
        self.assertEqual(audit(**data)['durable_original_transitions'],2)

    def test_original_cadence_cannot_skip_an_input_transition(self):
        data,_=bundle();data['dispatch_rows'][0]['job']['end']=16000
        with self.assertRaisesRegex(TraceViolation,'500ms_or_EOS'):audit(**data)

    def test_dispatch_must_wait_for_the_original_target_input_offer(self):
        d=[dict(job=dict(end=8000,dispatched_perf=100.6))]
        self.assertTrue(check_dispatch_arrivals(100,d)['no_dispatch_before_original_target_offer'])
        d[0]['job']['dispatched_perf']=100.49
        with self.assertRaisesRegex(TraceViolation,'unoffered_future'):check_dispatch_arrivals(100,d)

    def rejection_fixture(self,seen=True):
        data,_=bundle();event=cp(data['completion_rows'][0]['event']);jid=event['job_id']
        snapshot=dict(canon={'s':digest(state(0))},busy={'full0':jid,'full1':None},session_epochs={'s':0},
            physical_incarnations={'full0':0,'full1':0},inbound_seen={jid:{'asr_early':event_fingerprint(event)} if seen else {}})
        result=dict(disposition='reject_duplicate',reason='exact_duplicate_phase',job_id=jid,physical_terminal=False)
        owner={0:[dict(kind='local_message_disposition',result=cp(result),before=cp(snapshot),after=cp(snapshot))]}
        audits={0:[dict(kind='inbound_disposition',body=dict(result,event=event))]}
        return data['dispatch_rows'],owner,audits

    def test_duplicate_local_rejection_is_idempotent_with_prior_phase_proof(self):
        d,e,a=self.rejection_fixture();r=audit_local_rejections(dispatch_rows=d,owner_event_groups=e,policy_audit_groups=a)
        self.assertEqual(r['legal_progress_wrong_rejections'],0)

    def test_first_current_owned_progress_cannot_be_mislabelled_as_duplicate(self):
        d,e,a=self.rejection_fixture(False)
        with self.assertRaisesRegex(TraceViolation,'first_wellformed_progress'):
            audit_local_rejections(dispatch_rows=d,owner_event_groups=e,policy_audit_groups=a)

    def test_missing_phase_ownership_evidence_remains_unknown_not_zero(self):
        d,e,a=self.rejection_fixture();e[0][0]['before'].pop('inbound_seen');e[0][0]['after'].pop('inbound_seen')
        self.assertIsNone(audit_local_rejections(dispatch_rows=d,owner_event_groups=e,policy_audit_groups=a)['legal_progress_wrong_rejections'])

    def test_reject_cannot_release_another_physical_busy_job(self):
        d,e,a=self.rejection_fixture();e[0][0]['after']['busy']['full1']='changed'
        with self.assertRaisesRegex(TraceViolation,'released_or_relabelled'):
            audit_local_rejections(dispatch_rows=d,owner_event_groups=e,policy_audit_groups=a)

    def worker_fixture(self):
        e=[dict(kind='worker_started',slot='full0',incarnation=0,pid=100,start_ticks=1000,observed=0.),
           dict(kind='worker_death_confirmed',proof=dict(slot='full0',incarnation=0,pid=100,start_ticks=1000,
                confirmed_exit=True,confirmed_dead=True,exitcode=-9,confirmed_perf=2.,partial_frame_thread_blocked=False,
                cuda_release=dict(gpu_context_released=True,old_pid=100,observed_perf=3.))),
           dict(kind='worker_started',slot='full0',incarnation=1,pid=101,start_ticks=1001,observed=4.)]
        d=[dict(owner_epoch=0,physical_slot='full0',physical_incarnation=1,pid=101)]
        return {0:e},d

    def test_worker_replacement_binds_real_exit_and_new_incarnation(self):
        e,d=self.worker_fixture();r=audit_worker_replacements(owner_event_groups=e,dispatch_rows=d)
        self.assertEqual(r['observed_safe_worker_replacements'],1)

    def test_worker_replacement_cannot_precede_GPU_release(self):
        e,d=self.worker_fixture();e[0][-1]['observed']=2.5
        with self.assertRaisesRegex(TraceViolation,'before_actual_CUDA'):
            audit_worker_replacements(owner_event_groups=e,dispatch_rows=d)

    def test_worker_exit_proof_cannot_name_another_PID(self):
        e,d=self.worker_fixture();e[0][1]['proof']['pid']=999
        with self.assertRaisesRegex(TraceViolation,'physical_identity'):
            audit_worker_replacements(owner_event_groups=e,dispatch_rows=d)

if __name__=='__main__':unittest.main()


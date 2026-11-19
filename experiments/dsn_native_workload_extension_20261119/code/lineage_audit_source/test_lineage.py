"""Constructive complete-state chronology controls; no real corpus or model."""
import copy,json,unittest
from lineage import NN,FIELDS,AuditError,encoded,fingerprint,same,execution_state,classify_owner

def cut(F,label):
    x={k:[]for k in FIELDS};x.update(frontier=F,transcript='same visible text',context=label,
        contract=dict(source_sha='a'*64,stage_execution=dict(source_commit=NN)),decoder_type='greedy',
        last_attend_frame=0,initial_token_length=0,sot_index=0,detected_language='zh')
    return x
def build(*,ancestor_equal=False,ready=False,retired=False,own_mismatch=False,forecast_changed=True):
    x0=cut(0,'zero');forecast=cut(8000,'prediction');x1=forecast if ancestor_equal else cut(8000,'selected')
    x2=cut(16000,'converged');conditional_x2=cut(16000,'one-field-different')if own_mismatch else x2
    x3=cut(24000,'selected3');forecast3=cut(24000,'forecast3')if forecast_changed else x3
    if ready:sequences=dict(A=1,B=2,Br=3,C=4,Cr=5,Ar=6,Ai=7,D=8,Dr=9,Di=10,Ci=11)
    else:sequences=dict(A=1,B=2,Br=3,C=4,Ar=5,Ai=6,D=7,Dr=8,Di=9,Cr=10,Ci=11)
    def job(jid,start,deps):
        seq=sequences[jid];end=min(start['frontier']+8000,24000)
        return dict(job_id=jid,source_id='s',worker='full0'if jid in('A','D')else'full1',worker_incarnation=0,
            dispatch_epoch=0,start=start,end=end,frozen_dependencies=deps,birth_canonical_sha=fingerprint(deps[0]),
            started_on_canonical=jid in('A','D'),owner_dispatch_order=dict(sequence=seq,observed_perf=float(seq)),
            key=json.dumps(dict(complete_start_cut=start,source_sha256='a'*64,target_frontier=end,
                is_last=end==24000,runtime_identity=dict(source_commit=NN),added_audio_float32_sha256='b'*64)))
    jobs=[job('A',x0,[x0]),job('B',forecast,[x0,forecast]),job('C',conditional_x2,[x0,forecast,conditional_x2]),job('D',x1,[x1])]
    by={j['job_id']:j for j in jobs};endcuts=dict(A=x1,B=conditional_x2,C=x3,D=x2)
    workers=[];receipts=[]
    for jid in('A','B','C','D'):
        j=by[jid];fcast=forecast3 if jid=='C'else forecast if jid=='A'else endcuts[jid]
        e=dict(kind='asr_early',job_id=jid,source_id='s',worker=j['worker'],worker_incarnation=0,dispatch_epoch=0,
            start_state=j['start'],end_frontier=j['end'],projection=dict(kind='typed_ASR_stage_identity_feedback_projection',
                learned_C_executed=False,original_full_infer_completed=False,end=fcast,end_state_sha=fingerprint(fcast)))
        workers.append(dict(event=e,physical_slot=j['worker'],physical_incarnation=0,owner_dequeued_perf=float(sequences[jid])+.01))
        neural_begin=4.25 if jid=='C'else float(sequences[jid])+.1
        neural_end=4.75 if jid=='C'and ready else 9.75 if jid=='C'else float(sequences[jid+'r'])-.1
        rec=dict(role='authority',candidate_handoff=False,start_state=fingerprint(j['start']),end_state=fingerprint(endcuts[jid]),
            model_start=neural_begin,model_end=neural_end,native_model_evaluated=True)
        e=dict(kind='completed',job_id=jid,source_id='s',worker=j['worker'],worker_incarnation=0,dispatch_epoch=0,
            start=j['start'],end=endcuts[jid],record=rec)
        workers.append(dict(event=e,physical_slot=j['worker'],physical_incarnation=0))
        receipts.append(dict(job_id=jid,source_id='s',outcome_kind='buffered_full'if jid=='B'or(jid=='C'and ready)else'canonical',
            complete_receipt_order=dict(sequence=sequences[jid+'r'],observed_perf=float(sequences[jid+'r']))))
    facts=[];installs=[]
    for ix,jid in enumerate(('A','D','C'),2):
        if jid=='C'and(own_mismatch or retired):continue
        j=by[jid];body=dict(job=j,source_id='s',parent_state=j['start'],next_state=endcuts[jid],
            parent_state_sha256=fingerprint(j['start']),next_state_sha256=fingerprint(endcuts[jid]))
        facts.append(dict(sequence=ix,body=body))
        installs.append(dict(job_id=jid,source_id='s',receipt=dict(sequence=ix),parent_state_sha=fingerprint(j['start']),
            next_state_sha=fingerprint(endcuts[jid]),canonical_install_order=dict(sequence=sequences[jid+'i'],observed_perf=float(sequences[jid+'i']))))
    audits=[]
    if retired or own_mismatch:audits.append(dict(kind='discarded_full',observed=7.5 if retired else 11.5,body=dict(job=by['C'])))
    return dict(jobs=jobs,installs=installs,receipts=receipts,workers=workers,audits=audits,facts=facts,
        initials={'s':x0},source_frames={'s':24000},audio_float32_hash=lambda *args:'b'*64)

class Controls(unittest.TestCase):
    def test_constructive_three_frontier_four_call_active_reconvergence(self):
        result=classify_owner(**build());r=next(r for r in result['jobs']if r['job_id']=='C')
        self.assertTrue(r['actual_same_original_job_selected_after_reconfirmation'])
        self.assertEqual(r['first_refutation_execution_phase'],'native_model_active')
        self.assertEqual(r['own_confirmation_execution_phase'],'native_model_active')
        self.assertEqual(result['counts']['ancestor_refuted_original_job_later_selected_installed'],1)
    def test_completed_but_logically_owned_ready_survives(self):
        r=next(r for r in classify_owner(**build(ready=True))['jobs']if r['job_id']=='C')
        self.assertTrue(r['actual_same_original_job_selected_after_reconfirmation'])
        self.assertEqual(r['first_refutation_execution_phase'],'owner_admitted_ready')
    def test_birth_root_changed_without_actual_ancestor_refutation_is_negative(self):
        r=classify_owner(**build(ancestor_equal=True))
        self.assertEqual(r['counts']['actual_ancestor_refuted_jobs'],0)
        self.assertEqual(r['counts']['ancestor_refuted_original_job_later_selected_installed'],0)
    def test_single_nontext_state_field_difference_refutes_complete_input(self):
        r=next(r for r in classify_owner(**build(own_mismatch=True))['jobs']if r['job_id']=='C')
        self.assertEqual(r['own_input_actual_status'],'actual_installed_same_F_refutes')
        self.assertFalse(r['original_job_owned_through_confirmation'])
    def test_retired_original_then_eventual_equal_input_not_survivor(self):
        r=next(r for r in classify_owner(**build(retired=True))['jobs']if r['job_id']=='C')
        self.assertIsNotNone(r['own_input_later_confirm_order'])
        self.assertFalse(r['original_job_owned_through_confirmation'])
        self.assertFalse(r['actual_same_original_job_selected_after_reconfirmation'])
    def test_wrong_chronology_fails_instead_of_relabeling(self):
        fixture=build();next(j for j in fixture['jobs']if j['job_id']=='C')['owner_dispatch_order']=dict(sequence=12,observed_perf=12.)
        with self.assertRaises(AuditError):classify_owner(**fixture)
    def test_forecast_change_is_independent_overlapping_axis(self):
        positive=next(r for r in classify_owner(**build())['jobs']if r['job_id']=='C')
        ordinary=next(r for r in classify_owner(**build(ancestor_equal=True))['jobs']if r['job_id']=='C')
        self.assertTrue(positive['own_input_confirmed_and_forecast_changed'])
        self.assertTrue(ordinary['own_input_confirmed_and_forecast_changed']);self.assertFalse(ordinary['actual_ancestor_refuted'])
    def test_missing_clocks_are_unknown_not_model_active(self):
        self.assertEqual(execution_state(None,None,2.,False),'neural_clock_unknown_owner_inflight')
        self.assertEqual(execution_state(dict(native_model_evaluated=True,model_start=1.,model_end=2.),None,3.,False),
                         'after_observed_neural_stage_owner_unready')
    def test_wrong_audio_full_key_rejected(self):
        f=build();f['audio_float32_hash']=lambda *args:'c'*64
        with self.assertRaises(AuditError):classify_owner(**f)
    def test_complete_field_set_and_text_equality_not_enough(self):
        a=cut(8000,'a');b=cut(8000,'b');self.assertFalse(same(a,b))
        del a['last_attend_frame']
        with self.assertRaises(AuditError):same(a,b)

if __name__=='__main__':unittest.main()

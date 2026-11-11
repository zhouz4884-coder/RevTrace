"""Focused prepared controls. Run only in Root's post-pilot idle CPU window."""
import copy,unittest
from definitions import input_profile,execution_state,ready_before,loss_window,final_outcome
from consumer_audit import audit_consumer

class ActualPolicyOpportunityControls(unittest.TestCase):
    def fixture(self,kind):
        import test_versioned_policy as fixtures
        h=fixtures.VersionedControls();h.setUp();h.c=h.make(kind);return h
    def test_direct_compatible_handover_is_kept_by_both_actual_classes(self):
        from resilience_policy import ResilientFullSpecCoordinator
        from versioned_policy import DependencyVersionedCoordinator
        for kind in (ResilientFullSpecCoordinator,DependencyVersionedCoordinator):
            h=self.fixture(kind);parent,child,p1,p2=h.two_pending();h.finish(parent,p1);j=h.c.jobs[child]
            p=input_profile(dict(j,start=j['start'].state,frozen_dependencies=[x.state for x in j['frozen_dependencies']]),p1.state,{0:h.root.state,8000:p1.state},0)
            self.assertTrue(p['direct_compatible_retained_by_both']);self.assertFalse(p['treatment_disagreement'])
            self.assertNotIn(child,h.c.invalidations())
    def test_ancestor_fence_differs_while_complete_future_input_unresolved(self):
        from versioned_policy import DependencyVersionedCoordinator
        from test_resilience_policy import cut
        h=self.fixture(DependencyVersionedCoordinator);parent,child,p1,p2=h.two_pending();h.finish(child,p2)
        future=h.register('f1',p2);j=h.c.jobs[future];actual=cut(8000,'different ancestor');h.finish(parent,actual)
        p=input_profile(dict(j,start=j['start'].state,frozen_dependencies=[x.state for x in j['frozen_dependencies']]),actual.state,{0:h.root.state,8000:actual.state},0)
        self.assertTrue(p['treatment_disagreement']);self.assertEqual(p['input_status'],'future_complete_input_unresolved')
        self.assertEqual(h.c.invalidations()[future]['kind'],'dependency_version_policy_fence')
    def test_sticky_fence_survives_current_input_convergence_actual_class(self):
        from versioned_policy import DependencyVersionedCoordinator
        from test_resilience_policy import cut
        h=self.fixture(DependencyVersionedCoordinator);parent,child,p1,p2=h.two_pending();h.finish(child,p2)
        future=h.register('f1',p2);j=h.c.jobs[future];actual=cut(8000,'different');h.finish(parent,actual)
        frozen=dict(j,start=j['start'].state,frozen_dependencies=[x.state for x in j['frozen_dependencies']])
        first=input_profile(frozen,actual.state,{0:h.root.state,8000:actual.state},0)
        h.c.pop_ready_commits();replacement=h.register('f0',actual);h.finish(replacement,p2)
        second=input_profile(frozen,p2.state,{0:h.root.state,8000:actual.state,16000:p2.state},0,first['ancestor_fence'])
        self.assertEqual(second['input_status'],'currently_confirmed');self.assertTrue(second['treatment_disagreement'])
        self.assertEqual(h.c.invalidations()[future]['kind'],'dependency_version_policy_fence')
    def test_full_start_refutation_is_not_ancestor_only_increment(self):
        from test_resilience_policy import cut
        a,b=cut(8000,'pred').state,cut(8000,'actual').state
        p=input_profile(dict(start=a,end=16000,dispatch_epoch=0,frozen_dependencies=[cut(0).state,a]),b,{8000:b},0)
        self.assertEqual(p['input_status'],'complete_start_refuted');self.assertFalse(p['treatment_disagreement'])
    def test_actual_fullcall_can_later_install_the_same_retained_converged_job(self):
        from resilience_policy import ResilientFullSpecCoordinator
        from test_resilience_policy import cut
        h=self.fixture(ResilientFullSpecCoordinator);parent,child,p1,p2=h.two_pending();h.finish(child,p2)
        future=h.register('f1',p2);j=h.c.jobs[future];actual=cut(8000,'changed ancestor');h.finish(parent,actual)
        p=input_profile(dict(j,start=j['start'].state,frozen_dependencies=[x.state for x in j['frozen_dependencies']]),actual.state,{0:h.root.state,8000:actual.state},0)
        self.assertTrue(p['treatment_disagreement']);h.c.pop_ready_commits()
        replacement=h.register('f0',actual);h.finish(replacement,p2)
        self.assertNotIn(future,h.c.invalidations());self.assertEqual(h.finish(future,cut(24000,'actual full C'))['outcome']['kind'],'canonical')
    def test_actual_UIR_suppresses_only_hints_and_still_refuses_wrong_complete_result(self):
        from resilience_policy import ResilientFullSpecCoordinator
        from retention_policy import UnconditionalInflightCoordinator,process_c_entry_hints
        from test_resilience_policy import cut
        class Sink:
            def __init__(self):self.rows=[]
            def send(self,value):self.rows.append(value)
        sent=[]
        for kind in (ResilientFullSpecCoordinator,UnconditionalInflightCoordinator):
            h=self.fixture(kind);parent,child,p1,p2=h.two_pending();h.finish(parent,cut(8000,'actual differs'))
            sinks={slot:Sink() for slot in ('f0','f1')};logs=[]
            process_c_entry_hints(h.c,{slot:{'hints':sink} for slot,sink in sinks.items()},set(),lambda kind,**body:logs.append(dict(kind=kind,**body)))
            sent.append(sum(len(s.rows) for s in sinks.values()))
            self.assertEqual(h.finish(child,p2)['outcome']['kind'],'discarded')
            self.assertEqual(logs[0]['proof']['kind'],'actual_canonical_disagrees_with_complete_start')
        self.assertEqual(sent,[1,0])
    def test_covered_and_epoch_fence_are_not_input_retention_disagreements(self):
        from test_resilience_policy import cut
        j=dict(start=cut(8000).state,end=16000,dispatch_epoch=0,frozen_dependencies=[])
        self.assertEqual(input_profile(j,cut(16000).state,{},0)['fullcall_reason'],'covered_by_actual_canonical')
        self.assertEqual(input_profile(j,cut(0).state,{},1)['fullcall_reason'],'session_epoch_changed')

class ClockAndOutcomeControls(unittest.TestCase):
    def test_model_active_not_queued_ready_or_physical_complete_unread(self):
        r=dict(worker_job_begin_perf=1,model_start=2,model_end=5,worker_job_end_perf=6,native_model_evaluated=True)
        self.assertEqual(execution_state(r,{},3),'native_model_active')
        self.assertEqual(execution_state(r,{},0),'queued_before_worker_begin')
        self.assertEqual(execution_state(r,{},6.5),'physical_full_complete_owner_unadmitted')
        self.assertEqual(execution_state(r,{},6.5,True),'owner_admitted_complete_ready')
    def test_missing_abort_infer_interval_does_not_become_model_zero(self):
        terminal=dict(worker_job_begin_perf=1,worker_job_end_perf=6,asr_prefix_executed=True)
        self.assertEqual(execution_state(None,terminal,3),'worker_active_infer_timer_missing')
    def test_readiness_uses_admission_sequence_and_actual_buffer_not_model_end(self):
        self.assertTrue(ready_before({'sequence':4},{'sequence':5},True))
        self.assertFalse(ready_before({'sequence':6},{'sequence':5},True))
        self.assertFalse(ready_before({'sequence':4},{'sequence':5},False))
    def test_later_AU_durable_owner_install_and_Consumer_replay_separate(self):
        self.assertEqual(final_outcome('j',{'j'},set(),set(),set()),'later_durable_selected_application_unobserved')
        self.assertEqual(final_outcome('j',{'j'},set(),set(),set(),{'j'}),'later_selected_original_full_result_owner_installed')
        self.assertEqual(final_outcome('j',{'j'},set(),set(),set(),(),{'j'}),'later_selected_durable_fact_consumer_applied')
    def test_gap_is_censored_at_next_canonical_not_extended_across_roots(self):
        rows=[dict(source_id='s',kind='canonical',observed=2,visible_frontier=8000),dict(source_id='s',kind='canonical',observed=3,visible_frontier=8000),dict(source_id='s',kind='private',observed=8,visible_frontier=16000)]
        r=loss_window(rows,0,'s',16000,8000);self.assertEqual(r['end'],3);self.assertTrue(r['right_censored']);self.assertEqual(r['area_audio_seconds_x_wall_seconds'],.5)
    def test_gap_area_includes_piecewise_partial_private_recovery(self):
        rows=[dict(source_id='s',kind='canonical',observed=2,visible_frontier=8000),dict(source_id='s',kind='private',observed=3,visible_frontier=12000),dict(source_id='s',kind='private',observed=5,visible_frontier=16000)]
        r=loss_window(rows,0,'s',16000,8000);self.assertEqual(r['area_audio_seconds_x_wall_seconds'],1.0);self.assertFalse(r['right_censored'])
    def test_zero_opportunity_is_presence_absence_not_a_technical_error(self):
        from audit_all import presence
        sources=[dict(source_id='s',speaker_id='p')]
        rows=[dict(source_id='s',strategy='fullcall',repeat=r,status='PASS_ACTUAL_INPUT_FACT_CONSUMER_ACCOUNTING_BINDINGS',opportunities={}) for r in (0,1)]
        self.assertFalse(presence(rows,sources,('fullcall',),'unique_ancestor_disagreement_jobs')['all_speakers_minimum_one'])
    def test_missing_energy_owner_schema_or_no_samples_is_not_clean(self):
        from trial_audit import ownership
        window=dict(begin_perf=1,end_perf=2);workers=[dict(pid=1,start_ticks=5,begin=0,end=3)]
        rows=[dict(time=t,boards={'0':{'watts':1},'1':{'watts':1}},observation_begin_perf=t-.1,observation_end_perf=t+.1) for t in (1,2)]
        self.assertFalse(ownership(rows,workers,window)['verifiable'])
        for row in rows:row['compute_processes']=[]
        self.assertFalse(ownership(rows,workers,dict(begin_perf=1.2,end_perf=1.8))['verifiable'])
    def test_energy_recorded_owner_interval_match_and_foreign_owner(self):
        from trial_audit import ownership
        workers=[dict(pid=1,start_ticks=5,begin=0,end=3)];window=dict(begin_perf=1,end_perf=2)
        rows=[dict(time=t,boards={'0':{'watts':1},'1':{'watts':1}},observation_begin_perf=t-.1,observation_end_perf=t+.1,compute_processes=[{'pid':1}]) for t in (1,2)]
        self.assertTrue(ownership(rows,workers,window)['verifiable'])
        rows[0]['compute_processes']=[{'pid':99}];self.assertFalse(ownership(rows,workers,window)['verifiable'])

class ActualConsumerSupportControls(unittest.TestCase):
    def setup_rows(self,compatible=True):
        from test_resilience_policy import cut
        root,p1,p2=cut(0),cut(8000,'p1'),cut(16000,'p2');actual=p1 if compatible else cut(8000,'corrected')
        receipt=dict(sequence=2,record_sha256='a'*64,offset=0,end_offset=100)
        pubs=[dict(bound_owner_epoch=0,event=dict(kind='private',source_id='s',publication_id=1,canonical_sha=root.sha256,steps=[dict(job_id='a',start=root.state,end=p1.state,kind='typed_ASR_projection'),dict(job_id='b',start=p1.state,end=p2.state,kind='typed_ASR_projection')])),
            dict(bound_owner_epoch=0,event=dict(kind='canonical',source_id='s',publication_id=2,state=actual.state,durable_receipt=receipt))]
        rows=[dict(kind='private',source_id='s',observed=1,owner_epoch=0,publication_id=1,canonical_sha=root.sha256,text='p2',visible_frontier=16000,certified_frontier=0,private_job='b'),
            dict(kind='canonical',source_id='s',observed=2,owner_epoch=0,publication_id=2,journal_sequence=2,canonical_sha=actual.sha256,text='p2' if compatible else 'corrected',visible_frontier=16000 if compatible else 8000,certified_frontier=8000,private_job='b' if compatible else None)]
        facts=[dict(sequence=2,receipt=receipt,body=dict(parent_state=root.state,next_state=actual.state,record=dict(native_model_evaluated=True)))]
        registry={jid:dict(job=dict(source_id='s',start=start.state,end=end.frontier),asr_ends={end.sha256:dict(available_lower_bound=.5,owner_dequeued_perf=.6)},full_ends={}) for jid,start,end in (('a',root,p1),('b',p1,p2))}
        return rows,pubs,facts,{'s':root.state},registry
    def test_complete_compatible_ahead_view_preserved_actual_Reconciler(self):
        r=audit_consumer(*self.setup_rows());self.assertEqual(r['counts']['compatible_ahead_applications'],1)
        self.assertEqual(r['counts']['compatible_ahead_preserved'],1);self.assertEqual(r['counts'].get('avoidable_supported_view_losses',0),0)
    def test_necessary_incompatible_withdrawal_kept_separate(self):
        r=audit_consumer(*self.setup_rows(False));self.assertEqual(r['counts']['necessary_incompatible_withdrawals'],1)
        self.assertEqual(r['counts'].get('avoidable_supported_view_losses',0),0)
    def test_same_frontier_wrong_text_is_not_whole_view_support(self):
        rows,pubs,facts,initials,registry=self.setup_rows();rows[-1]['text']='wrong'
        with self.assertRaises(ValueError):audit_consumer(rows,pubs,facts,initials,registry)
    def test_contiguous_view_without_actual_registered_receipt_is_rejected(self):
        rows,pubs,facts,initials,registry=self.setup_rows();pubs[0]['event']['steps'][1]['job_id']='unregistered'
        with self.assertRaises(ValueError):audit_consumer(rows,pubs,facts,initials,registry)
    def test_ASR_projection_cannot_claim_full_C_U_completion(self):
        rows,pubs,facts,initials,registry=self.setup_rows();pubs[0]['event']['steps'][1]['actual_full_C_U_completed']=True
        with self.assertRaises(ValueError):audit_consumer(rows,pubs,facts,initials,registry)
    def test_late_identical_duplicate_does_not_erase_earliest_receipt_availability(self):
        from consumer_audit import provisional_registry
        from test_resilience_policy import cut
        root,end=cut(0),cut(8000,'p');job=dict(source_id='s',start=root.state,end=8000,worker='f0',worker_incarnation=0,dispatch_epoch=0,job_id='a')
        e=dict(kind='asr_early',job_id='a',source_id='s',worker='f0',worker_incarnation=0,dispatch_epoch=0,start_state=root.state,start_state_sha=root.sha256,end_frontier=8000,producer_role='authority',candidate_wire=None,produced_perf=.5,
            projection=dict(kind='typed_ASR_stage_identity_feedback_projection',learned_C_executed=False,original_full_infer_completed=False,token_ids=[8000],end=end.state,end_state_sha=end.sha256))
        first=dict(event=e,physical_slot='f0',physical_incarnation=0,owner_dequeued_perf=.6);second=dict(first,owner_dequeued_perf=3.6)
        registry=provisional_registry([{'job':job}],[first,second]);self.assertEqual(registry['a']['asr_ends'][end.sha256]['owner_dequeued_perf'],.6)

if __name__=='__main__':unittest.main()

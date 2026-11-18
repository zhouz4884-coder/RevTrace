"""CPU-only outcome, witness-binding and gap-accounting fixtures."""
import copy,unittest
from consumer_audit import audit_consumer
from native_view_metrics import continuity_metrics,union_segment_area

def row(t,f,kind='private',root='a',source='s',epoch=0):
    return dict(source_id=source,observed=t,visible_frontier=f,kind=kind,canonical_sha=root,owner_epoch=epoch)

def witness(i,t,before,after,status='compatible_boundary',source='s'):
    return dict(row_index=i,observed=t,source_id=source,support_status=status,
        before_visible_frontier=before,after_visible_frontier=after,
        before_nonempty_visible_ahead=True,preserved_complete_tip=False)

class FrontierContinuityControls(unittest.TestCase):
    def test_partial_recovery_integrates_actual_piecewise_frontiers(self):
        rows=[row(1,16000),row(2,8000,'canonical','b'),row(3,12000,root='b'),row(5,16000,root='b')]
        x=continuity_metrics(rows,[witness(1,2,16000,8000)],end_perf=6)
        c=x['continuity'];self.assertEqual(c['avoidable_withdrawals'],1)
        self.assertEqual(c['removed_audio_seconds'],.5);self.assertEqual(c['total_gap_audio_seconds_x_wall_seconds'],1.)
        self.assertEqual(c['avoidable_gap_audio_seconds_x_wall_seconds'],1.)
        self.assertFalse(x['loss_windows'][0]['right_censored']);self.assertEqual(c['gap_restored_windows'],1)
    def test_next_canonical_stops_same_root_area_without_faking_cross_root_recovery(self):
        rows=[row(1,16000),row(2,8000,'canonical','b'),row(3,8000,'canonical','c'),row(5,16000,root='c')]
        x=continuity_metrics(rows,[witness(1,2,16000,8000)],end_perf=6);c=x['continuity']
        self.assertEqual(c['total_gap_audio_seconds_x_wall_seconds'],1.5)
        self.assertEqual(c['avoidable_gap_audio_seconds_x_wall_seconds'],.5)
        self.assertTrue(x['loss_windows'][0]['boundary_truncated']);self.assertTrue(x['loss_windows'][0]['right_censored'])
    def test_actual_restoration_at_next_canonical_closes_recorded_window(self):
        rows=[row(1,16000),row(2,8000,'canonical','b'),row(3,16000,'canonical','c')]
        x=continuity_metrics(rows,[witness(1,2,16000,8000)],end_perf=4)
        self.assertEqual(x['continuity']['avoidable_gap_audio_seconds_x_wall_seconds'],.5)
        self.assertTrue(x['loss_windows'][0]['restored']);self.assertFalse(x['loss_windows'][0]['right_censored'])
    def test_explicit_service_end_keeps_observed_censored_tail(self):
        x=continuity_metrics([row(1,16000),row(2,8000,'canonical','b')],[witness(1,2,16000,8000)],end_perf=6)
        self.assertEqual(x['continuity']['total_gap_audio_seconds_x_wall_seconds'],2.)
        self.assertEqual(x['continuity']['avoidable_gap_audio_seconds_x_wall_seconds'],2.)
        self.assertTrue(x['loss_windows'][0]['right_censored']);self.assertEqual(x['loss_windows'][0]['stop_reason'],'service_end')
    def test_epoch_boundary_truncates_same_root_continuation(self):
        rows=[row(1,16000),row(2,8000,'canonical','b'),row(3,8000,root='b',epoch=1),row(5,16000,root='b',epoch=1)]
        x=continuity_metrics(rows,[witness(1,2,16000,8000)],end_perf=6)
        self.assertEqual(x['continuity']['avoidable_gap_audio_seconds_x_wall_seconds'],.5)
        self.assertEqual(x['loss_windows'][0]['stop_reason'],'owner_epoch_boundary')
    def test_refuted_boundary_is_necessary_not_avoidable(self):
        rows=[row(1,16000),row(2,8000,'canonical','b'),row(3,16000,root='b')]
        c=continuity_metrics(rows,[witness(1,2,16000,8000,'refuted_boundary')],end_perf=4)['continuity']
        self.assertEqual((c['necessary_withdrawals'],c['avoidable_withdrawals'],c['unknown_withdrawals']),(1,0,0))
    def test_missing_boundary_is_unknown_not_an_invented_refutation(self):
        rows=[row(1,16000),row(2,8000,'canonical','b'),row(3,16000,root='b')]
        c=continuity_metrics(rows,[witness(1,2,16000,8000,'missing_boundary')],end_perf=4)['continuity']
        self.assertEqual((c['unknown_withdrawals'],c['necessary_withdrawals'],c['avoidable_withdrawals']),(1,0,0))
    def test_private_empty_view_drop_has_unknown_semantics(self):
        c=continuity_metrics([row(1,16000),row(2,0),row(3,16000)],[],end_perf=4)['continuity']
        self.assertEqual(c['unknown_withdrawals'],1);self.assertEqual(c['removed_audio_seconds'],1.)
    def test_no_opportunity_is_zero_observed_outcome_not_a_failure(self):
        c=continuity_metrics([row(1,8000),row(2,16000)],[],end_perf=4)['continuity']
        self.assertEqual(c['compatible_ahead_applications'],0);self.assertEqual(c['total_gap_audio_seconds_x_wall_seconds'],0.)
    def test_compatible_preservation_is_positive_opportunity_and_zero_loss(self):
        e=witness(1,2,16000,16000);e['preserved_complete_tip']=True
        c=continuity_metrics([row(1,16000),row(2,16000,'canonical','b')],[e],end_perf=4)['continuity']
        self.assertEqual((c['compatible_ahead_applications'],c['compatible_ahead_preserved'],c['avoidable_withdrawals']),(1,1,0))
    def test_drop_window_does_not_charge_new_loss_below_its_initial_removed_span(self):
        rows=[row(1,16000),row(2,8000,'canonical','b'),row(3,0,root='b'),row(4,16000,root='b')]
        c=continuity_metrics(rows,[witness(1,2,16000,8000)],end_perf=5)['continuity']
        self.assertEqual(c['avoidable_gap_audio_seconds_x_wall_seconds'],1.)
        self.assertEqual(c['total_gap_audio_seconds_x_wall_seconds'],1.5)
    def test_zero_time_drop_can_have_zero_area_but_nonzero_count(self):
        rows=[row(1,16000),row(2,8000,'canonical','b'),row(2,16000,root='b')]
        c=continuity_metrics(rows,[witness(1,2,16000,8000)],end_perf=3)['continuity']
        self.assertEqual(c['avoidable_withdrawals'],1);self.assertEqual(c['avoidable_gap_audio_seconds_x_wall_seconds'],0.)
    def test_service_end_before_last_actual_row_is_rejected(self):
        with self.assertRaises(ValueError):continuity_metrics([row(4,16000)],[],end_perf=3)
    def test_clock_regression_is_not_sorted_away(self):
        with self.assertRaises(ValueError):continuity_metrics([row(2,8000),row(1,16000)],[],end_perf=3)
    def test_nonfinite_clock_and_negative_frontier_rejected(self):
        for bad in (row(float('nan'),8000),row(1,-1)):
            with self.assertRaises(ValueError):continuity_metrics([bad],[],end_perf=3)
    def test_canonical_witness_cannot_be_attached_to_another_source(self):
        with self.assertRaises(ValueError):continuity_metrics([row(1,16000),row(2,8000,'canonical','b')],[witness(1,2,16000,8000,source='other')],end_perf=3)

class UnionControls(unittest.TestCase):
    def rect(self,start,end,low,high,source='s'):return dict(start=start,end=end,low=low,high=high,source_id=source)
    def test_identical_windows_are_not_double_counted(self):
        r=self.rect(0,1,0,16000);self.assertEqual(union_segment_area([r,r]),1.)
    def test_nested_and_partially_overlapping_audio_losses_union(self):
        outer=self.rect(0,4,0,16000);nested=self.rect(1,3,4000,12000);extra=self.rect(1,3,8000,24000)
        self.assertEqual(union_segment_area([outer,nested]),4.)
        self.assertEqual(union_segment_area([outer,extra]),5.)
    def test_distinct_sources_add_even_at_same_wall_time(self):
        self.assertEqual(union_segment_area([self.rect(0,1,0,16000),self.rect(0,1,0,16000,'other')]),2.)

class BoundConsumerControls(unittest.TestCase):
    def fixture(self,retain=True,compatible=True):
        from test_opportunities import ActualConsumerSupportControls
        rows,pubs,facts,initials,registry=ActualConsumerSupportControls().setup_rows(compatible)
        facts[0]['body']['source_id']='s'
        for r in rows:r['consumer_retain_views']=retain
        if not retain:
            rows[-1].update(text=facts[0]['body']['next_state']['transcript'],visible_frontier=8000,private_job=None)
        return rows,pubs,facts,initials,registry
    def annotate(self,data,retain):
        from feedback_contract import FeedbackCut
        rows,pubs,facts,initials,_=data
        root=FeedbackCut(initials['s']);target=FeedbackCut(facts[0]['body']['next_state'])
        boundary=FeedbackCut(pubs[0]['event']['steps'][0]['end']);tip=FeedbackCut(pubs[0]['event']['steps'][1]['end'])
        compatible=boundary.same(target);preserve=compatible and retain
        snapshot=lambda r:{k:r[k]for k in ('certified_frontier','visible_frontier','text','canonical_sha','private_job')}
        rows[-1]['view_reconciliation']=dict(consumer_retain_views=retain,
            support_status='compatible_boundary'if compatible else'refuted_boundary',
            before=snapshot(rows[0]),after=snapshot(rows[1]),before_root_sha=root.sha256,before_tip_sha=tip.sha256,
            actual_new_canonical_sha=target.sha256,boundary_index=0,boundary_job_id='a',boundary_end_sha=boundary.sha256,
            before_internal_ahead=True,before_nonempty_visible_ahead=True,
            reconciliation=dict(compatible=compatible,ahead=True,retained_steps=1 if preserve else 0,
                covered_steps_removed=1 if preserve else 0,discarded_steps=0 if preserve else 2,generation=0 if preserve else 1))
        return data
    def test_S0_compatible_clear_is_valid_observed_loss(self):
        r=audit_consumer(*self.fixture(False),retain_views=False)
        self.assertEqual(r['counts']['avoidable_supported_view_losses'],1)
        self.assertEqual(r['canonical_events'][0]['support_status'],'compatible_boundary')
        self.assertEqual(r['canonical_events'][0]['retained_steps'],0)
    def test_S1_compatible_ahead_view_survives(self):
        r=audit_consumer(*self.fixture(True),retain_views=True)
        self.assertEqual(r['counts']['compatible_ahead_preserved'],1)
        self.assertEqual(r['counts'].get('avoidable_supported_view_losses',0),0)
    def test_both_S_policies_refuse_incompatible_view_preservation(self):
        for retain in (False,True):
            r=audit_consumer(*self.fixture(retain,False),retain_views=retain)
            self.assertEqual(r['canonical_events'][0]['support_status'],'refuted_boundary')
            self.assertEqual(r['counts']['necessary_incompatible_withdrawals'],1)
    def test_wrong_actual_S_flag_is_not_accepted(self):
        with self.assertRaises(ValueError):audit_consumer(*self.fixture(False),retain_views=True)
    def test_wrong_durable_source_is_rejected(self):
        data=self.fixture();data[2][0]['body']['source_id']='other'
        with self.assertRaises(ValueError):audit_consumer(*data)
    def test_wrong_private_root_and_wrong_publication_source_are_rejected(self):
        for field,value in [('canonical_sha','f'*64),('source_id','other')]:
            data=self.fixture();data[1][0]['event'][field]=value
            with self.assertRaises(ValueError):audit_consumer(*data)
    def test_unregistered_original_receipt_is_not_invented(self):
        data=self.fixture();data[1][0]['event']['steps'][-1]['job_id']='fake'
        with self.assertRaises(ValueError):audit_consumer(*data)
    def test_duplicate_durable_application_is_rejected(self):
        data=self.fixture();data[0].append(copy.deepcopy(data[0][-1]))
        with self.assertRaises(ValueError):audit_consumer(*data)
    def test_missing_boundary_is_reported_as_unknown(self):
        data=self.fixture(False);rows,pubs,facts,initials,registry=data
        from feedback_contract import FeedbackCut
        tip=pubs[0]['event']['steps'][-1]['end'];start=initials['s'];end=FeedbackCut(tip)
        pubs[0]['event']['steps']=[dict(job_id='a',start=start,end=tip,kind='typed_ASR_projection')]
        registry['a']=dict(job=dict(source_id='s',start=start,end=16000),asr_ends={end.sha256:dict(available_lower_bound=.5,owner_dequeued_perf=.6)},full_ends={})
        rows[0]['private_job']='a'
        r=audit_consumer(*data,retain_views=False)
        self.assertEqual(r['canonical_events'][0]['support_status'],'missing_boundary')
        self.assertEqual(r['counts']['unknown_support_withdrawals'],1)
    def test_required_metadata_cannot_be_absent_or_self_asserted(self):
        data=self.fixture(False)
        with self.assertRaises(ValueError):audit_consumer(*data,retain_views=False,require_reconciliation_metadata=True)
        data[0][-1]['view_reconciliation']={'support_status':'compatible_boundary'}
        with self.assertRaises(ValueError):audit_consumer(*data,retain_views=False)
    def test_complete_reconciliation_metadata_is_checked_and_accepted(self):
        for retain in (False,True):
            for compatible in (False,True):
                data=self.annotate(self.fixture(retain,compatible),retain)
                r=audit_consumer(*data,retain_views=retain,require_reconciliation_metadata=True)
                self.assertTrue(r['canonical_events'][0]['metadata_binding_checked'])
    def test_forged_emitted_compatibility_and_tip_are_rejected(self):
        for field,value in [('support_status','refuted_boundary'),('before_tip_sha','f'*64)]:
            data=self.annotate(self.fixture(False),False);data[0][-1]['view_reconciliation'][field]=value
            with self.assertRaises(ValueError):audit_consumer(*data,retain_views=False,require_reconciliation_metadata=True)

if __name__=='__main__':unittest.main()

"""Synthetic CPU controls for actual-time/frontier read-point arithmetic."""
import copy
import unittest
from continuity_readpoints import (aggregate_readpoints,credited_readpoints,
    duration_statistics,high_watermark_gap,union_area,validate_rows,validate_windows)

def row(t,f,kind='private'):
    return dict(source_id='s',observed=t,visible_frontier=f,certified_frontier=f,
                kind=kind,owner_epoch=0,canonical_sha='root',consumer_retain_views=False)
def frontier(F=8000,offer=.5,D=.2,C=.4,weight=.5):
    return dict(source_id='s',frontier=F,offer=offer,D=D,C=C,audio_seconds=weight)
def window(start=2.3,end=2.7,low=0,high=8000,classification='avoidable',stop='restored_within_same_root'):
    return dict(source_id='s',row_index=1,classification=classification,start=start,end=end,
                stop_reason=stop,segments=[dict(source_id='s',start=start,end=end,low=low,high=high)])
def calculate(rows=None,windows=None,frontiers=None,end=3.,initial_known=True):
    return credited_readpoints(frontiers or[frontier()],rows if rows is not None else[row(.7,8000),row(2.3,0,'canonical'),row(2.7,8000)],
        windows if windows is not None else[window()],source_id='s',origin=0.,end=end,initial_known=initial_known)

class ReadpointControls(unittest.TestCase):
    def test_01_first_credit_retained_once_but_missing_at_readpoint(self):
        s=calculate()['summary'];self.assertEqual(s['first_credited_audio_seconds'],.5)
        self.assertEqual(s['observed_missing_audio_seconds'],.5)
        self.assertEqual(s['classifications']['avoidable'],.5)

    def test_02_recovery_before_readpoint_means_no_actual_missing(self):
        x=calculate(rows=[row(.7,8000),row(2.3,0),row(2.4,8000)],windows=[window(end=2.4)])
        self.assertEqual(x['summary']['observed_missing_audio_seconds'],0)

    def test_03_drop_at_readpoint_is_right_continuous(self):
        x=calculate(rows=[row(.7,8000),row(2.5,0),row(2.7,8000)],windows=[window(start=2.5)])
        self.assertEqual(x['summary']['observed_missing_audio_seconds'],.5)

    def test_04_restore_at_readpoint_is_already_visible(self):
        x=calculate(rows=[row(.7,8000),row(2.3,0),row(2.5,8000)],windows=[window(end=2.5)])
        self.assertEqual(x['summary']['observed_missing_audio_seconds'],0)

    def test_05_read_after_explicit_end_is_censored_not_zero(self):
        x=calculate(rows=[row(.7,8000),row(2.3,0)],windows=[window(end=2.4,stop='service_end')],end=2.4)
        s=x['summary'];self.assertEqual(s['readpoint_censored_frontiers'],1)
        self.assertIsNone(s['fully_observed_missing_audio_seconds'])
        self.assertEqual((s['missing_audio_seconds_lower'],s['missing_audio_seconds_upper']),(0,.5))

    def test_06_last_state_persists_until_fifo_closeout(self):
        x=calculate(rows=[row(.7,8000)],windows=[],end=3.)
        self.assertEqual(x['summary']['readpoint_observed_frontiers'],1)
        self.assertEqual(x['summary']['fully_observed_missing_audio_seconds'],0)

    def test_07_service_end_endpoint_can_still_have_known_missing_state(self):
        x=calculate(rows=[row(.7,8000),row(2.3,0)],windows=[window(end=2.5,stop='service_end')],end=2.5)
        self.assertEqual(x['summary']['fully_observed_missing_audio_seconds'],.5)
        self.assertEqual(x['summary']['classifications']['avoidable'],.5)

    def test_08_noncredited_intervals_do_not_enter_previously_credited_population(self):
        for f in[frontier(D=2.1),frontier(C=8.1),frontier(D=None),frontier(C=None)]:
            x=calculate(frontiers=[f]);self.assertEqual(x['summary']['first_credited_frontiers'],0)

    def test_09_missing_initial_witness_censors_population(self):
        x=calculate(initial_known=False)
        self.assertEqual(x['summary']['readpoint_censored_frontiers'],1)
        self.assertIsNone(x['summary']['fully_observed_missing_audio_seconds'])

    def test_10_spatial_overlap_union_does_not_double_count(self):
        w1=window(low=0,high=6000);w2=window(low=4000,high=8000);w2['row_index']=2
        x=calculate(rows=[row(.7,8000),row(2.3,4000)],windows=[w1,w2])
        s=x['summary'];self.assertEqual(s['observed_missing_audio_seconds'],.25)
        self.assertEqual(s['same_root_classified_union_audio_seconds'],.25)
        self.assertEqual(s['observed_missing_frontier_weight_audio_seconds'],.5)

    def test_11_audio_tail_is_intersected_at_its_actual_weight(self):
        f1=frontier();f2=frontier(F=10000,offer=.625,D=.2,C=.4,weight=.125)
        x=calculate(frontiers=[f1,f2],rows=[row(.7,10000),row(2.3,9000)],windows=[window(low=9000,high=10000)])
        self.assertEqual(x['summary']['observed_missing_audio_seconds'],.0625)
        self.assertEqual(x['summary']['first_credited_audio_seconds'],.625)

    def test_12_boundary_truncated_window_does_not_authorize_later_root(self):
        x=calculate(rows=[row(.7,8000),row(2.3,0),row(2.4,0,'canonical')],windows=[window(end=2.4,stop='next_canonical_boundary')])
        self.assertEqual(x['summary']['observed_missing_audio_seconds'],.5)
        self.assertEqual(x['summary']['same_root_classified_union_audio_seconds'],0)
        self.assertEqual(x['summary']['unclassified_beyond_root_windows_audio_seconds'],.5)

    def test_13_classes_are_retained_and_union_may_be_nonadditive(self):
        a=window(classification='avoidable');b=window(classification='necessary');b['row_index']=2
        x=calculate(windows=[a,b]);s=x['summary']
        self.assertEqual(s['same_root_classified_union_audio_seconds'],.5)
        self.assertEqual(s['classifications']['avoidable']+s['classifications']['necessary'],1.)

    def test_14_area_union_handles_nested_and_partial_rectangles(self):
        a=dict(source_id='s',start=0,end=2,low=0,high=8000)
        b=dict(source_id='s',start=1,end=3,low=4000,high=12000)
        self.assertEqual(union_area([a,b]),1.75)

    def test_15_row_clock_mode_and_source_guards(self):
        valid=[row(.5,8000),row(1.,16000)]
        validate_rows(valid,'s',0,2,False)
        for key,value in [('source_id','other'),('consumer_retain_views',True),('observed',float('nan'))]:
            bad=copy.deepcopy(valid);bad[1][key]=value
            with self.assertRaises(ValueError):validate_rows(bad,'s',0,2,False)
        with self.assertRaises(ValueError):validate_rows(list(reversed(valid)),'s',0,2,False)

    def test_16_aggregate_keeps_censor_bounds_and_na(self):
        a=calculate()['summary'];b=calculate(rows=[row(.7,8000),row(2.3,0)],windows=[window(end=2.4,stop='service_end')],end=2.4)['summary']
        s=aggregate_readpoints([a,b]);self.assertEqual(s['first_credited_audio_seconds'],1.)
        self.assertEqual((s['missing_audio_seconds_lower'],s['missing_audio_seconds_upper']),(.5,1.))
        self.assertIsNone(s['fully_observed_missing_audio_seconds'])

    def test_17_zero_duration_population_has_explicit_empty_distribution(self):
        s=duration_statistics([]);self.assertEqual(s['n'],0);self.assertIsNone(s['median_seconds'])

    def test_18_full_positive_distribution_is_descriptive(self):
        s=duration_statistics([.03,.05,.1]);self.assertEqual(s['n'],3)
        self.assertEqual(s['median_seconds'],.05)

    def test_19_nonfinite_primary_latency_is_rejected_not_dropped(self):
        for key,value in [('D',float('nan')),('C',float('inf')),('D',True)]:
            f=frontier();f[key]=value
            with self.assertRaises(ValueError):calculate(frontiers=[f])

    def test_20_canonical_support_record_must_bind_actual_row(self):
        rows=[row(.7,8000),row(2.3,0,'canonical'),row(2.7,8000)]
        event=dict(row_index=1,source_id='s',observed=2.3,new_canonical_sha='root',
                   before_visible_frontier=8000,after_visible_frontier=0,
                   metadata_binding_checked=True,support_status='compatible_boundary')
        validate_windows(rows,[event],[],3.)
        for key,value in [('observed',2.4),('new_canonical_sha','wrong'),('before_visible_frontier',4000)]:
            bad=dict(event);bad[key]=value
            with self.assertRaises(ValueError):validate_windows(rows,[bad],[],3.)

    def test_21_gap_integrates_last_state_to_explicit_end(self):
        rows=[row(.5,16000),row(1.,8000),row(1.5,12000)]
        self.assertEqual(high_watermark_gap(rows,2.5),.5)

    def test_22_loss_rectangles_bind_actual_spatial_interval_not_just_area(self):
        rows=[row(.7,8000),row(2.3,0,'canonical'),row(2.7,8000)]
        event=dict(row_index=1,source_id='s',observed=2.3,new_canonical_sha='root',
                   before_visible_frontier=8000,after_visible_frontier=0,
                   metadata_binding_checked=True,support_status='compatible_boundary')
        w=window();w.update(owner_epoch=0,canonical_sha='root',before_visible_frontier=8000,
            after_visible_frontier=0,observed_duration_seconds=2.7-2.3,initial_removed_audio_seconds=.5,
            restored=True,observed_same_root_area_audio_seconds_x_wall_seconds=(2.7-2.3)*.5)
        validate_windows(rows,[event],[w],3.)
        w['segments'][0].update(low=8000,high=16000)
        with self.assertRaises(ValueError):validate_windows(rows,[event],[w],3.)

    def test_23_missing_difference_propagates_censor_bounds(self):
        from final_recount import readpoint_effect
        known=calculate()['summary']
        censored=calculate(rows=[row(.7,8000)],windows=[],end=2.4)['summary']
        effect=readpoint_effect(censored,known)
        self.assertIsNone(effect['point_audio_seconds'])
        self.assertEqual((effect['lower_audio_seconds'],effect['upper_audio_seconds']),(-.5,0.))

    def test_24_quality_normalization_removes_unicode_whitespace_only(self):
        from quality_recount import normalize
        self.assertEqual(normalize(' A\t中\u3000文\n\u00a0! '),'A中文!')
        self.assertNotEqual(normalize('Ａ，é'),normalize('A,e\u0301'))

    def test_25_quality_recounts_edits_and_binds_original_final_text(self):
        from quality_recount import SCOPE,verify_quality,pool_quality
        source=dict(source_id='s',reference='你 好，世界')
        q=dict(source_id='s',reference_characters=5,character_edits=2,CER=.4,final_text='你 好世界!',scope=SCOPE)
        actual=verify_quality([q],source,'你 好世界!')
        self.assertEqual(pool_quality([actual,actual])['CER'],.4)
        with self.assertRaises(ValueError):verify_quality([dict(q,character_edits=1)],source,'你 好世界!')
        with self.assertRaises(ValueError):verify_quality([q],source,'你 好世界。')

    def test_26_empty_quality_reference_is_na_and_pooled_by_characters(self):
        from quality_recount import SCOPE,verify_quality,pool_quality
        empty=dict(source_id='empty',reference=' \t')
        q=dict(source_id='empty',reference_characters=0,character_edits=1,CER=None,final_text='!',scope=SCOPE)
        verified=verify_quality([q],empty,'!')
        self.assertIsNone(pool_quality([verified])['CER'])
        with self.assertRaises(ValueError):verify_quality([dict(q,CER=0.)],empty,'!')
        other=dict(source_id='other',reference_characters=4,character_edits=1,CER=.25,final_text='test',scope=SCOPE)
        pooled=pool_quality([verified,other]);self.assertEqual(pooled['CER'],.5)

if __name__=='__main__':unittest.main()

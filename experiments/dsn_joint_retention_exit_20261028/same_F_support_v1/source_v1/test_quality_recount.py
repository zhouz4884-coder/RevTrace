"""Synthetic CPU controls for exact-F, unknown, full-text and fault semantics."""
from pathlib import Path
import hashlib,importlib.util,os,unittest
from quality_recount import partition_first_credit,worker_fault_identity,first_actual_view

class QualityRecountControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(os.environ['REVTRACE_USEFULNESS_SOURCE'])/'canonical_usefulness_v1.py'
        spec=importlib.util.spec_from_file_location('fixed_fde_controls',path);cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)
    def view(self,text='Hello world',F=64000,certified=32000):
        return dict(session_id=0,valid_visible_frontier=F,certified_frontier=certified,observed_perf=10.,visible_text=text)
    def canonical(self,text='Hello world',F=64000,selected=11.):
        return {(0,F):dict(text=text,version=1,job_id='authority',selected_perf=selected,published_perf=selected+.01,consumer_certified_perf=selected+.02)}
    def test_complete_same_F_raw_identity(self):
        result=self.module.compare_view(self.view(),self.canonical());self.assertTrue(result['raw_equal']);self.assertTrue(result['normalized_equal']);self.assertEqual(result['same_F_status'],'FUTURE_SELECTED_SAME_F')
    def test_frozen_normalizer_agreement_is_separate_from_raw(self):
        result=self.module.compare_view(self.view('HELLO, world!'),self.canonical());self.assertFalse(result['raw_equal']);self.assertTrue(result['normalized_equal'])
    def test_later_longer_snapshot_cannot_supply_missing_same_F(self):
        result=self.module.compare_view(self.view(),self.canonical('Hello world extra',F=96000))
        self.assertEqual(result['same_F_status'],'UNMATCHED_NO_SELECTED_SAME_F');self.assertIsNone(result['raw_equal']);self.assertIsNone(result['normalized_equal'])
    def test_equal_prefix_is_not_complete_same_F_agreement(self):
        result=self.module.compare_view(self.view('Hello'),self.canonical('Hello world'));self.assertFalse(result['raw_equal']);self.assertFalse(result['normalized_equal'])
    def test_already_selected_snapshot_is_not_counted_as_future(self):
        result=self.module.compare_view(self.view(),self.canonical(selected=9.));self.assertEqual(result['same_F_status'],'SELECTED_BEFORE_OR_AT_VIEW');self.assertEqual(result['selected_lead_seconds'],-1.)
    def test_offered_weight_uses_complete_visible_F_not_offered_F(self):
        actual=self.view();frontier=dict(session_id=0,frontier=32000,audio_seconds=2.,display_latency=1.,commit_view_latency=2.,dual_credit=True,first_actual_visible_perf=10.)
        views,offered=self.module.recount([actual],[frontier],self.canonical(),12.)
        self.assertEqual(offered[0]['visible_frontier'],64000);self.assertTrue(offered[0]['raw_equal']);self.assertEqual(offered[0]['frontier'],32000)
    def test_unknowns_remain_separate_and_first_credit_is_unchanged(self):
        def row(weight,status,ahead,raw,norm,credit=True):return dict(audio_seconds=weight,same_F_status=status,ahead=ahead,raw_equal=raw,normalized_equal=norm,dual_timely=credit)
        rows=[row(2.,'NOT_AHEAD',False,None,None),row(2.,'FUTURE_SELECTED_SAME_F',True,True,True),row(1.,'FUTURE_SELECTED_SAME_F',True,False,True),row(.5,'UNMATCHED_NO_SELECTED_SAME_F',True,None,None),row(10.,'NOT_OBSERVED',False,None,None,False)]
        result=partition_first_credit(rows);self.assertEqual(result['offered_audio_seconds'],15.5);self.assertEqual(result['original_dual_credited_audio_seconds'],5.5)
        self.assertEqual(result['raw']['audio_seconds']['unknown'],.5);self.assertEqual(result['raw']['audio_seconds']['first_ahead_different'],1.)
        self.assertEqual(result['normalized']['first_certified_or_same_F_agreeing_audio_seconds'],5.)
    def worker(self,override=False):
        job=dict(prompt_tokens=[1],prefix_audio_sha256='a'*64)
        if override:job['fault_actual_prompt_tokens']=[2]
        actual=[2] if override else [1]
        result=dict(execution_context_audit=dict(fault_override=override,executed_prompt_tokens=actual,executed_prompt_digest=hashlib.sha256(','.join(map(str,actual)).encode()).hexdigest(),actual_audio_sha256='a'*64),model_input_audit=dict(waveform_sha256='a'*64,declared_prompt_tokens=[1]))
        return job,result
    def test_actual_worker_fault_flag_is_preserved(self):
        job,result=self.worker(True);observed=worker_fault_identity(job,result);self.assertTrue(observed['actual_fault_override']);self.assertFalse(observed['actual_executed_prompt_equals_declared'])
    def test_missing_or_contradictory_actual_fault_flag_is_rejected(self):
        job,result=self.worker();del result['execution_context_audit']['fault_override']
        with self.assertRaises(ValueError):worker_fault_identity(job,result)
        job,result=self.worker(True);result['execution_context_audit']['fault_override']=False
        with self.assertRaises(ValueError):worker_fault_identity(job,result)
    def test_first_actual_view_allows_Canonical_coverage(self):
        old=self.view(F=32000);old['source_kind']='display';old['observed_perf']=9.
        actual=self.view(F=64000,certified=64000);actual['source_kind']='canonical-display'
        self.assertIs(first_actual_view([old,actual],0,64000),actual)
    def test_same_F_Canonical_must_select_complete_Authority(self):
        events=[dict(kind='run-start',t0_perf=0.),dict(kind='commit',session_id=0,version=1,job_id='a',audio_end_sample=64000,segment_tokens=[7],next_prompt_tokens=[8],installed=11.),dict(kind='canonical-display',session_id=0,version=1,job_id='a',audio_end_sample=64000,text='full',time=11.1)]
        workers=[dict(job=dict(job_id='a',role='proposal'),result=dict(token_ids=[7],state_tokens=[8],text='full'))]
        with self.assertRaises(ValueError):self.module.canonical_snapshots(events,workers,[])

if __name__=='__main__':unittest.main()

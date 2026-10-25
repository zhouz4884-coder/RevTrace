"""CPU event/accounting fixtures for diagnostics, not GPU research results."""
from pathlib import Path
import contextlib,io,json,tempfile,unittest
from unittest.mock import patch
import analyze_closed_diagnostics as a


def write(path,value,jsonl=False):
    path.write_text(('\n'.join(json.dumps(x) for x in value) if jsonl else json.dumps(value))+'\n',encoding='utf8')


def fixture(root,method='causal'):
    spec={'pool':'fixture','arrival':'sync','traffic':'mixed','label':method,'method':method,'repeat':0}
    C=root/a.name_for(spec);C.mkdir()
    j={'job_id':'a','session_id':0,'source_id':'source','role':'authority','contract_epoch':1,'parent':0,
       'audio_start_sample':0,'audio_end_sample':32000,'end_window':1,'audio_ready_perf':102.,
       'enqueue_perf':102.1,'ces_operation':'generate'}
    r={'started_perf':102.15,'received_perf':102.35,'hit_token_limit':False,
       '_row_receipt':{'terminal_perf':102.3,'rendered_perf':102.31,'emitted_perf':102.32}}
    identity={'sid':0,'epoch':1,'parent_version':0,'frontier_start':0,'frontier_end':32000}
    events=[{'kind':'run-start','t0_perf':100.,'time':0.}]
    if method=='causal':
        events.append({'kind':'closed-loop-observation','observed_perf':102.05,'time':2.05,
            'contexts':{'0':{'identity':identity,'released_successors':[],
                'target_context':{'private_delay_distribution':[]},'private_path':{'status':'none'}}}})
    events.append({'kind':'ces-decision','observed_perf':102.05,'time':2.075,
        'features':[{'sid':0,'window':1,'display_met':False,'display_expired':False}] if method=='causal' else [],
        'operation':'generate','sids':[0],'plan':[{'operation':'generate','sids':[0]}],
        'common_cut_sids':[0],'effective_deadlines':{'0':{'inherited_from_windows':[]}},
        'planner_wall_seconds':.02,'feature_wall_seconds':.005,'expected_current_credit_audio':2.,
        'expected_successor_credit_audio':0.,'expected_private_additional_credit_audio':0.,
        'expected_lease_seconds':.21,'expected_cut_wall_seconds':.35})
    events.extend([dict(kind='enqueue',time=2.1,eligible_perf=102.,**j),
        {'kind':'batch-dispatched','role':'authority','job_ids':['a'],'time':2.11},
        {'kind':'executor-complete','job_id':'a','time':2.35},
        {'kind':'commit','job_id':'a','session_id':0,'parent':0,'version':1,'audio_end_sample':32000,
         'audio_start_sample':0,'installed':2.4,'audio_ready':2.,'latency_seconds':.4,'time':2.4}])
    if method=='causal':
        events.append({'kind':'closed-loop-service-retired','session_id':0,'installed_perf':102.4,'time':2.4,
            'retired':[{'identity':identity,'first_seen':102.05,'actual_install_time':102.4,
                'deferrals':0,'promised_finish':None,'actual_promise_late':False,'promise_breaches':0}]})
    view={'session_id':0,'source_kind':'canonical-display','server_time':2.4,'observed':2.41,
        'observed_perf':102.41,'valid_visible_frontier':32000,'certified_frontier':32000,
        'audio_rollback_samples':0,'erased_characters':0}
    account={'batch_id':'b','job_ids':['a'],'worker_started_perf':102.15,'batch_drained_perf':102.36,
        'phases':[{'phase':'independent-generate','started_perf':102.16,'completed_perf':102.3}]}
    write(C/'config.json',{'rho':1,'fine_seconds':2,'ces_study':{'method':method}})
    write(C/'result.json',{'fine_window_accounting_complete':True,'decision':'PASS_PROTOCOL_COMPLETENESS',
        'certified_commits':1,'wall_seconds_including_arrival_and_drain':2.5,
        'CES_host_cost':{'planner_wall_seconds':.02}})
    write(C/'sessions.json',[{'session_id':0,'source_id':'source','offset':0.,'duration':2.}])
    write(C/'initial_states.json',[{'session_id':0,'state':{'audio_frontier_window':0,'checkpoint_id':0,'contract_epoch':1}}])
    write(C/'events.jsonl',events,True);write(C/'worker_records.jsonl',[{'job':j,'result':r}],True)
    write(C/'consumer.jsonl',[view],True);write(C/'worker_batch_accounting.jsonl',[account],True)
    write(C/'power_samples.json',{'samples':[{'gpu':gpu,'t':t,'power_w':10.*(gpu+1)} for gpu in (0,1) for t in (100.,102.5)]})
    return C,spec


class DiagnosticsTests(unittest.TestCase):
    def test_raw_clock_path_and_actual_host_window(self):
        with tempfile.TemporaryDirectory(prefix='cpu_diag_',dir=Path(__file__).resolve().parent) as d:
            C,spec=fixture(Path(d));tables=a.analyze_cell(C,spec)
            m=tables['CELL_METRICS'][0];p=tables['CRITICAL_PATHS'][0]
            self.assertAlmostEqual(m['Audio_Goodput_2_8'],.8)
            self.assertAlmostEqual(m['GPU_J_audio_s'],37.5)
            self.assertAlmostEqual(p['commit_latency_s'],.4)
            self.assertAlmostEqual(p['eligible_to_enqueue_s'],.1)
            self.assertAlmostEqual(p['eligible_queue_overlap_observed_authority_scheduling_s'],.05)
            self.assertAlmostEqual(m['authority_planner_wall_s'],.02)
            self.assertEqual(tables['TARGET_DEFERRALS'][0]['actual_first_batch_deferrals'],0)

    def test_baseline_without_feature_snapshot_is_not_assigned_zero_deferrals(self):
        with tempfile.TemporaryDirectory(prefix='cpu_diag_',dir=Path(__file__).resolve().parent) as d:
            C,spec=fixture(Path(d),'fine');tables=a.analyze_cell(C,spec)
            self.assertEqual(tables['TARGET_DEFERRALS'],[])
            self.assertIsNone(tables['CELL_METRICS'][0]['maximum_observed_target_deferrals'])

    def test_overlap_is_union_not_sum(self):
        self.assertEqual(a.merged_overlap(0.,5.,[(0.,3.),(2.,4.),(4.,6.)]),5.)

    def test_counts_without_explicit_safety_pass_are_not_success(self):
        report={'cells':72,'expected_cells':72,'failures':[]}
        self.assertFalse(a.safety_audit_complete(report,72))
        report['status']='PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT'
        self.assertTrue(a.safety_audit_complete(report,72))
        report['expected_cells']=48
        self.assertFalse(a.safety_audit_complete(report,72))

    def test_incomplete_energy_coverage_is_not_a_zero_cost_gain(self):
        with tempfile.TemporaryDirectory(prefix='cpu_diag_',dir=Path(__file__).resolve().parent) as d:
            C,spec=fixture(Path(d));power=a.read(C/'power_samples.json')
            for r in power['samples']:
                if r['t']==102.5:r['t']=101.
            write(C/'power_samples.json',power)
            m=a.analyze_cell(C,spec)['CELL_METRICS'][0]
            self.assertIsNone(m['GPU_J_audio_s'])
            self.assertFalse(m['strict_energy_comparison_eligible'])
            self.assertGreater(m['recorded_energy_J_audio_s_unfilled'],0.)

    def test_first_and_stable_visibility_are_separate(self):
        views=[{'observed':1.,'valid_visible_frontier':10,'certified_frontier':0},
               {'observed':1.5,'valid_visible_frontier':0,'certified_frontier':0},
               {'observed':3.,'valid_visible_frontier':10,'certified_frontier':10}]
        self.assertEqual(a.stable_visible(views,10),(1.,3.,3.,True))

    def test_group_medians_are_not_paired_changes(self):
        base={i:{'x':v} for i,v in enumerate([1.,100.,101.])}
        changed={i:{'x':v} for i,v in enumerate([2.,110.,202.])}
        result=a.paired(base,changed,'x')
        self.assertEqual(result['paired_median'],1.)
        self.assertAlmostEqual(result['treatment_group_median']/result['baseline_group_median']-1.,.1)
        self.assertEqual(result['resamples'],27)

    def test_failed_requested_cell_keeps_audio_and_recorded_paid_work(self):
        with tempfile.TemporaryDirectory(prefix='cpu_diag_',dir=Path(__file__).resolve().parent) as d:
            root=Path(d);C=root/'formal'/'fixture-sync-mixed-fine-r0';C.mkdir(parents=True)
            write(C/'sessions.json',[{'duration':2.}])
            write(C/'worker_batch_accounting.jsonl',[{'worker_started_perf':1.,'batch_drained_perf':2.}],True)
            plan=root/'plan.json';out=root/'diag'
            write(plan,{'stages':{'formal':{'expected_repeats':3,'cells':[{'pool':'fixture','arrival':'sync',
                'traffic':'mixed','label':'fine','repeat':0}]}}})
            argv=['diagnostics','--root',str(root),'--stage','formal','--output',str(out),'--plan',str(plan)]
            with patch('sys.argv',argv),contextlib.redirect_stdout(io.StringIO()):a.main()
            summary=a.read(out/'SUMMARY.json')
            self.assertEqual(summary['expected_cells'],1);self.assertEqual(summary['complete_cells'],0)
            self.assertFalse(summary['performance_claim_eligible'])
            failure=summary['failures'][0]
            self.assertEqual(failure['requested_frontiers'],1)
            self.assertEqual(failure['recorded_physical_lease_s_lower_bound'],1.)


if __name__=='__main__':unittest.main()

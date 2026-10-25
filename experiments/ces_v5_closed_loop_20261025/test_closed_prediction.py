"""CPU-only cost-clock fixtures; these are not actual model observations."""
from pathlib import Path
import dataclasses,sys,tempfile,unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime'/'src'))
import diagnose_closed_prediction as p
from test_closed_diagnostics import fixture,write
from revtrace.ces_v5_policy import V5Target,BatchOutcome

def prepare(root,verify=False):
    C,spec=fixture(root,'fine');cfg=p.read(C/'config.json')
    cfg['ces_study'].update(display_slo=2.,commit_slo=8.,calibration={
        'cost_seconds':{k:{'1':v} for k,v in [('generate',.4),('verify',.1),('fallback',.4)]},
        'v5_risk_model':{'min_bucket_samples':1,'owner_delivery_seconds':.08,
          'generation_scenarios':{'global':[{'weight':1.,'lease_ratio':1.,'row_fraction':.5}]},
          'verification_scenarios':{'global':[{'weight':1.,'original_rows':1,'failed_count':1,
            'verify_ratio':1.,'fallback_ratio':1.,'fallback_row_fraction':1.}]}}})
    rs=p.lines(C/'worker_records.jsonl');rs[0]['job']['prompt_tokens']=[]
    rs[0]['result']['completed_perf']=rs[0]['result']['_row_receipt']['rendered_perf']
    events=p.lines(C/'events.jsonl');d=next(e for e in events if e['kind']=='ces-decision')
    d.update(planned_seconds=999.,expected_cut_wall_seconds=1000.)
    if verify:
        cfg['ces_study']['method']='cost';spec.update(method='cost',label='cost')
        j=rs[0]['job'];j['ces_operation']='verify';d['operation']='verify'
        d['features']=[dataclasses.asdict(V5Target(sid=0,window=1,ready=102.,deadline=110.,
            candidate_ready=True,same_birth=False,previous_reject=False,candidate_tokens=5,
            descendant_count=0,descendant_seconds=0.,candidate_eta=None,audio_seconds=2.,interval_seconds=2.))]
        rs[0]['result']['online_verification']={'fallback_used':True,'candidate_accepted':False}
        accounts=p.lines(C/'worker_batch_accounting.jsonl')
        accounts[0]['phases'].append({'phase':'fresh-FP32-fallback','started_perf':102.3,'completed_perf':102.35,'physical_batch_rows':1})
        write(C/'worker_batch_accounting.jsonl',accounts,True)
    write(C/'config.json',cfg);write(C/'worker_records.jsonl',rs,True);write(C/'events.jsonl',events,True)
    return C,spec

class PredictionTests(unittest.TestCase):
    def test_common_cut_never_compared_to_first_lease_and_render_clock(self):
        with tempfile.TemporaryDirectory(prefix='cpu_pred_',dir=HERE) as d:
            C,spec=prepare(Path(d));bs,rs,_=p.diagnose_cell(C,spec)
            b=bs[0];r=rs[0]
            self.assertEqual(b['reported_planned_seconds_complete_cut_not_comparable'],999.)
            self.assertEqual(b['predicted_first_lease_mean_s'],.4)
            self.assertAlmostEqual(b['actual_full_worker_lease_s'],.21)
            self.assertAlmostEqual(r['actual_row_rendered_after_start_s'],.16)
            self.assertAlmostEqual(r['actual_row_terminal_after_start_s'],.15)
            self.assertEqual(b['input_scope'],'Known dispatched input shape only; baseline had no target snapshot')

    def test_actual_verify_fallback_and_full_call_cost_retained(self):
        with tempfile.TemporaryDirectory(prefix='cpu_pred_',dir=HERE) as d:
            C,spec=prepare(Path(d),True);bs,rs,scenarios=p.diagnose_cell(C,spec)
            self.assertEqual(bs[0]['actual_fallback_K'],1)
            self.assertEqual(bs[0]['predicted_fallback_K_mean'],1)
            self.assertEqual(bs[0]['actual_fallback_executed_rows'],1)
            self.assertEqual(bs[0]['predicted_first_lease_mean_s'],.5)
            self.assertEqual(scenarios[0]['reject_fraction'],1.)

    def test_shared_row_mixture_mass_and_two_row_groups(self):
        os=[BatchOutcome(.5,2.,.1,1.,.25,'fixture',(.1,.2),(1.,)),
            BatchOutcome(.5,1.,.4,.4,0.,'fixture')]
        vs=p.marginal_rows(os)
        self.assertAlmostEqual(sum(w for _,w in vs),1.)
        self.assertAlmostEqual(p.cdf(vs,.3),.375)
        self.assertEqual(p.cdf(vs,2.),1.)

    def test_real_dispatch_row_ids_must_match_selected_sessions(self):
        with tempfile.TemporaryDirectory(prefix='cpu_pred_',dir=HERE) as d:
            C,spec=prepare(Path(d));events=p.lines(C/'events.jsonl')
            next(e for e in events if e['kind']=='ces-decision')['sids']=[7]
            write(C/'events.jsonl',events,True)
            with self.assertRaises(AssertionError):p.diagnose_cell(C,spec)

if __name__=='__main__':unittest.main()

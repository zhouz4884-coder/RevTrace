"""Independent tests for mathematical repairs; CPU fixtures only."""
from pathlib import Path
import math
import random
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime/src'))
from revtrace.ces_v5_policy import (BatchOutcome,V5Target,_normalise,_row_cdf,
    _row_moments,_plan_metrics,_plans,choose_v5,predict_batch)


def row(sid=0, **updates):
    d=dict(sid=sid,window=1,ready=0.,deadline=8.,candidate_ready=True,
        same_birth=False,previous_reject=False,candidate_tokens=8,
        descendant_count=0,descendant_seconds=0.,candidate_eta=None,
        display_met=False,display_expired=False,audio_weight=2.)
    d.update(updates)
    return V5Target(**d)


def calibration():
    return {'global_reject':0.,'causal_reject':{},'cost_seconds':{
        'generate':{str(n):1.4*n for n in range(1,17)},
        'verify':{str(n):.2 for n in range(1,17)},
        'fallback':{str(n):1.4*n for n in range(1,17)},'proposal':{'1':.5}},
        'v5_risk_model':{'min_bucket_samples':1,'risk_quantile':.9,
            'generation_scenarios':{'global':[{'weight':1.,'lease_ratio':1.,'row_fraction':1.}]},
            'verification_scenarios':{'global':[{'weight':1.,'original_rows':1,'failed_count':0,
                'verify_ratio':1.,'verify_row_fraction':1.}]}}}


class MathematicalRepairTests(unittest.TestCase):
    def test_prior_counterexample_now_earns_attainable_credit(self):
        targets=[row(0,ready=-6.5,deadline=1.5,candidate_ready=False,display_expired=True),
                 row(1,ready=-1.5,deadline=6.5)]
        d=choose_v5(targets,now=0.,mode='progress',cal=calibration(),limit=2)
        self.assertEqual(d['operation'],'verify')
        self.assertEqual(d['sids'],[1])
        self.assertEqual(d['expected_credit_audio'],2.)
        self.assertEqual(sorted(s for batch in d['plan'] for s in batch['sids']),[0,1])

    def test_deadline_cdf_not_indicator_of_mean(self):
        cal=calibration();cal['cost_seconds']['generate']['2']=1.
        cal['v5_risk_model']['generation_scenarios']['global'][0].update(
            row_fraction=.5,row_fractions=[.1,.9])
        targets=[row(i,ready=-1.5,candidate_ready=False,deadline=6.5) for i in (0,1)]
        m=_plan_metrics((('generate',targets),),0.,cal,2.,{})
        self.assertEqual(m['expected_credit_audio'],2.)
        self.assertEqual(m['expected_lease_seconds'],1.)
        self.assertEqual(m['row_predictions'][0]['predicted_credit_audio'],1.)

    def test_cdf_probability_and_tardy_match_explicit_weighted_sum(self):
        out=BatchOutcome(.5,2.,.3,1.5,.25,'fixture',(.1,.3,.6),(1.2,1.8))
        samples=[(.1,.25),(.3,.25),(.6,.25),(1.2,.125),(1.8,.125)]
        times,cumulative,moments=_row_cdf(out)
        self.assertAlmostEqual(cumulative[-1],1.)
        for t in [-1.,0.,.1,.10000000001,.3,.5,.6,1.2,1.8,2.,10.]:
            p,tardy,mean=_row_moments(out,t)
            self.assertAlmostEqual(p,sum(w for x,w in samples if x<=t))
            self.assertAlmostEqual(tardy,sum(w*max(0.,x-t) for x,w in samples))
            self.assertAlmostEqual(mean,sum(w*x for x,w in samples))

    def test_no_reject_and_all_reject_distributions_keep_unit_mass(self):
        for rejected in (0.,1.):
            out=BatchOutcome(1.,2.,.2,1.5,rejected,'fixture',(.1,.2),(1.,1.5))
            _,cumulative,_=_row_cdf(out)
            self.assertAlmostEqual(cumulative[-1],1.)
            self.assertEqual(_row_moments(out,-1.)[0],0.)
            self.assertEqual(_row_moments(out,2.)[0],1.)

    def test_scenario_weight_normalisation_preserves_joint_mass(self):
        outcomes=_normalise([BatchOutcome(2.,1.,.2,.8,0.,'a'),
                             BatchOutcome(1.,2.,.4,1.5,1.,'b')])
        self.assertAlmostEqual(sum(o.weight for o in outcomes),1.)
        self.assertAlmostEqual(outcomes[0].weight,2/3)
        self.assertAlmostEqual(sum(o.weight*_row_moments(o,1.)[0] for o in outcomes),2/3)

    def test_early_row_does_not_release_physical_worker(self):
        cal=calibration();cal['cost_seconds']['generate']['1']=1.
        cal['v5_risk_model']['generation_scenarios']['global'][0].update(
            row_fraction=.1,row_fractions=[.1])
        m=_plan_metrics((('generate',[row(0)]),('generate',[row(1)])),0.,cal,2.,{})
        self.assertAlmostEqual(m['row_predictions'][0]['predicted_finish_seconds'],.1)
        self.assertAlmostEqual(m['row_predictions'][1]['predicted_finish_seconds'],1.1)
        self.assertAlmostEqual(m['expected_lease_seconds'],2.)

    def test_common_cut_wall_includes_final_owner_delivery(self):
        cal=calibration();cal['cost_seconds']['generate']['1']=1.
        cal['v5_risk_model']['owner_delivery_seconds']=.3
        m=_plan_metrics((('generate',[row(0)]),),0.,cal,2.,{})
        self.assertAlmostEqual(m['expected_lease_seconds'],1.)
        self.assertAlmostEqual(m['expected_cut_wall_seconds'],1.3)
        self.assertAlmostEqual(m['credit_per_cut_wall_second'],2/1.3)

    def test_split_candidate_family_never_discards_or_double_counts(self):
        rng=random.Random(20261023)
        for n in range(1,17):
            targets=[row(i,candidate_ready=rng.choice([True,False]),display_met=bool(i%2)) for i in range(n)]
            plans=list(_plans(targets,calibration(),0.,2.))
            self.assertTrue(plans)
            seen=set()
            for plan in plans:
                ids=[t.sid for _,rows in plan for t in rows]
                self.assertEqual(sorted(ids),list(range(n)))
                key=tuple((op,tuple(t.sid for t in rows)) for op,rows in plan)
                self.assertNotIn(key,seen);seen.add(key)
                for op,rows in plan:
                    self.assertTrue(rows)
                    self.assertIn(op,('generate','verify'))
                    if op=='verify':self.assertTrue(all(t.candidate_ready for t in rows))
            if n>=2:
                self.assertTrue(any(tuple(op for op,_ in p)==('generate','generate') for p in plans))

    def test_all_ready_targets_enable_real_verify_verify_split(self):
        plans=list(_plans([row(i) for i in range(4)],calibration(),0.,2.))
        self.assertTrue(any(tuple(op for op,_ in p)==('verify','verify') for p in plans))

    def test_actual_display_met_retains_commit_credit_only(self):
        cal=calibration();cal['cost_seconds']['generate']['1']=3.
        targets=[row(0,display_met=True,candidate_ready=False)]
        m=_plan_metrics((('generate',targets),),0.,cal,2.,{})
        self.assertEqual(m['expected_credit_audio'],2.)
        m=_plan_metrics((('generate',targets),),6.,cal,2.,{})
        self.assertEqual(m['expected_credit_audio'],0.)


if __name__=='__main__':
    unittest.main()

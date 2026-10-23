"""CPU mathematical counterexamples; no serving or GPU gain is inferred."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'runtime/src'))
from revtrace.ces_v5_policy import V5Target, choose_v5, _plan_metrics


def target(sid, ready, candidate, expired=False):
    return V5Target(sid=sid,window=1,ready=ready,deadline=ready+8.,
        candidate_ready=candidate,same_birth=False,previous_reject=False,
        candidate_tokens=8,descendant_count=0,descendant_seconds=0.,
        candidate_eta=None,display_met=False,display_expired=expired,audio_weight=2.)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--expect',choices=['initial','repaired','either'],default='either')
    args=ap.parse_args()
    cal={'global_reject':0.,'causal_reject':{},'cost_seconds':{
        'generate':{'1':1.4,'2':2.8},'verify':{'1':.2,'2':.2},
        'fallback':{'1':1.4,'2':2.8},'proposal':{'1':.5}},
        'v5_risk_model':{'min_bucket_samples':1,'risk_quantile':.9,
          'generation_scenarios':{'global':[{'weight':1.,'lease_ratio':1.,'row_fraction':1.}]},
          'verification_scenarios':{'global':[{'weight':1.,'original_rows':1,'failed_count':0,
            'verify_ratio':1.,'verify_row_fraction':1.}]}}}
    expired = target(0,-6.5,False,True)
    salvageable = target(1,-1.5,True)
    decision=choose_v5([expired,salvageable],now=0.,mode='progress',cal=cal,limit=2)
    generation_first=_plan_metrics((('generate',[expired]),('verify',[salvageable])),0.,cal,2.,{})
    verification_first=_plan_metrics((('verify',[salvageable]),('generate',[expired])),0.,cal,2.,{})
    expected={'chosen_operation':decision['operation'],
        'generation_first_credit':generation_first['expected_credit_audio'],
        'generation_first_commit_late':generation_first['expected_commit_late_audio'],
        'verification_first_credit':verification_first['expected_credit_audio'],
        'verification_first_commit_late':verification_first['expected_commit_late_audio']}
    assert expected['generation_first_credit']==0. and expected['generation_first_commit_late']==0.
    assert expected['verification_first_credit']==2. and expected['verification_first_commit_late']==2.
    if args.expect=='initial':assert decision['operation']=='generate',expected
    if args.expect=='repaired':assert decision['operation']=='verify',expected
    expected['current_policy_eliminates_counterexample']=decision['operation']=='verify'
    row_times=[.1,.9];deadline=.5
    actual=sum(t<=deadline for t in row_times)
    mean_prediction=sum(sum(row_times)/len(row_times)<=deadline for _ in row_times)
    assert actual==1 and mean_prediction==2
    cal['cost_seconds']['generate']['2']=1.
    cal['v5_risk_model']['generation_scenarios']['global'][0].update(
        row_fraction=.5,row_fractions=row_times)
    current=_plan_metrics((('generate',[target(0,-1.5,False),target(1,-1.5,False)]),),0.,cal,2.,{})
    if args.expect=='repaired':assert current['expected_credit_audio']==2.
    report={'evidence_type':'CPU_deterministic_math_counterexamples_no_GPU',
        'commit_priority_counterexample':expected,
        'row_mean_counterexample':{'row_times':row_times,'deadline':deadline,
            'actual_on_time_rows':actual,'mean_row_prediction_on_time_rows':mean_prediction,
            'current_policy_expected_audio_credit':current['expected_credit_audio'],
            'correct_audio_credit':2.},
        'interpretation':'CPU counterexamples and current-policy repair checks. They do not measure any real-workload speedup.'}
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()

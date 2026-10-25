"""CPU structural counterexamples for the frozen V5 scheduler.

Constructed service/arrival values are not measured GPU performance. The
runtime source is imported read-only and no model or remote process is used.
"""
import json
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'ces_v5_20261023/runtime'
sys.path.insert(0,str(SOURCE/'src'))
from revtrace.ces_v5_policy import V5Target,choose_v5,_plan_metrics


def row(sid,ready,**kw):
    values=dict(sid=sid,window=1,ready=ready,deadline=ready+8.,candidate_ready=False,
        same_birth=False,previous_reject=False,candidate_tokens=0,descendant_count=0,
        descendant_seconds=0.,candidate_eta=None,display_met=False,display_expired=False,
        audio_weight=2.,audio_seconds=2.,interval_seconds=2.,prompt_tokens=0)
    values.update(kw)
    return V5Target(**values)


def calibration():
    return {'global_reject':0.,'causal_reject':{},'cost_seconds':{
        'generate':{'1':1.2,'2':3.},'verify':{'1':.2,'2':.3},
        'fallback':{'1':1.2,'2':3.},'proposal':{'1':.5}},
        'v5_risk_model':{'min_bucket_samples':1,'owner_delivery_seconds':.08,
          'generation_scenarios':{'global':[{'weight':1.,'lease_ratio':1.,'row_fraction':1.}]},
          'verification_scenarios':{'global':[{'weight':1.,'original_rows':1,'failed_count':0,
              'verify_ratio':1.,'verify_row_fraction':1.}]}}}


def replanning_fixture(row_fraction):
    # Positive run clocks: all first 2-s audio windows have nonnegative session
    # offsets. The initial decision occurs at t=5 after A released at t=2.
    origin=5.;cal=calibration();old=row(0,2.,display_expired=True);now=origin;trace=[]
    cal['v5_risk_model']['generation_scenarios']['global'][0]['row_fraction']=row_fraction
    previous_delivery=None
    for step in range(6):
        arriving=row(step+1,now)
        for target in (old,arriving):
            assert target.ready<=now and target.deadline==target.ready+8.
            assert target.audio_weight==target.interval_seconds==target.audio_seconds==2.
            assert target.ready-2.>=0. # Declared session offset for its first fine window.
        if row_fraction<1. and previous_delivery is not None:
            assert previous_delivery<=now
        decision=choose_v5([old,arriving],now=now,mode='progress',cal=cal,limit=16)
        assert decision['operation']=='generate'
        assert decision['sids']==[step+1]
        assert sorted(s for batch in decision['plan'] for s in batch['sids'])==[0,step+1]
        trace.append({'now':now,'now_relative_to_initial_cut':now-origin,
            'arriving_target_ready':arriving.ready,'arriving_target_display_deadline':arriving.ready+2.,
            'arriving_target_commit_deadline':arriving.deadline,'old_target_ready':old.ready,
            'old_target_display_deadline':old.ready+2.,'audio_weight_per_target':2.,
            'executed_first_sids':decision['sids'],
            'complete_scored_plan':decision['plan'],
            'old_target_predicted_finish':decision['row_predictions'][0]['predicted_finish_seconds'],
            'old_target_commit_deadline':old.deadline})
        # Exactly the declared first physical batch finishes. The evaluated
        # suffix is not executed; a newly released target enters the next cut.
        previous_delivery=now+1.2*row_fraction+.08
        now+=1.2
    final=choose_v5([old],now=now,mode='progress',cal=cal,limit=16)
    assert final['sids']==[0]
    old_finished=now+1.2*row_fraction+.08
    assert old_finished>old.deadline
    return {'trace':trace,'old_target_completion_under_declared_fixture':old_finished,
        'completion_relative_to_initial_cut':old_finished-origin,'old_target_commit_deadline':old.deadline,
        'constructed_calibration':cal,'all_deadlines_follow_release_plus_2_and_8':True,
        'all_audio_released_and_fine_weight_2':True,'row_fraction':row_fraction,
        'owner_delivery_completes_before_next_dispatch':row_fraction<1.,
        'meaning':'Inclusion in each evaluated suffix does not reserve actual service or bound postponement.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    reference=replanning_fixture(1.)
    owner_completed=replanning_fixture(.9)
    cdf_cal=calibration();cdf_cal['cost_seconds']['generate']['2']=2.
    cdf_cal['v5_risk_model']['owner_delivery_seconds']=0.
    cdf_cal['v5_risk_model']['generation_scenarios']['global'][0].update(
        row_fraction=.5,row_fractions=[.1,.9])
    tight=row(0,3.5);loose=row(1,5.)
    modeled=_plan_metrics((('generate',[tight,loose]),),5.,cdf_cal,2.,{})['expected_credit_audio']
    # Both mappings have the identical empirical marginal row completion CDF.
    fast_tight=2.*(.2<=.5)+2.*(1.8<=2.)
    slow_tight=2.*(1.8<=.5)+2.*(.2<=2.)
    assert modeled==3. and fast_tight==4. and slow_tight==2.
    report={'evidence_type':'CPU_constructed_scheduling_counterexamples_no_GPU',
        'source_commit':subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip(),
        'policy_sha256':hashlib.sha256((SOURCE/'src/revtrace/ces_v5_policy.py').read_bytes()).hexdigest(),
        'runtime_sha256':hashlib.sha256((SOURCE/'src/revtrace/ces_runtime.py').read_bytes()).hexdigest(),
        'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'service_times_are_constructed_not_measured':True,
        'reference_common_cut_replanning':reference,
        'owner_completed_before_next_dispatch_replanning':owner_completed,
        'exchangeable_row_identity':{'predicted_audio_credit':modeled,
            'decision_time':5.,'target_releases':[tight.ready,loose.ready],
            'display_deadlines':[tight.ready+2.,loose.ready+2.],
            'commit_deadlines':[tight.deadline,loose.deadline],
            'row_completion_times':[5.2,6.8],
            'all_deadlines_follow_release_plus_2_and_8':True,
            'fast_row_has_tight_deadline_audio_credit':fast_tight,
            'slow_row_has_tight_deadline_audio_credit':slow_tight,
            'meaning':'Correct marginal row CDF cannot identify target-specific deadline success without row identity information.'}}
    if args.output:
        if args.output.exists():raise FileExistsError('Preserve previous CPU evidence')
        args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

"""Read-only CPU probes for closed-loop branch semantics; no GPU evidence."""
import argparse
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime/src'))
from revtrace.ces_v5_policy import V5Target,BatchOutcome
from revtrace.ces_closed_loop import (Identity,SuccessorObligation,TargetContext,
    ClosedLoopState,PlannerConfig,_evaluate,_private_probability,
    AncestorPrediction,_ancestor_survival_factor,_private_survival_probability)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path)
    ap.add_argument('--expect-deep',choices=['present','fixed','either'],default='either')
    args=ap.parse_args()
    target=V5Target(sid=0,window=1,ready=2.,deadline=10.,candidate_ready=False,
        same_birth=False,previous_reject=False,candidate_tokens=0,descendant_count=0,
        descendant_seconds=0.,candidate_eta=None,display_expired=True,display_met=False,
        audio_weight=2.,audio_seconds=2.,interval_seconds=2.,prompt_tokens=0)
    identity=Identity(0,1,0,'actual-root',0,32000,'declared-contract')
    def successor(window,release,remaining):
        return SuccessorObligation(window=window,frontier_end=window*32000,
            release=release,display_deadline=release+2.,commit_deadline=release+8.,
            audio_weight=2.,remaining_service_s=remaining,parent_frontier_start=(window-1)*32000,
            audio_seconds=2.*window,interval_seconds=2.,estimated_prompt_tokens=0,
            private_delay_distribution=((1.,.8),),private_path_currently_legal=True,
            direct_private_probability=0.,fallback_private_probability=0.)
    context=TargetContext(identity,successors=(successor(2,4.,.5),successor(3,6.,2.5)),
        private_path_currently_legal=True,private_delay_distribution=((1.,.8),),
        direct_private_probability=0.,fallback_private_probability=0.)
    cal={'global_reject':0.,'causal_reject':{},
        'cost_seconds':{'generate':{'1':.5},'verify':{'1':.1},'fallback':{'1':.5},'proposal':{'1':.8}},
        'contextual_cost_models':{'generate':{'coefficients':[2.,0.,-11.25,18.75,0.,0.,0.],
            'prediction_floor_s':.0001,'prediction_ceiling_s':10.}},
        'v5_risk_model':{'min_bucket_samples':1,'owner_delivery_seconds':0.,
            'generation_scenarios':{'global':[{'weight':1.,'lease_ratio':1.,'row_fraction':1.}]},
            'verification_scenarios':{'global':[{'weight':1.,'original_rows':1,'failed_count':0,'verify_ratio':1.}]}}}
    state=ClosedLoopState('CPU-audit');state.observe({0:context},6.1)
    metrics=_evaluate((('generate',(target,)),),{0:context},now=6.1,mode='causal',cal=cal,
        display_slo=2.,observed_credit_audio=0.,elapsed_seconds=6.1,state=state,
        config=PlannerConfig(),interleave=False,cache={})
    extra=metrics['expected_private_additional_credit_audio']
    if args.expect_deep=='present':assert abs(extra-2.)<1e-9,extra
    if args.expect_deep=='fixed':assert abs(extra)<1e-9,extra
    rates=TargetContext(identity,direct_private_probability=.8,fallback_private_probability=.1)
    failed=BatchOutcome(1.,1.,.2,1.,1.,'constructed-all-fallback')
    explicit,identified=_private_probability(rates,'verify',failed,True,
        direct=.8,fallback=.1,inherit_current=False)
    assert abs(explicit-.1)<1e-12 and identified
    single=BatchOutcome(1.,2.,.2,2.,0.,'CPU-root-early',(.2,),())
    ancestor=AncestorPrediction('generate',single,10.,0.,0.,0.,0.,True)
    before=_ancestor_survival_factor(ancestor,10.1)
    after=_ancestor_survival_factor(ancestor,10.5)
    assert before==1. and after==0.
    mixed=BatchOutcome(1.,2.,.55,2.,0.,'CPU-root-exchangeable',(.1,1.),())
    mixed_ancestor=AncestorPrediction('generate',mixed,10.,0.,0.,0.,0.,True)
    half=_ancestor_survival_factor(mixed_ancestor,10.5)
    assert half==.5
    before_publication=_private_survival_probability(((1.,.1),),None,now=10.,delivery=0.,
        display_deadline=10.8,ancestor_updates=[ancestor],currently_legal=True)
    illegal_before=_private_survival_probability(((1.,.1),),None,now=10.,delivery=0.,
        display_deadline=10.8,ancestor_updates=[ancestor],currently_legal=False)
    assert before_publication==1. and illegal_before==0.
    report={'evidence_type':'CPU_constructed_branch_semantics_no_GPU',
        'policy_sha256':hashlib.sha256((HERE/'runtime/src/revtrace/ces_closed_loop.py').read_bytes()).hexdigest(),
        'owner_sha256':hashlib.sha256((HERE/'runtime/src/revtrace/ces_closed_loop_owner.py').read_bytes()).hexdigest(),
        'probe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'deep_private_hazard':{'now':6.1,'current_root_completion':6.6,
            'first_successor_completion':7.1,'second_successor_completion':9.1,
            'actual_pending_private_completion_in_constructed_model':6.9,
            'second_successor_display_deadline':8.,'all_deadlines_release_plus_2_and_8':True,
            'root_retention_probability_explicitly_zero':True,
            'correct_additional_private_credit':0.,'implemented_additional_private_credit':extra,
            'explanation':'A branch that cannot survive the first root update must not become unconditionally legal again before the later parent update.'},
        'split_direct_fallback_profile':{'direct_probability':.8,'fallback_probability':.1,
            'all_rejected_Verify_expected_retention':.1,'implemented_retention':explicit},
        'first_root_row_CDF_boundary':{'known_root_update_at':10.2,
            'legal_private_at_10_1_credit_probability':before,
            'unretained_private_at_10_5_credit_probability':after,
            'exchangeable_root_updates_10_1_or_11_private_at_10_5_survival':half,
            'currently_illegal_private_before_root_is_not_buffered_for_republication':illegal_before},
        'constructed_calibration':cal,'no_runtime_mutation':True}
    if args.output:
        if args.output.exists():raise FileExistsError('Preserve earlier audit output')
        args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

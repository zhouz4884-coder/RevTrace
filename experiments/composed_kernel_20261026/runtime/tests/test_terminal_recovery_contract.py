"""CPU contract checks for the documented terminal replacement primitive."""
from dataclasses import replace
import pytest
from revtrace.dgft import (
    FeedbackTransactionState,
    build_terminal_fallback_certificate,
    commit_session_fallback,
)

def fixture():
    state=FeedbackTransactionState(session_id=7,contract_epoch=3,
        policy_version="frozen",contract_digest="contract",canonical_runtime_digest="runtime",
        checkpoint_id=2,audio_frontier_window=100,prompt_tokens=(4,5),
        stable_token_segments=((4,5),),committed_segment_ids=("forward:0",),
        checkpoint_audio_frontiers=(0,100),speculative_version=10)
    cert=build_terminal_fallback_certificate(state=state,fallback_id="recover:7",
        audio=b"complete-audio",replacement_segments=((1,2),(3,)),feedback_state_tokens=(1,2,3))
    args=dict(expected_contract_epoch=3,expected_policy_version="frozen",
        final_audio_frontier=100,replacement_segments=((1,2),(3,)),next_prompt_tokens=(1,2,3),
        fallback_id="recover:7",certificate=cert,audio=b"complete-audio",descendant_versions=(12,11))
    return state,args

def test_equal_frontier_recovery_updates_representation_and_version():
    state,args=fixture(); r=commit_session_fallback(state,**args)
    assert r.accepted
    assert r.state.audio_frontier_window==state.audio_frontier_window
    assert r.state.checkpoint_id==state.checkpoint_id+1
    assert r.state.prompt_tokens==(1,2,3)
    assert r.state.stable_token_segments==((1,2),(3,))
    assert r.state.checkpoint_audio_frontiers==(0,100,100)
    assert r.state.committed_segment_ids==("forward:0","recover:7")
    assert r.invalidated_speculative_versions==(11,12)
    assert state.prompt_tokens==(4,5)

@pytest.mark.parametrize("field,value,reason",[
    ("session_id",8,"certificate-session"),
    ("contract_digest","different","certificate-contract"),
    ("policy_version","different","certificate-policy"),
    ("parent_checkpoint_id",1,"certificate-parent"),
    ("fallback_id","different","certificate-fallback"),
    ("audio_sha256","different","certificate-audio"),
    ("replacement_segments_sha256","different","certificate-replacement"),
    ("feedback_state_sha256","different","certificate-feedback-state"),
    ("canonical_runtime_sha256","different","certificate-runtime"),
])
def test_each_bound_field_rejects_tampering_without_state_change(field,value,reason):
    state,args=fixture();args["certificate"]=replace(args["certificate"],**{field:value})
    r=commit_session_fallback(state,**args)
    assert not r.accepted and r.reason==reason and r.state is state

@pytest.mark.parametrize("field,value,reason",[
    ("expected_contract_epoch",2,"stale-epoch"),
    ("expected_policy_version","old","stale-policy"),
    ("final_audio_frontier",99,"fallback-frontier-regression"),
])
def test_operation_fences(field,value,reason):
    state,args=fixture();args[field]=value;r=commit_session_fallback(state,**args)
    assert not r.accepted and r.reason==reason and r.state is state

def test_recovery_identifier_is_consumed():
    state,args=fixture();installed=commit_session_fallback(state,**args).state
    replay=commit_session_fallback(installed,**args)
    assert not replay.accepted and replay.reason=="duplicate-segment"
    assert replay.state is installed

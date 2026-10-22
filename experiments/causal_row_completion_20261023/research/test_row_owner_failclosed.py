"""CPU fault fixtures through the real frozen owner; no model/GPU evidence."""
from pathlib import Path
import hashlib,sys
import pytest
S=Path(__file__).resolve().parent/'source_row_sdk_v2'
sys.path[:0]=[str(S/'src'),str(S/'tests')]
from test_live_qwen import build,Fake
from revtrace.dgft import CanonicalSegmentJob,build_dual_axis_certificate,commit_canonical_segment,digest_tokens

def leased_authority():
    owner=build(count=1,barrier='decoupled');owner.clock.sleep(.04)
    session=owner.sessions[0];job=owner._make_job(session,'authority');w=owner.executors['authority'][0]
    w.submit([job]);owner.inflight[w.name]=(w,[job['job_id']]);session.auth_busy=True;owner.clock.sleep(.01)
    return owner,session,job,w

def test_current_parent_change_is_rejected_in_actual_owner_receive():
    owner,s,j,w=leased_authority();before=s.state
    # A separately validated alternative state is injected to test the defensive
    # stale-result branch. This is not an allowed second concurrent writer.
    audio=s.audio[:j['audio_end_sample']*4]
    alternate=CanonicalSegmentJob(s.sid,before.contract_epoch,before.policy_version,before.checkpoint_id,
      0,j['audio_end_sample'],'legal-counterfactual-parent',digest_tokens(before.prompt_tokens),
      before.contract_digest,before.canonical_runtime_digest,hashlib.sha256(audio).hexdigest())
    certificate=build_dual_axis_certificate(job=alternate,audio=audio,display_tokens=[77],feedback_state_tokens=[77],
      canonical_runtime_digest=before.canonical_runtime_digest)
    legal=commit_canonical_segment(before,alternate,certificate=certificate,display_tokens=[77],segment_tokens=[77],next_prompt_tokens=[77])
    assert legal.accepted;s.state=legal.state
    with pytest.raises(AssertionError,match='stale result'):owner._receive()
    assert s.state==legal.state and not any(e['kind']=='commit' for e in owner.events)

def test_actual_audio_mismatch_fails_before_owner_installation():
    owner,s,j,w=leased_authority();original=w.poll
    def corrupt():
        rows=original()
        for row in rows or []:row['prefix_audio_sha256']='wrong-actual-audio'
        return rows
    w.poll=corrupt
    with pytest.raises(AssertionError,match='audio digest mismatch'):owner._receive()
    assert s.state.checkpoint_id==0 and not any(e['kind']=='commit' for e in owner.events)

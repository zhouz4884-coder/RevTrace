"""Read-only independent replay of Qwen canonical commit WAL records."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from revtrace.dgft import (CanonicalSegmentJob, DualAxisCommitCertificate,
                          FeedbackTransactionState, commit_canonical_segment,
                          digest_tokens)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode()).hexdigest()


def restore_state(value):
    fields = dict(value)
    for key in ("prompt_tokens", "committed_segment_ids", "checkpoint_audio_frontiers"):
        fields[key] = tuple(fields[key])
    fields["stable_token_segments"] = tuple(tuple(row) for row in fields["stable_token_segments"])
    return FeedbackTransactionState(**fields)


def audit(path: Path, expected_directory: Path | None = None, expected_prior_commits: int = 0):
    data = path.read_bytes()
    offset, sequence, previous = 0, 0, ""
    states, state_hashes, consumed = {}, {}, set()
    commits, restarts = 0, 0
    latest_restart_states = None
    commits_before_latest_restart = 0
    while offset < len(data):
        assert len(data)-offset >= 4, "incomplete WAL header in completed run"
        length = struct.unpack_from(">I", data, offset)[0]
        assert 0 < length <= 32*1024*1024, "invalid WAL length"
        end = offset+4+length+32
        assert end <= len(data), "incomplete WAL frame in completed run"
        payload = data[offset+4:offset+4+length]
        checksum = hashlib.sha256(payload).digest()
        assert checksum == data[offset+4+length:end], "WAL checksum mismatch"
        record = json.loads(payload)
        assert record["schema_version"] == 1, "unknown WAL schema"
        assert record["sequence"] == sequence, "WAL sequence mismatch"
        assert record["previous_sha256"] == previous, "WAL chain mismatch"
        kind = record["kind"]
        if kind == "genesis":
            assert sequence == 0 and not states, "unexpected WAL genesis"
            states = {int(sid):restore_state(value) for sid,value in record["states"].items()}
            state_hashes = {sid:digest({"genesis_state":asdict(state)})
                            for sid,state in states.items()}
            assert record["state_hashes"] == {str(k):v for k,v in state_hashes.items()}
        elif kind == "restart_epoch":
            assert record["parent_state_hashes"] == {str(k):v for k,v in state_hashes.items()}
            epoch = record["next_contract_epoch"]
            assert all(epoch == state.contract_epoch+1 for state in states.values())
            state_hashes = {sid:digest({"parent":state_hashes[sid],
                "transition":"restart_epoch","contract_epoch":epoch}) for sid in states}
            assert record["next_state_hashes"] == {str(k):v for k,v in state_hashes.items()}
            states = {sid:replace(state,contract_epoch=epoch) for sid,state in states.items()}
            latest_restart_states = {str(sid):json.loads(json.dumps(asdict(state))) for sid,state in states.items()}
            commits_before_latest_restart = commits
            restarts += 1
        elif kind == "commit":
            sid, transaction_id = record["session_id"], record["transaction_id"]
            key = (sid,transaction_id)
            assert key not in consumed, "duplicate durable transaction ID"
            state = states[sid]
            delta, event = record["state_delta"], record["event"]
            assert delta["kind"] == "canonical-segment", "unsupported Qwen state delta"
            assert event["event"] == "canonical-segment-committed"
            assert event["session_id"] == sid and event["segment_id"] == transaction_id
            assert record["parent_checkpoint_id"] == state.checkpoint_id
            assert record["parent_state_sha256"] == state_hashes[sid], "WAL parent state mismatch"
            cert = DualAxisCommitCertificate(**event["certificate"])
            start,stop = delta["audio_start_sample"],delta["audio_end_sample"]
            assert transaction_id == f"{sid}:{start}:{stop}", "unstable durable transaction ID"
            assert delta["audio_sha256"] == cert.audio_sha256
            job = CanonicalSegmentJob(sid,state.contract_epoch,state.policy_version,
                state.checkpoint_id,start,stop,transaction_id,digest_tokens(state.prompt_tokens),
                state.contract_digest,state.canonical_runtime_digest,delta["audio_sha256"])
            result = commit_canonical_segment(state,job,certificate=cert,
                display_tokens=delta["segment_tokens"],segment_tokens=delta["segment_tokens"],
                next_prompt_tokens=delta["next_prompt_tokens"],
                descendant_versions=delta["invalidated_speculative_versions"])
            assert result.accepted, result.reason
            assert result.state.speculative_version == delta["speculative_version"]
            request = {
                "kind":"canonical-segment","session_id":sid,"transaction_id":transaction_id,
                "parent_checkpoint_id":state.checkpoint_id,"audio_start_sample":start,
                "audio_end_sample":stop,"interval_audio_sha256":delta["audio_sha256"],
                "parent_prompt_digest":digest_tokens(state.prompt_tokens),
                "display_sha256":digest_tokens(delta["segment_tokens"]),
                "feedback_state_sha256":digest_tokens(delta["next_prompt_tokens"]),
                "contract_digest":state.contract_digest,"runtime_digest":state.canonical_runtime_digest,
            }
            assert record["request_sha256"] == digest(request), "WAL request binding mismatch"
            next_hash = digest({"parent":state_hashes[sid],"delta":delta})
            assert record["next_state_sha256"] == next_hash
            states[sid],state_hashes[sid] = result.state,next_hash
            consumed.add(key)
            commits += 1
        else:
            raise AssertionError(f"unknown WAL record kind {kind!r}")
        previous,sequence,offset = checksum.hex(),sequence+1,end
    assert states, "empty WAL"
    if expected_directory is not None:
        expected = json.loads((expected_directory/"result.json").read_text())
        for row in expected["final_states"]:
            observed = json.loads(json.dumps(asdict(states[row["session_id"]])))
            assert observed == row["state"], "WAL state differs from returned serving state"
        assert commits == expected["certified_commits"]+expected_prior_commits, "WAL/serving commit denominator differs"
    return {"decision":"PASS_READ_ONLY_WAL_REPLAY","commits":commits,
        "records":sequence,"restart_epochs":restarts,"trailing_bytes":0,
        "journal_sha256":hashlib.sha256(data).hexdigest(),
        "latest_restart_states":latest_restart_states,
        "commits_before_latest_restart":commits_before_latest_restart,
        "final_frontier_samples":{str(sid):state.audio_frontier_window for sid,state in states.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("journal",type=Path)
    parser.add_argument("--expected-directory",type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.journal,args.expected_directory),indent=2))

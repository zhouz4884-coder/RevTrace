"""Independently replay recorded production certificates and verify clocks."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from revtrace.dgft import (FeedbackTransactionState, CanonicalSegmentJob,
    DualAxisCommitCertificate, commit_canonical_segment, digest_tokens)
from revtrace.live_qwen import fingerprint

def audit(root, expected_evidence_type="real_gpu_wall_clock_arrival_certified_runtime"):
    config=json.loads((root/"config.json").read_text())
    result=json.loads((root/"result.json").read_text())
    specs={s["session_id"]:s for s in json.loads((root/"sessions.json").read_text())}
    events=[json.loads(line) for line in (root/"events.jsonl").read_text().splitlines()]
    cd,rd=fingerprint(config),fingerprint(config["authority_runtime"])
    states={sid:FeedbackTransactionState(sid,1,config["policy"],contract_digest=cd,
             canonical_runtime_digest=rd) for sid in specs}
    initial_file=root/"initial_states.json"
    if initial_file.exists():
        from audit_dsn_journal import restore_state
        for row in json.loads(initial_file.read_text()):
            states[row["session_id"]]=restore_state(row["state"])
        provenance=json.loads((root/"provenance.json").read_text())
        journal_path=provenance.get("durable_journal_path")
        if journal_path:
            from audit_dsn_journal import audit as audit_wal
            wal=audit_wal(Path(journal_path))
            expected=wal["latest_restart_states"]
            if expected is not None:
                assert {str(sid):json.loads(json.dumps(__import__('dataclasses').asdict(state))) for sid,state in states.items()}==expected,"resume snapshot not backed by WAL history"
            else:
                assert all(state.checkpoint_id==0 and state.audio_frontier_window==0 for state in states.values())
        else:
            assert all(state.checkpoint_id==0 and state.audio_frontier_window==0 for state in states.values())
    initial_frontiers={sid:state.audio_frontier_window for sid,state in states.items()}
    jobs,completed={},{}
    latest_generation={sid:0 for sid in specs}
    pending_retention={}
    count=0
    for e in events:
        sid=e.get("session_id")
        if e["kind"]=="enqueue":
            assert e["job_id"] not in jobs,"duplicate enqueue"
            jobs[e["job_id"]]=e
            if e["role"]=="proposal" and "branch_generation" in e:
                latest_generation[sid]=e["branch_generation"]
            assert e["enqueue_perf"]>=e["audio_ready_perf"],"future audio"
            assert e["audio_start_sample"]<e["audio_end_sample"],"parent audio exceeds job frontier"
        elif e["kind"]=="executor-complete":
            assert e["job_id"] not in completed,"duplicate execution"
            job=jobs[e["job_id"]]
            assert e["role"]==job["role"],"executor role mismatch"
            assert e["audio_ready"]<=e["enqueue"]<=e["started"]<=e["completed"]<=e["time"],"noncausal execution"
            assert abs(e["audio_ready"]-(specs[sid]["offset"]+(job["audio_end_sample"]-initial_frontiers[sid])/16000))<1e-5,"incorrect audio release"
            assert e["prefix_audio_sha256"]==job["prefix_audio_sha256"],"wrong consumed audio"
            if e["role"]=="authority" and config.get("verification_policy")=="grouped_replay":
                proof=e["verification"]
                assert proof["batch_rows"]==config.get("authority_microbatch",config["microbatch"])
                candidate=job["candidate_token_ids"]
                predicted=proof["predicted_token_ids"]
                assert len(predicted)==len(candidate)==proof["candidate_tokens"]
                matched=next((i for i,(a,b) in enumerate(zip(candidate,predicted)) if a!=b),len(candidate))
                assert matched==proof["matched_prefix_tokens"]
                assert proof["repaired"] == (matched != len(candidate))
                if not proof["repaired"] and job.get("candidate_parent_bound",True):
                    assert e["output_sha256"]==digest_tokens(job["candidate_state_tokens"])
            completed[e["job_id"]]=e
        elif e["kind"]=="display":
            assert completed[e["job_id"]]["role"]=="proposal"
            assert e["time"]>=e["displayed"]>=completed[e["job_id"]]["completed"]
            assert abs(e["latency_seconds"]-(e["displayed"]-e["audio_ready"]))<1e-7
        elif e["kind"]=="verified-private-prefix-retained":
            assert config.get("retain_verified_private_prefix")
            assert e["branch_generation"]==latest_generation[sid]
            candidates=[(jid,job) for jid,job in jobs.items() if job["role"]=="proposal"
                and job["session_id"]==sid and job["audio_end_sample"]==e["frontier"]
                and jid in completed and job.get("branch_generation")==e["branch_generation"]]
            assert len(candidates)==1,"retained prefix is not from the current private generation"
            assert e["private_window"]*config["fine_seconds"]*16000>=e["frontier"]
            pending_retention[sid]=(e,completed[candidates[0][0]]["output_sha256"])
        elif e["kind"]=="commit":
            job=jobs[e["job_id"]]
            done=completed[e["job_id"]]
            assert job["role"]==done["role"]=="authority","proposer acquired write authority"
            assert done["completed"]<=e["certified"]<=e["installed"]<=e["time"],"noncausal certificate or installation"
            assert digest_tokens(e["next_prompt_tokens"])==done["output_sha256"]
            state=states[sid]
            cert=DualAxisCommitCertificate(**e["certificate"])
            # Historical traces used executor job IDs. New traces use a stable
            # session/audio-interval ID so an execution retry cannot create a
            # second durable transition.
            segment_id=e.get("segment_id",cert.segment_id)
            if "durability_mode" in config:
                expected=f"{sid}:{job['audio_start_sample']}:{job['audio_end_sample']}"
                assert segment_id==cert.segment_id==expected,"unstable segment ID"
            else:
                assert segment_id==cert.segment_id==job["job_id"],"historical segment ID mismatch"
            j=CanonicalSegmentJob(sid,state.contract_epoch,config["policy"],job["parent"],job["audio_start_sample"],
                job["audio_end_sample"],segment_id,job["parent_prompt_digest"],cd,rd,job["interval_audio_sha256"])
            applied=commit_canonical_segment(state,j,certificate=cert,display_tokens=e["segment_tokens"],
                segment_tokens=e["segment_tokens"],next_prompt_tokens=e["next_prompt_tokens"],
                descendant_versions=e["invalidated_versions"])
            assert applied.accepted,applied.reason
            if sid in pending_retention:
                retained,projection_hash=pending_retention.pop(sid)
                assert retained["parent"]==applied.state.checkpoint_id
                assert retained["frontier"]==applied.state.audio_frontier_window
                assert projection_hash==digest_tokens(applied.state.prompt_tokens)
            assert e["parent"]==state.checkpoint_id and e["version"]==applied.state.checkpoint_id
            assert abs(e["latency_seconds"]-(e["installed"]-e["audio_ready"]))<1e-7
            replay=commit_canonical_segment(applied.state,j,certificate=cert,display_tokens=e["segment_tokens"],
                segment_tokens=e["segment_tokens"],next_prompt_tokens=e["next_prompt_tokens"])
            assert not replay.accepted,"duplicate certificate accepted on replay"
            states[sid]=applied.state; count+=1
    for s in result["final_states"]:
        actual=states[s["session_id"]]
        assert list(actual.prompt_tokens)==s["state"]["prompt_tokens"]
        assert actual.audio_frontier_window==round(specs[s["session_id"]]["duration"]*16000)
    assert count==result["certified_commits"]
    assert not pending_retention
    assert result["evidence_type"]==expected_evidence_type
    assert count==len([e for e in events if e["kind"]=="commit"])
    return {"decision":"PASS_REPLAYED_CERTIFICATES_AND_CAUSAL_CLOCKS","commits":count,
            "display_events":sum(e["kind"]=="display" for e in events),
            "certificate_replays_rejected":count,"display_p99_seconds":result["display_p99_seconds"],
            "display_slo_pass":result["display_p99_seconds"]<=2,
            "token_limit_events":result["token_limit_events"]}

if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("directory",type=Path)
    root=p.parse_args().directory
    value=audit(root)
    (root/"audit.json").write_text(json.dumps(value,indent=2)+"\n")
    print(json.dumps(value))

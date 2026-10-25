"""CPU orchestration tests, explicitly not GPU or live-service evidence."""
import hashlib
import numpy as np
import pytest
from revtrace.live_qwen import LiveQwenScheduler, fingerprint

class Clock:
    def __init__(self): self.now=100.0
    def __call__(self): return self.now
    def sleep(self,n): self.now+=n

class Fake:
    def __init__(self,name,clock,delay=.001,bad_runtime=False):
        self.name,self.clock,self.delay=name,clock,delay
        self.jobs=None
        self.batch_sizes=[]
        self.bad_runtime=bad_runtime
    def submit(self,jobs):
        assert self.jobs is None
        self.batch_sizes.append(len(jobs))
        self.jobs,self.started=jobs,self.clock()
    def poll(self):
        if self.jobs is None or self.clock()<self.started+self.delay: return None
        jobs,self.jobs=self.jobs,None
        return [{"job_id":j["job_id"],"runtime_digest":"WRONG" if self.bad_runtime else j["runtime_digest"],
            "prefix_audio_sha256":j["prefix_audio_sha256"],"started_perf":self.started,
            "completed_perf":self.clock(),"generated_tokens":1,"hit_token_limit":False,
            "text":str(j["end_window"]),"token_ids":[j["end_window"]],
            "state_tokens":[j["end_window"]+(0 if j["role"]=="authority" or getattr(self,"same_projection",False) else 999)]}
            for j in jobs]

def build(rho=3,delay=.001,bad=False,barrier="segment",*,
          durable_path=None,emit=None,count=2,journal_sync_mode="single",grouped_speculative=False,
          retain_prefix=False,same_projection=False):
    clock=Clock()
    config={"policy":"coarse","rho":rho,"fine_seconds":.01,"sample_rate":16000,
        "authority_runtime":{"dtype":"float32"},"proposal_runtime":{"dtype":"float16"},
        "microbatch":2,"timeout_seconds":2,"proposal_barrier":barrier,
        "journal_sync_mode":journal_sync_mode,
        "verification_policy":"grouped_replay" if grouped_speculative else "canonical_generate",
        "grouped_speculative":grouped_speculative,
        "retain_verified_private_prefix":retain_prefix,
        "evidence_type":"cpu_simulated_orchestration_only"}
    sessions=[{"session_id":i,"audio":np.zeros(960,dtype="<f4").tobytes(),
        "source_id":str(i),"language":"English","offset":i*.004} for i in range(count)]
    s=LiveQwenScheduler(sessions=sessions,contract=config,
        executors={"proposal":[Fake("p",clock)],"authority":[Fake("a",clock,delay,bad)]},
        clock=clock,sleep=clock.sleep,emit=emit or (lambda e:None),
        durable_journal_path=durable_path)
    s.executors["proposal"][0].same_projection=same_projection
    return s

def test_release_clock_and_complete_certified_history():
    scheduler=build()
    result=scheduler.run()
    assert result["display_events"]==12
    assert result["certified_commits"]==4
    assert result["evidence_type"]=="cpu_simulated_orchestration_only"
    for event in scheduler.events:
        if event["kind"]=="enqueue":
            assert event["enqueue_perf"]>=event["audio_ready_perf"]
        if event["kind"]=="commit":
            assert event["certificate_consumed"]
            assert max(event["next_prompt_tokens"])<999
    assert all(s.state.audio_frontier_window==960 for s in scheduler.sessions.values())
    for event in scheduler.events:
        if event["kind"] in ("display","commit"):
            key="displayed" if event["kind"]=="display" else "installed"
            assert event["latency_seconds"]==pytest.approx(event[key]-event["audio_ready"])
            assert event[key]<=event["time"]

def test_fine_baseline_certifies_every_revision():
    result=build(rho=1).run()
    assert result["display_events"]==result["certified_commits"]==12

def test_slow_authority_wait_is_not_omitted_from_latency():
    s=build(delay=.06)
    result=s.run()
    assert result["commit_p99_seconds"]>=.06
    assert any(e["enqueue_perf"]-e["audio_ready_perf"]>.02
               for e in s.events if e["kind"]=="enqueue" and e["role"]=="proposal")

def test_unexpected_executor_realization_fails_closed():
    s=build(bad=True)
    with pytest.raises(AssertionError,match="realization"):
        s.run()
    assert not any(e["kind"]=="commit" for e in s.events)
    assert all(s.state.checkpoint_id==0 for s in s.sessions.values())

def test_partial_final_window_closes_exact_audio_frontier():
    s=build()
    s.sessions[0].duration=.057
    s.sessions[0].audio=s.sessions[0].audio[:912*4]
    result=s.run()
    assert result["certified_commits"]==4
    assert s.sessions[0].state.audio_frontier_window==912

def test_decoupled_display_does_not_wait_for_slow_authority():
    s=build(delay=.06,barrier="decoupled")
    result=s.run()
    assert result["display_p99_seconds"] < .01
    assert result["commit_p99_seconds"] > .06
    assert result["certified_commits"]==4 and result["display_events"]==12
    assert all(max(row["state"]["prompt_tokens"])<999 for row in result["final_states"])

def test_fast_authority_does_not_leak_future_parent_audio_to_slow_proposals():
    s=build(barrier="decoupled")
    s.executors["proposal"][0].delay=.025
    s.run()
    for e in s.events:
        if e["kind"]=="proposal-rebase":
            assert e["parent_frontier"] < e["next_window"]*.01*16000

def test_ready_jobs_are_shared_across_idle_replicas():
    s=build(barrier="decoupled")
    s.sessions[1].offset=0
    extra=Fake("p2",s.clock)
    s.executors["proposal"].append(extra)
    result=s.run()
    assert result["display_events"]==12
    assert extra.batch_sizes and s.executors["proposal"][0].batch_sizes

def test_qwen_scheduler_resumes_from_last_fsynced_segment(tmp_path):
    path=tmp_path/"qwen-session.wal"
    class StopAfterFirstCommit(RuntimeError):
        pass
    commits=0
    def stop_after_commit(event):
        nonlocal commits
        if event["kind"]=="commit":
            commits+=1
            raise StopAfterFirstCommit("simulated caller interruption")
    first=build(count=1,durable_path=path,emit=stop_after_commit)
    with pytest.raises(StopAfterFirstCommit):
        first.run()
    assert first.sessions[0].state.audio_frontier_window==480
    first.close()

    resumed=build(count=1,durable_path=path)
    assert resumed.sessions[0].state.audio_frontier_window==480
    assert resumed.sessions[0].state.contract_epoch==2
    result=resumed.run()
    assert result["resumed_sessions"]==1
    assert result["resumed_audio_frontier_samples"]=={"0":480}
    assert result["display_events"]==3
    assert result["certified_commits"]==1
    assert resumed.sessions[0].state.audio_frontier_window==960
    assert resumed.sessions[0].state.checkpoint_id==2
    resumed.close()


def test_independent_trace_and_wal_replay_matches_serving_state(tmp_path):
    import json
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
    from audit_tc_live_qwen import audit as audit_trace
    from audit_dsn_journal import audit as audit_journal

    path=tmp_path/"state.wal"
    scheduler=build(count=1,durable_path=path)
    result=scheduler.run()
    scheduler.close()
    (tmp_path/"config.json").write_text(json.dumps(scheduler.contract))
    (tmp_path/"result.json").write_text(json.dumps(result))
    (tmp_path/"sessions.json").write_text(json.dumps([
        {"session_id":s.sid,"offset":s.offset,"duration":s.duration}
        for s in scheduler.sessions.values()]))
    (tmp_path/"events.jsonl").write_text("\n".join(json.dumps(e) for e in scheduler.events))
    with pytest.raises(AssertionError):
        audit_trace(tmp_path)  # A CPU fixture cannot pass the GPU evidence gate.
    checked=audit_trace(tmp_path,"cpu_simulated_orchestration_only")
    assert checked["commits"]==2
    before=path.read_bytes()
    assert audit_journal(path,tmp_path)["commits"]==2
    assert path.read_bytes()==before  # Inspection must not append a restart epoch.
    altered=bytearray(before)
    altered[-1]^=1
    path.write_bytes(altered)
    with pytest.raises(AssertionError,match="checksum"):
        audit_journal(path,tmp_path)


def test_ready_group_has_one_sync_barrier_and_ack_after_it(tmp_path):
    scheduler=build(durable_path=tmp_path/"group.wal",journal_sync_mode="group_ready")
    scheduler.sessions[1].offset=0
    journal=scheduler._journal
    synced=[]
    original=journal._write_frame
    def record(frame):
        original(frame)
        synced.append(journal._next_sequence)
    journal._write_frame=record
    result=scheduler.run()
    assert len(synced)==2  # two groups, each containing two independent sessions
    assert result["certified_commits"]==4
    commits=[e for e in scheduler.events if e["kind"]=="commit"]
    assert all(e["journal_group_size"]==2 for e in commits)
    assert [e["durable_journal_sequence"] for e in commits]==[1,2,3,4]
    scheduler.close()
    resumed=build(durable_path=tmp_path/"group.wal",journal_sync_mode="group_ready")
    assert all(s.state.checkpoint_id==2 for s in resumed.sessions.values())
    assert resumed.run()["certified_commits"]==0
    resumed.close()


def test_group_write_failure_cannot_publish_memory_commit(tmp_path):
    scheduler=build(durable_path=tmp_path/"failed.wal",journal_sync_mode="group_ready")
    scheduler.sessions[1].offset=0
    def fail(_frame):
        raise OSError("injected fsync failure")
    scheduler._journal._write_frame=fail
    with pytest.raises(OSError,match="fsync failure"):
        scheduler.run()
    assert all(s.state.checkpoint_id==0 for s in scheduler.sessions.values())
    assert not any(e["kind"]=="commit" for e in scheduler.events)
    scheduler.close()


def test_grouped_baseline_overlaps_private_display_and_fine_verification():
    scheduler=build(rho=1,delay=.06,barrier="decoupled",grouped_speculative=True)
    result=scheduler.run()
    assert result["display_events"]==result["certified_commits"]==12
    assert result["display_p99_seconds"]<.01
    assert result["commit_p99_seconds"]>.06
    assert all(max(row["state"]["prompt_tokens"])<999 for row in result["final_states"])
    jobs=[job for job in scheduler.jobs.values() if job["role"]=="authority"]
    assert all("candidate_token_ids" in job for job in jobs)
    assert all(not job["prompt_tokens"] or max(job["prompt_tokens"])<999 for job in jobs)
    assert any(not job["candidate_parent_bound"] for job in jobs)


def test_matching_verified_prefix_keeps_valid_private_descendants():
    scheduler=build(rho=1,delay=.04,barrier="decoupled",grouped_speculative=True,
        retain_prefix=True,same_projection=True)
    result=scheduler.run()
    kept=[e for e in scheduler.events if e["kind"]=="verified-private-prefix-retained"]
    assert kept and result["certified_commits"]==12
    assert all(e["private_window"]*.01*16000>=e["frontier"] for e in kept)
    assert all(s.branch_generation==0 for s in scheduler.sessions.values())


def test_private_prefix_retention_cannot_cross_a_rebase_generation():
    scheduler=build(rho=1,delay=.04,barrier="decoupled",grouped_speculative=True,
        retain_prefix=True,same_projection=True)
    original=scheduler._finish_commit
    def changed_generation(s,*args,**kwargs):
        s.branch_generation+=1
        return original(s,*args,**kwargs)
    scheduler._finish_commit=changed_generation
    scheduler.run()
    assert not any(e["kind"]=="verified-private-prefix-retained" for e in scheduler.events)

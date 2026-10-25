"""Arrival-driven Qwen feedback serving with real DGFT commit validation.

The scheduler owns committed state. Executors receive immutable jobs; only an
authority completion can reach commit_canonical_segment. The same event loop
is testable with CPU executors, whose outputs are explicitly not GPU evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .dgft import (CanonicalSegmentJob, FeedbackTransactionState,
                   build_dual_axis_certificate, commit_canonical_segment,
                   digest_tokens)
from .durable_journal import DurableCommitJournal


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("empty latency population")
    xs = sorted(values)
    x = (len(xs)-1)*q
    lo = int(x)
    hi = min(lo+1, len(xs)-1)
    return xs[lo] + (xs[hi]-xs[lo])*(x-lo)


@dataclass
class Session:
    sid: int
    duration: float
    offset: float
    language: str
    audio: bytes
    source_id: str
    state: FeedbackTransactionState
    fine_window: int = 1
    branch_tokens: tuple[int, ...] = ()
    branch_chunk: int = 0
    branch_parent: int = 0
    branch_root_tokens: tuple[int, ...] = ()
    branch_root_frontier: int = 0
    fine_busy: bool = False
    auth_busy: bool = False
    auth_result: dict | None = None
    fine_end_result: dict | None = None
    segment_start: int = 0
    segment_end: int = 0
    text: str = ""
    done: bool = False
    auth_done: bool = False
    resume_frontier_sample: int = 0
    resumed_start_window: int = 0
    branch_generation: int = 0
    display_revision: int = 0
    visible_frontier: int = 0
    display_ever_frontier: int = 0
    visible_text: str = ""
    canonical_display_version: int = 0
    canonical_display_text: str = ""
    state_available_perf: float = 0.


class LiveQwenScheduler:
    """Single-owner event loop: receive, validate and replace are serialized."""

    def __init__(self, *, sessions: list[dict], contract: dict,
                 executors: dict[str, list[Any]], emit: Callable[[dict], None],
                 clock=time.perf_counter, sleep=time.sleep,
                 durable_journal_path: str | Path | None = None, trusted_render=None):
        contract = dict(contract)
        durability_mode = "wal" if durable_journal_path is not None else "volatile"
        configured_durability = contract.setdefault("durability_mode", durability_mode)
        if configured_durability != durability_mode:
            raise ValueError("durability_mode must match durable_journal_path")
        self.trusted_render=trusted_render
        self.text_binding=contract.get("trusted_text_binding",False)
        if self.text_binding and not callable(trusted_render):raise ValueError("trusted renderer required")
        if self.text_binding and contract.get('evidence_type','').startswith('real_gpu') and not contract['authority_runtime'].get('render_contract'):raise ValueError('real GPU render contract assets must be pinned')
        self.contract = contract
        self.contract_digest = fingerprint(contract)
        self.runtime_digest = fingerprint(contract["authority_runtime"])
        self.fine = float(contract["fine_seconds"])
        self.rho = int(contract["rho"])
        self.reconciliation = contract.get("proposal_reconciliation", "legacy")
        if self.reconciliation not in ("legacy", "lazy"):
            raise ValueError("unknown proposal reconciliation policy")
        if (self.reconciliation != "legacy" and
                contract.get("verification_policy") == "grouped_replay"):
            raise ValueError("lazy policy currently requires independent authority generation")
        self.window_outcomes: dict[tuple[int, int], str] = {}
        self.sample_rate = int(contract.get("sample_rate", 16000))
        if self.fine <= 0 or self.rho < 1:
            raise ValueError("invalid granularity")
        self.executors, self.emit = executors, emit
        if not executors.get("proposal") or not executors.get("authority"):
            raise ValueError("both executor lanes are required")
        self.clock, self.sleep = clock, sleep
        self.t0 = self.clock()
        self.jobs: dict[str, dict] = {}
        self.inflight: dict[str, tuple[Any, list[str]]] = {}
        self.sequence = 0
        self._proposal_results = {}
        self.events: list[dict] = []
        self._event("run-start", t0_perf=self.t0, contract_digest=self.contract_digest)
        self._wal_active=False
        self._blocking_observer=None
        self.sessions = {}
        session_specs = list(sessions)
        initial_states = [
            FeedbackTransactionState(
                int(spec["session_id"]), 1, contract["policy"],
                contract_digest=self.contract_digest,
                canonical_runtime_digest=self.runtime_digest,
            )
            for spec in session_specs
        ]
        recovery_started=time.perf_counter()
        self._journal = (
            DurableCommitJournal(durable_journal_path, initial_states)
            if durable_journal_path is not None else None
        )
        self.journal_recovery_seconds=time.perf_counter()-recovery_started
        restored_states = {
            state.session_id: state for state in
            (self._journal.states() if self._journal is not None else initial_states)
        }
        restored_text: dict[int, str] = {}
        if self._journal is not None:
            for event in self._journal.events():
                if (event.get("event") == "canonical-segment-committed"
                        and "committed_text" in event):
                    if self.text_binding:
                        from .certified_display import replay_bound_text
                        try:replay_bound_text(self.trusted_render,event)
                        except BaseException:
                            self._journal.close()
                            raise
                    restored_text[int(event["session_id"])] = str(event["committed_text"])
        chunk_samples = int(round(self.fine * self.sample_rate))
        for spec in session_specs:
            sid = int(spec["session_id"])
            audio = spec["audio"]
            duration = len(audio)/(4*self.sample_rate)
            if duration <= 0 or sid in self.sessions or spec["offset"] < 0:
                raise ValueError("invalid or duplicate session")
            state = restored_states[sid]
            total_samples = len(audio) // 4
            if state.audio_frontier_window > total_samples:
                raise ValueError("journal frontier exceeds this session's audio")
            session = Session(sid, duration, float(spec["offset"]),
                spec["language"], audio, spec["source_id"], state)
            session.state_available_perf=self.t0
            session.text = restored_text.get(sid, "")
            frontier = state.audio_frontier_window
            session.resume_frontier_sample = frontier
            if frontier == total_samples:
                start_window = math.ceil(duration / self.fine)
                session.segment_start = start_window
                session.resumed_start_window = start_window
                session.auth_done = True
                session.done = True
            else:
                if frontier % chunk_samples:
                    raise ValueError("journal frontier is not on a fine-window boundary")
                start_window = frontier // chunk_samples
                session.resume_frontier_sample = frontier
                session.resumed_start_window = start_window
                session.segment_start = start_window
                session.fine_window = start_window + 1
                session.branch_tokens = state.prompt_tokens
                session.branch_chunk = start_window
                session.branch_parent = state.checkpoint_id
                session.branch_root_tokens = state.prompt_tokens
                session.branch_root_frontier = frontier
            self.sessions[sid] = session
            if not session.done:
                self._begin_segment(session)
            if self._journal is not None and state.checkpoint_id:
                self._event("state-recovered", session_id=sid,
                    checkpoint_id=state.checkpoint_id,
                    frontier=state.audio_frontier_window,
                    contract_epoch=state.contract_epoch,
                    committed_segment_count=len(state.committed_segment_ids))
                if self.contract.get('display_protocol')=='canonical-snapshot-v1':
                    self._publish_display(session,canonical=True,text=session.text,
                        frontier=frontier,job_id=None,transaction_id=state.committed_segment_ids[-1],recovered=True)
        if self.contract.get('blocking_instrumentation',False):
            from .blocking_observer import BlockingObserver
            self._blocking_observer=BlockingObserver(self)
        if self._journal is not None and self.contract.get('diagnostic_lifecycle',True):
            self._journal.timing_hook=self._journal_timing

    def _journal_timing(self,phase,started,completed):
        if self.contract.get('blocking_instrumentation',False):
            if self.contract.get('evidence_type','').startswith('real_gpu'):
                self._event('wal-physical-timing',phase=phase,started=started-self.t0,completed=completed-self.t0)
            else:
                self._event('wal-host-clock-fixture',phase=phase,host_started=started,host_completed=completed,
                    host_elapsed=completed-started,clock_domain='real host perf_counter, separate from simulated owner clock')

    def _publish_display(self,s,*,canonical,text,frontier,job_id,transaction_id=None,recovered=False,**fields):
        if self.text_binding:
            from .certified_display import text_sha
            fields.update(text_sha256=text_sha(text),canonical_projection_sha256=digest_tokens(s.state.prompt_tokens),
                canonical_Z_sha256=digest_tokens(s.state.stable_token_segments[-1]) if s.state.stable_token_segments else None,
                contract_epoch=s.state.contract_epoch,contract_digest=self.contract_digest)
            if not canonical:
                j=self.jobs[job_id];r=self._proposal_results[s.sid,j['end_window']]
                fields.update(input_projection_sha256=digest_tokens(j['prompt_tokens']),output_projection_sha256=digest_tokens(r['state_tokens']),chunk_id=j['chunk_id'],end_window=j['end_window'],branch_generation=j['branch_generation'])
        published=self.clock()-self.t0
        if 'audio_ready' in fields:fields['latency_seconds']=published-fields['audio_ready']
        prior_frontier,prior_text=s.visible_frontier,s.visible_text
        s.display_revision+=1;s.visible_frontier=frontier
        s.display_ever_frontier=max(s.display_ever_frontier,frontier);s.visible_text=text
        if canonical:s.canonical_display_version=s.state.checkpoint_id;s.canonical_display_text=text
        common=0
        for a,b in zip(prior_text,text):
            if a!=b:break
            common+=1
        return self._event('canonical-display' if canonical else 'display',session_id=s.sid,
            job_id=job_id,displayed=published,text=text,provisional=not canonical,
            audio_end_sample=frontier,version=s.state.checkpoint_id,transaction_id=transaction_id,
            display_revision=s.display_revision,canonical_version=s.canonical_display_version,
            canonical_snapshot=s.canonical_display_text,visible_frontier=frontier,
            display_ever_frontier=s.display_ever_frontier,audio_rollback_samples=max(0,prior_frontier-frontier),
            erased_characters=len(prior_text)-common,protocol='versioned-full-snapshot-no-token-audio-patch',
            recovered=recovered,**fields)

    def _event(self, kind: str, **fields) -> dict:
        row = {"kind": kind, "time": self.clock()-self.t0, **fields}
        self.events.append(row)
        self.emit(row)
        return row

    def _end_seconds(self, s: Session, window: int) -> float:
        return min(window*self.fine, s.duration)

    def _ready_time(self, s: Session, window: int) -> float:
        available_after_restart = max(
            0.0, self._end_seconds(s, window)
            - s.resume_frontier_sample / self.sample_rate
        )
        return self.t0 + s.offset + available_after_restart

    def _begin_segment(self, s: Session):
        total = math.ceil(s.duration/self.fine)
        s.segment_end = min(total, s.segment_start+self.rho)
        if self.contract.get("proposal_barrier", "segment") == "segment":
            s.branch_generation += 1
            s.fine_window = s.segment_start+1
            s.branch_tokens = s.state.prompt_tokens
            s.branch_chunk = s.segment_start
            s.branch_parent = s.state.checkpoint_id
            s.branch_root_tokens = s.state.prompt_tokens
            s.branch_root_frontier = s.state.audio_frontier_window
        s.auth_result = s.fine_end_result = None
        self._event("segment-parent", session_id=s.sid,
                    parent=s.state.checkpoint_id, frontier=s.state.audio_frontier_window,
                    prompt_digest=digest_tokens(s.state.prompt_tokens),
                    start_window=s.segment_start, end_window=s.segment_end)

    def _make_job(self, s: Session, role: str) -> dict:
        window = s.fine_window if role == "proposal" else s.segment_end
        end = self._end_seconds(s, window)
        start_sample = s.state.audio_frontier_window
        end_sample = min(int(round(end*self.sample_rate)), len(s.audio)//4)
        ready = self._ready_time(s, window)
        if self.clock()+1e-8 < ready:
            raise AssertionError("future audio dispatch")
        self.sequence += 1
        jid = f"{role}-{s.sid}-{self.sequence}"
        if (role == "proposal" and s.state.checkpoint_id > s.branch_parent
                and s.state.audio_frontier_window < end_sample):
            # Rebase only when the committed audio precedes this display job.
            # A late proposal must not read a parent containing newer audio.
            s.branch_tokens = s.state.prompt_tokens
            s.branch_generation += 1
            s.branch_chunk = min(s.segment_start, window-1)
            s.branch_parent = s.state.checkpoint_id
            s.branch_root_tokens = s.state.prompt_tokens
            s.branch_root_frontier = s.state.audio_frontier_window
            self._event("proposal-rebase", session_id=s.sid,
                        parent=s.branch_parent, next_window=window,
                        parent_frontier=s.state.audio_frontier_window)
        tokens = s.branch_tokens if role == "proposal" else s.state.prompt_tokens
        if role == "proposal":
            start_sample = s.branch_root_frontier
        chunk = s.branch_chunk if role == "proposal" else s.segment_start
        job = {"job_id": jid, "session_id": s.sid, "role": role,
            "contract_epoch":s.state.contract_epoch,
            "source_id": s.source_id, "language": s.language,
            "parent": s.branch_parent if role == "proposal" else s.state.checkpoint_id,
            "parent_prompt_digest": digest_tokens(s.branch_root_tokens if role == "proposal" else s.state.prompt_tokens),
            "prompt_tokens": list(tokens), "chunk_id": chunk,
            "chunk_advance": window-chunk, "end_window": window,
            "audio_start_sample": start_sample, "audio_end_sample": end_sample,
            "audio_ready_perf": ready, "enqueue_perf": self.clock(),
            "contract_digest": self.contract_digest,
            "runtime_digest": self.runtime_digest if role == "authority" else
                              fingerprint(self.contract["proposal_runtime"]),
            "prefix_audio_sha256": hashlib.sha256(s.audio[:end_sample*4]).hexdigest(),
            "interval_audio_sha256": hashlib.sha256(s.audio[start_sample*4:end_sample*4]).hexdigest()}
        if role == "authority" and self.contract.get("verification_policy") == "grouped_replay":
            candidate = self._proposal_results.get((s.sid,s.segment_end))
            if candidate is None:
                raise AssertionError("grouped verifier requires a completed candidate")
            proposal_job = self.jobs[candidate["job_id"]]
            parent_bound=(digest_tokens(proposal_job["prompt_tokens"])==digest_tokens(s.state.prompt_tokens))
            if not self.contract.get("grouped_speculative",False) and (proposal_job["parent"] != s.state.checkpoint_id
                    or proposal_job["parent_prompt_digest"] != digest_tokens(s.state.prompt_tokens)
                    or proposal_job["audio_end_sample"] != end_sample):
                raise AssertionError("candidate was not rooted at the verifier's parent/frontier")
            if proposal_job["audio_end_sample"] != end_sample:
                raise AssertionError("candidate audio frontier mismatch")
            job["candidate_parent_bound"] = parent_bound
            job["candidate_token_ids"] = list(candidate["token_ids"])
            job["candidate_state_tokens"] = list(candidate["state_tokens"])
            job["candidate_text"] = candidate["text"]
        self.jobs[jid] = job
        if role=="proposal":
            job["branch_generation"]=s.branch_generation
        diagnostics={}
        if self.contract.get('diagnostic_lifecycle',True):
            diagnostics={'eligible_perf':max(ready,s.state_available_perf) if role=='authority' else None,
                         'declared_prompt_tokens':list(tokens)}
        self._event("enqueue", **{k: v for k, v in job.items() if k != "prompt_tokens"},**diagnostics)
        return job

    def _ready(self, role: str):
        now = self.clock()
        eligible = []
        for s in self.sessions.values():
            if s.done:
                continue
            if role == "proposal":
                if not s.fine_busy:
                    self._reconcile_covered_windows(s)
                limit = s.segment_end if self.contract.get("proposal_barrier", "segment") == "segment" else math.ceil(s.duration/self.fine)
                if s.fine_busy or s.fine_window > limit:
                    continue
                window = s.fine_window
            else:
                if s.auth_done or s.auth_busy or s.auth_result is not None:
                    continue
                if self.contract.get("verification_policy") == "grouped_replay" and (s.sid,s.segment_end) not in self._proposal_results:
                    continue
                window = s.segment_end
            ready = self._ready_time(s, window)
            if now >= ready:
                eligible.append((ready, s.sid, s))
        return [s for _, _, s in sorted(eligible)]

    def _account_window(self, s: Session, window: int, outcome: str):
        key = (s.sid, window)
        if key in self.window_outcomes:
            raise AssertionError("fine window accounted twice")
        self.window_outcomes[key] = outcome

    def _reconcile_covered_windows(self, s: Session):
        """Lazy single-flight reconciliation; never alters committed state."""
        if (self.reconciliation != "lazy" or s.fine_busy or
                self.contract.get("proposal_barrier", "segment") != "decoupled"):
            return
        total = math.ceil(s.duration/self.fine)
        if self.contract.get('async_implementation')=='standard':
            from .standard_safe_async import covered_indices
            ends=[min(round(self._end_seconds(s,w)*self.sample_rate),len(s.audio)//4) for w in range(1,total+1)]
            for w in covered_indices(s.fine_window,ends,s.state.audio_frontier_window):
                self._account_window(s,w,'covered-without-dispatch')
                self._event('proposal-skip',session_id=s.sid,window=w,audio_end_sample=ends[w-1],committed_frontier=s.state.audio_frontier_window,reason='target-already-committed')
                s.fine_window=w+1
            return
        while s.fine_window <= total:
            target = min(round(self._end_seconds(s, s.fine_window)*self.sample_rate),
                         len(s.audio)//4)
            if target > s.state.audio_frontier_window:
                break
            self._account_window(s, s.fine_window, "covered-without-dispatch")
            self._event("proposal-skip", session_id=s.sid, window=s.fine_window,
                        audio_end_sample=target,
                        committed_frontier=s.state.audio_frontier_window,
                        reason="target-already-committed")
            s.fine_window += 1
        # _make_job performs the existing eligible-parent rebase only when
        # the next actual dispatch lies strictly beyond this committed root.

    def _dispatch(self):
        for role, workers in self.executors.items():
            idle = [w for w in workers if w.name not in self.inflight]
            if not idle:
                continue
            batch_limit=self.contract.get("authority_microbatch",self.contract["microbatch"]) if role=="authority" else self.contract["microbatch"]
            share = min(int(batch_limit),
                        max(1, math.ceil(len(self._ready(role))/len(idle))))
            for worker in idle:
                ready = self._ready(role)[:share]
                if not ready:
                    continue
                jobs = [self._make_job(s, role) for s in ready]
                for s in ready:
                    if role == "proposal":
                        s.fine_busy = True
                    else:
                        s.auth_busy = True
                worker.submit(jobs)
                self.inflight[worker.name] = (worker, [j["job_id"] for j in jobs])
                if self.contract.get('blocking_instrumentation',False):
                    self._event('batch-dispatched',worker=worker.name,role=role,job_ids=[j['job_id'] for j in jobs])

    def _receive(self):
        for name, (worker, ids) in list(self.inflight.items()):
            results = worker.poll()
            if hasattr(worker,'drain_telemetry'):
                for item in worker.drain_telemetry():
                    self._event('worker-status',worker=name,status=item['kind'],
                        **{k:v for k,v in item.items() if k!='kind'})
            if results is None:
                continue
            if getattr(worker,'row_delivery',False):
                if not {r['job_id'] for r in results}.issubset(set(ids)):
                    raise AssertionError('partial row is outside leased batch')
                if worker.batch_drained:del self.inflight[name]
            else:
                if sorted(r["job_id"] for r in results) != sorted(ids):
                    raise AssertionError("executor result set mismatch")
                del self.inflight[name]
            for result in results:
                job = self.jobs[result["job_id"]]
                s = self.sessions[job["session_id"]]
                if result["runtime_digest"] != job["runtime_digest"]:
                    raise AssertionError("executor realization mismatch")
                if result["prefix_audio_sha256"] != job["prefix_audio_sha256"]:
                    raise AssertionError("executor audio digest mismatch")
                stamps = (job["audio_ready_perf"], job["enqueue_perf"],
                          result["started_perf"], result["completed_perf"], self.clock())
                if any(a > b+1e-7 for a, b in zip(stamps, stamps[1:])):
                    raise AssertionError("noncausal timestamps")
                if job["role"] == "authority" and job["parent"] != s.state.checkpoint_id:
                    raise AssertionError("stale result must not enter branch or state")
                owner_received=self.clock()
                if self.text_binding:
                    from .certified_display import validate_bound_text
                    render_started=time.perf_counter()
                    result['text_binding']=validate_bound_text(self.trusted_render,job,result)
                    self._event('render-checked',job_id=job['job_id'],session_id=s.sid,role=job['role'],host_cpu_wall_seconds=time.perf_counter()-render_started,text_sha256=result['text_binding']['text_sha256'])
                result["received_perf"] = owner_received
                self._event("executor-complete", job_id=job["job_id"],
                    session_id=s.sid, role=job["role"], worker=name,
                    audio_ready=job["audio_ready_perf"]-self.t0,
                    enqueue=job["enqueue_perf"]-self.t0,
                    started=result["started_perf"]-self.t0,
                    completed=result["completed_perf"]-self.t0,
                    gpu_model_started=None if result.get('model_started_perf') is None else result['model_started_perf']-self.t0,
                    gpu_model_completed=None if result.get('model_completed_perf') is None else result['model_completed_perf']-self.t0,
                    received=result['received_perf']-self.t0,
                    prefix_audio_sha256=result["prefix_audio_sha256"],
                    output_sha256=digest_tokens(result["state_tokens"]),
                    generated_tokens=result["generated_tokens"],
                    hit_token_limit=result["hit_token_limit"],
                    verification=result.get("verification"))
                if self.contract.get('capture_worker_records',False):
                    self._event('worker-record',job=job,result=result)
                if job["role"] == "proposal":
                    s.fine_busy = False
                    obsolete = job["audio_end_sample"] <= s.state.audio_frontier_window
                    invalid_generation = job.get("branch_generation", 0) != s.branch_generation
                    expired=obsolete or invalid_generation
                    if self.contract.get('async_implementation')=='standard':
                        from .standard_safe_async import expired as conventional_expired
                        expired=conventional_expired(job['audio_end_sample'],job.get('branch_generation',0),s.state.audio_frontier_window,s.branch_generation)
                    if self.reconciliation == "lazy" and expired:
                        self._account_window(s, job["end_window"], "obsolete-completion")
                        self._event("proposal-obsolete", session_id=s.sid,
                            job_id=job["job_id"], window=job["end_window"],
                            audio_end_sample=job["audio_end_sample"],
                            committed_frontier=s.state.audio_frontier_window,
                            invalid_generation=invalid_generation,
                            job_generation=job.get("branch_generation"),
                            active_generation=s.branch_generation,
                            job_execution_seconds=result['completed_perf']-result['started_perf'],
                            reason="covered-target" if obsolete else "invalid-generation")
                        s.fine_window = max(s.fine_window, job["end_window"]+1)
                        self._reconcile_covered_windows(s)
                        continue
                    self._proposal_results[(s.sid,job["end_window"])]=result
                    s.branch_tokens = tuple(result["state_tokens"])
                    s.branch_chunk = job["end_window"]
                    s.fine_window += 1
                    self._account_window(s, job["end_window"], "provisional-display")
                    displayed = self.clock()
                    if self.contract.get('display_protocol')=='canonical-snapshot-v1':
                        self._publish_display(s,canonical=False,text=result['text'],frontier=job['audio_end_sample'],
                            job_id=job['job_id'],window=job['end_window'],parent=job['parent'],
                            audio_ready=job['audio_ready_perf']-self.t0,latency_seconds=displayed-job['audio_ready_perf'],
                            parent_superseded=job['parent']!=s.state.checkpoint_id)
                    else:self._event("display", session_id=s.sid, job_id=job["job_id"],
                        window=job["end_window"], parent=job["parent"],
                        audio_ready=job["audio_ready_perf"]-self.t0,
                        displayed=displayed-self.t0,
                        latency_seconds=displayed-job["audio_ready_perf"],
                        text=result["text"], provisional=True,
                        parent_superseded=job["parent"]!=s.state.checkpoint_id)
                    if job["end_window"] == s.segment_end:
                        s.fine_end_result = result
                else:
                    s.auth_busy = False
                    s.auth_result = result

    def _commit_ready(self):
        pending = []
        for s in self.sessions.values():
            if s.done or s.auth_done or s.auth_result is None:
                continue
            if self.contract.get("proposal_barrier", "segment") == "segment" and s.fine_end_result is None:
                continue
            result = s.auth_result
            job = self.jobs[result["job_id"]]
            transaction_id = (
                f"{s.sid}:{job['audio_start_sample']}:{job['audio_end_sample']}"
            )
            authority = CanonicalSegmentJob(s.sid, s.state.contract_epoch,
                self.contract["policy"], job["parent"],
                job["audio_start_sample"], job["audio_end_sample"],
                transaction_id, job["parent_prompt_digest"],
                self.contract_digest, self.runtime_digest, job["interval_audio_sha256"])
            before = s.state
            tokens = tuple(result["state_tokens"])
            cert = build_dual_axis_certificate(job=authority,
                audio=s.audio[job["audio_start_sample"]*4:job["audio_end_sample"]*4],
                display_tokens=result["token_ids"], feedback_state_tokens=tokens,
                canonical_runtime_digest=result["runtime_digest"])
            certified = self.clock()
            install = commit_canonical_segment(before, authority, certificate=cert,
                display_tokens=result["token_ids"], segment_tokens=result["token_ids"],
                next_prompt_tokens=tokens,
                descendant_versions=range(before.speculative_version+1,
                    before.speculative_version+max(1,s.fine_window-s.segment_start)+1))
            if not install.accepted:
                self._event("rejected", session_id=s.sid, reason=install.reason)
                raise AssertionError(f"live commit rejected: {install.reason}")
            durable_sequence = None
            durable_fsync_seconds = None
            if self._journal is not None:
                durable_event = {
                    "event": "canonical-segment-committed",
                    "session_id": s.sid,
                    "segment_id": transaction_id,
                    "parent_checkpoint_id": before.checkpoint_id,
                    "checkpoint_id": install.state.checkpoint_id,
                    "audio_start_sample": job["audio_start_sample"],
                    "audio_end_sample": job["audio_end_sample"],
                    "invalidated_speculative_versions": list(
                        install.invalidated_speculative_versions
                    ),
                    "certificate_consumed": True,
                    "certificate": asdict(cert),
                    "committed_text": result["text"],
                    "text_binding": result.get("text_binding"),
                }
                request_sha = fingerprint({
                    "kind": "canonical-segment",
                    "session_id": s.sid,
                    "transaction_id": transaction_id,
                    "parent_checkpoint_id": before.checkpoint_id,
                    "audio_start_sample": job["audio_start_sample"],
                    "audio_end_sample": job["audio_end_sample"],
                    "interval_audio_sha256": job["interval_audio_sha256"],
                    "parent_prompt_digest": job["parent_prompt_digest"],
                    "display_sha256": digest_tokens(result["token_ids"]),
                    "feedback_state_sha256": digest_tokens(tokens),
                    "contract_digest": self.contract_digest,
                    "runtime_digest": self.runtime_digest,
                })
                transition = dict(
                    session_id=s.sid, transaction_id=transaction_id,
                    request_sha256=request_sha, parent_state=before,
                    next_state=install.state, event=durable_event,
                )
                if self.contract.get("journal_sync_mode", "single") == "group_ready":
                    pending.append((s, result, job, transaction_id, cert, certified,
                                    install, transition))
                    continue
                self._wal_active=True
                if self._blocking_observer:self._blocking_observer.update(force=True)
                if self.contract.get('diagnostic_lifecycle',True):self._event('wal-owner-start',job_ids=[job['job_id']])
                try:durable_sequence, durable_fsync_seconds = self._journal.commit_transition(**transition)
                finally:
                    self._wal_active=False
                    if self._blocking_observer:self._blocking_observer.update(force=True)
                if self.contract.get('diagnostic_lifecycle',True):self._event('wal-owner-complete',job_ids=[job['job_id']])
            self._finish_commit(s, result, job, transaction_id, cert, certified,
                                install, durable_sequence, durable_fsync_seconds)
        if pending:
            self._wal_active=True
            if self._blocking_observer:self._blocking_observer.update(force=True)
            if self.contract.get('diagnostic_lifecycle',True):self._event('wal-owner-start',job_ids=[item[2]['job_id'] for item in pending])
            try:outcomes = self._journal.commit_transitions([item[-1] for item in pending])
            finally:
                self._wal_active=False
                if self._blocking_observer:self._blocking_observer.update(force=True)
            if self.contract.get('diagnostic_lifecycle',True):self._event('wal-owner-complete',job_ids=[item[2]['job_id'] for item in pending])
            for item, (sequence, elapsed) in zip(pending, outcomes):
                self._finish_commit(*item[:-1], sequence, elapsed, group_size=len(pending))

    def _finish_commit(self, s, result, job, transaction_id, cert, certified,
                       install, durable_sequence, durable_fsync_seconds, *, group_size=1):
            before = s.state
            s.state = install.state
            s.text = result["text"]
            if self.contract.get("retain_verified_private_prefix",False):
                from .continuity_proof import eligible_chain
                proof_started=time.perf_counter()
                eligible,witness=eligible_chain(s,self.jobs,self._proposal_results)
                self._event('private-continuity-proof',session_id=s.sid,eligible=eligible,witness=witness,
                    proof_host_wall_seconds=time.perf_counter()-proof_started,
                    certified_frontier=s.state.audio_frontier_window,canonical_version=s.state.checkpoint_id,
                    branch_chunk=s.branch_chunk,branch_generation=s.branch_generation)
                if eligible:
                    s.branch_parent=s.state.checkpoint_id
                    s.branch_root_tokens=s.state.prompt_tokens
                    s.branch_root_frontier=s.state.audio_frontier_window
                    self._event('verified-private-prefix-retained',session_id=s.sid,frontier=s.branch_root_frontier,
                        parent=s.branch_parent,branch_generation=s.branch_generation,private_window=s.branch_chunk)
            installed = self.clock()
            s.state_available_perf=installed
            self._event("commit", session_id=s.sid, job_id=job["job_id"],
                segment_id=transaction_id,
                parent=before.checkpoint_id, version=s.state.checkpoint_id,
                audio_start_sample=job["audio_start_sample"],
                audio_end_sample=job["audio_end_sample"],
                certified=certified-self.t0,
                audio_ready=job["audio_ready_perf"]-self.t0,
                installed=installed-self.t0,
                latency_seconds=installed-job["audio_ready_perf"],
                certificate=asdict(cert), certificate_consumed=True,
                next_prompt_tokens=list(s.state.prompt_tokens),
                segment_tokens=list(result["token_ids"]),
                invalidated_versions=list(install.invalidated_speculative_versions),
                durable_journal_sequence=durable_sequence,
                journal_group_size=group_size,
                journal_fsync_seconds=durable_fsync_seconds)
            if self.contract.get('display_protocol')=='canonical-snapshot-v1':
                self._publish_display(s,canonical=True,text=result['text'],frontier=job['audio_end_sample'],
                    job_id=job['job_id'],transaction_id=transaction_id)
            elif self.contract.get("publish_canonical_display", False):
                self._event("canonical-display", session_id=s.sid,
                    job_id=job["job_id"], version=s.state.checkpoint_id,
                    audio_end_sample=job["audio_end_sample"],
                    displayed=self.clock()-self.t0, text=result["text"],
                    provisional=False, source="durable-commit-publication")
            if self.contract.get('display_protocol')=='canonical-snapshot-v1':
                self._event('install-ack',session_id=s.sid,job_id=job['job_id'],
                    transaction_id=transaction_id,version=s.state.checkpoint_id,
                    audio_end_sample=job['audio_end_sample'],acknowledged=self.clock()-self.t0)
            s.segment_start = s.segment_end
            if s.state.audio_frontier_window == len(s.audio)//4:
                s.auth_done = True
            else:
                self._begin_segment(s)

    def run(self) -> dict:
        while not all(s.done for s in self.sessions.values()) or self.inflight:
            if self.clock()-self.t0 > float(self.contract["timeout_seconds"]):
                raise TimeoutError("live run exceeded frozen drain timeout")
            self._receive()
            if self._blocking_observer:self._blocking_observer.update()
            self._commit_ready()
            for s in self.sessions.values():
                s.done = (s.auth_done and not s.fine_busy and
                          s.fine_window > math.ceil(s.duration/self.fine))
            self._dispatch()
            if self._blocking_observer:self._blocking_observer.update()
            self.sleep(0.001)
        if self._blocking_observer:self._blocking_observer.update(finish=True,force=True)
        elapsed = self.clock()-self.t0
        display = [e["latency_seconds"] for e in self.events if e["kind"] == "display"]
        commits = [e["latency_seconds"] for e in self.events if e["kind"] == "commit"]
        expected_display = sum(
            max(0, math.ceil(s.duration/self.fine)-s.resumed_start_window)
            for s in self.sessions.values()
        )
        expected_commits = sum(
            math.ceil(max(
                0,
                math.ceil(s.duration/self.fine)-s.resumed_start_window,
            )/self.rho)
            for s in self.sessions.values()
        )
        expected_windows = {(s.sid,w) for s in self.sessions.values()
                            for w in range(s.resumed_start_window+1,
                                           math.ceil(s.duration/self.fine)+1)}
        if (set(self.window_outcomes) != expected_windows or
                len(commits) != expected_commits or
                (self.reconciliation == "legacy" and len(display) != expected_display)):
            raise AssertionError("event completeness failed")
        return {"wall_seconds_including_arrival_and_drain": elapsed,
            "audio_seconds": sum(
                max(0.0, s.duration-s.resume_frontier_sample/self.sample_rate)
                for s in self.sessions.values()
            ),
            "audio_seconds_per_wall_second": sum(
                max(0.0, s.duration-s.resume_frontier_sample/self.sample_rate)
                for s in self.sessions.values()
            )/max(elapsed, 1e-12),
            "last_audio_arrival_seconds": max(
                s.offset+max(0.0,s.duration-s.resume_frontier_sample/self.sample_rate)
                for s in self.sessions.values()
            ),
            "display_events": len(display), "certified_commits": len(commits),
            "canonical_display_events": sum(e["kind"]=="canonical-display" for e in self.events),
            "fine_window_outcomes": {outcome:sum(x==outcome for x in self.window_outcomes.values())
                for outcome in sorted(set(self.window_outcomes.values()))},
            "fine_window_accounting_complete": True,
            "resumed_sessions": sum(s.resumed_start_window > 0
                                    for s in self.sessions.values()),
            "resumed_audio_frontier_samples": {
                str(s.sid): s.resume_frontier_sample for s in self.sessions.values()
            },
            "display_p50_seconds": quantile(display, .5) if display else 0.0,
            "display_p99_seconds": quantile(display, .99) if display else 0.0,
            "commit_p50_seconds": quantile(commits, .5) if commits else 0.0,
            "commit_p99_seconds": quantile(commits, .99) if commits else 0.0,
            "display_2s_misses": sum(x > 2 for x in display),
            "token_limit_events": sum(e.get("hit_token_limit", False) for e in self.events),
            "final_states": [{"session_id": s.sid, "text": s.text,
                "state": asdict(s.state)} for s in self.sessions.values()],
            "contract_digest": self.contract_digest,
            "evidence_type": self.contract["evidence_type"]}

    def close(self):
        if self._journal is not None:
            self._journal.close()

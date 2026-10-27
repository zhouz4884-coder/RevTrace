"""Bounded dispatch timing before immutable Private input construction.

Development implementation; no performance advantage has been established.
This controller never reads Authority output, source IDs, fault plans, future
completion times, or creates/rewrites jobs. The scheduler retains every gate.
"""
from collections import defaultdict, deque
from dataclasses import dataclass
import math


POLICIES = ('immediate', 'fixed', 'pending_eta', 'backpressure',
            'recent_gain', 'state_aware')
DEFAULTS = dict(policy='immediate', max_wait_seconds=.75,
                fixed_wait_seconds=.25, fixed_condition='pending', display_slo_seconds=2.,
                deadline_reserve='full_service',
                private_cost_default_seconds=.5,
                authority_cost_default_seconds=1.7,
                service_quantile=.9, history_size=64,
                lead_threshold_windows=2, poll_floor_seconds=.005,
                initial_recent_wait_seconds=.25,
                recent_step_seconds=.05, recent_backoff=.5)


def _quantile(xs, q):
    xs = sorted(xs)
    p = (len(xs) - 1) * q
    lo = int(p)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (p - lo)


@dataclass
class Wait:
    sid: int
    window: int
    target: int
    opened: float
    audio_ready: float
    deadline: float
    until: float
    parent: int
    frontier: int
    projection: tuple
    pending_job: str | None
    active: bool
    closed: bool = False
    input_before: dict | None = None
    service_estimate: float = 0.
    logical_release: float | None = None
    actual_job: str | None = None
    actual_input: dict | None = None
    actual_enqueue: float | None = None
    actual_service: float | None = None
    consumer_first_legal: float | None = None
    input_logged: bool = False
    feedback_done: bool = False


class DispatchWaitController:
    """Six shared-budget timing policies, with no admission authority.

    filter_candidates(scheduler, effective_ready_sessions) is called ONLY for
    proposals, after the real _ready gates and before _make_job. Its result is
    a subset in the same order. observe_event consumes past owner events.

    recent_gain adapts a budget with AIMD using the actual Consumer's D2
    outcome of previously waited frontiers. Actual postwait row service and
    its preregistered historical estimate are logged separately. This is
    observational feedback, not a counterfactual GPU saving. state_aware
    additionally observes Private lineage depth/projection and pending target
    relation; the same ETA/cost/deadline model is given to pending_eta.
    """
    def __init__(self, config=None):
        supplied = dict(config or {})
        unknown = set(supplied) - set(DEFAULTS)
        if unknown:
            raise ValueError('unknown dispatch-wait keys: ' + str(sorted(unknown)))
        self.config = dict(DEFAULTS, **supplied)
        c = self.config
        if c['policy'] not in POLICIES:
            raise ValueError('unknown dispatch-wait policy')
        if c['fixed_condition'] not in ('pending', 'all_ready'):
            raise ValueError('fixed_condition')
        if c['deadline_reserve'] not in ('full_service','raw_slack'):
            raise ValueError('deadline_reserve')
        if not math.isfinite(c['recent_backoff']) or not 0<c['recent_backoff']<1:
            raise ValueError('recent_backoff')
        for k in ('max_wait_seconds', 'fixed_wait_seconds',
                  'private_cost_default_seconds', 'authority_cost_default_seconds',
                  'initial_recent_wait_seconds', 'recent_step_seconds'):
            if not math.isfinite(c[k]) or c[k] < 0:
                raise ValueError(k)
        if not math.isfinite(c['display_slo_seconds']) or c['display_slo_seconds'] <= 0:
            raise ValueError('display_slo_seconds')
        if not 0 <= c['service_quantile'] <= 1:
            raise ValueError('service_quantile')
        if not isinstance(c['history_size'], int) or c['history_size'] < 1:
            raise ValueError('history_size')
        if not isinstance(c['lead_threshold_windows'], int) or c['lead_threshold_windows'] < 1:
            raise ValueError('lead_threshold_windows')
        if not math.isfinite(c['poll_floor_seconds']) or c['poll_floor_seconds'] <= 0:
            raise ValueError('poll_floor_seconds')
        self.waits = {}
        self._active = {}
        self._batch_sizes = {}
        self._completed_jobs = set()
        self._job_waits = {}
        self._feedback = {}
        self.history = defaultdict(lambda: deque(maxlen=c['history_size']))
        self.recent_wait = min(c['max_wait_seconds'], c['initial_recent_wait_seconds'])
        self._last_cohort = None
        self._cohort_sequence = 0

    def observe_event(self, row):
        """Accept already observed events, never a worker's future result."""
        kind = row.get('kind')
        if kind == 'enqueue' and row['role']=='proposal':
            key=(row['session_id'],row['end_window']);wait=self.waits.get(key)
            if wait is not None and wait.active:
                wait.actual_job=row['job_id'];wait.actual_enqueue=row['enqueue_perf']
                wait.actual_input=dict(prompt_tokens=row.get('declared_prompt_tokens'),
                    chunk_id=row['chunk_id'],root_frontier=row['audio_start_sample'],
                    target_frontier=row['audio_end_sample'],parent=row['parent'])
                self._job_waits[row['job_id']]=key
        elif kind == 'batch-dispatched':
            for jid in row['job_ids']:
                self._batch_sizes[jid] = len(row['job_ids'])
        elif kind == 'executor-complete':
            jid = row['job_id']
            if jid in self._completed_jobs:
                return
            # Past row delivery duration is an ETA predictor; it is NOT a
            # physical-batch energy or GPU-lease accounting measurement.
            value = float(row['received']) - float(row['enqueue'])
            role = row['role']
            if value < 0 or not math.isfinite(value):
                raise ValueError('noncausal observed completion')
            self._completed_jobs.add(jid)
            self.history[(role, self._batch_sizes.get(jid, 0))].append(value)
            self.history[(role, -1)].append(value)
            if jid in self._job_waits:
                self.waits[self._job_waits[jid]].actual_service=value

    def observe_consumer_ack(self, scheduler, ack):
        """Hook AFTER the envelope has validated an actual applied-view ACK.

        A receipt is progress feedback only. It never grants canonical writes.
        Each actual ACK must reach this hook; sampling only the latest _acks
        entry could miss an earlier timely view that was later withdrawn.
        """
        if isinstance(ack,dict):return
        session=scheduler.sessions.get(ack.session_id)
        if (session is None or ack.owner_incarnation!=scheduler.t0
            or ack.contract_digest!=scheduler.contract_digest
            or ack.canonical_epoch!=session.state.contract_epoch
            or ack.observed_perf>scheduler.clock()+1e-7):return
        for key in list(self._feedback):
            wait=self.waits[key]
            if (wait.sid==ack.session_id and wait.consumer_first_legal is None
                    and ack.valid_visible_frontier>=wait.target):
                wait.consumer_first_legal=float(ack.observed_perf)

    def _cost(self, role, batch_size):
        xs = self.history.get((role, batch_size))
        exact = bool(xs)
        if not xs:
            xs = self.history.get((role, -1))
        if xs:
            return _quantile(xs, self.config['service_quantile']), len(xs), exact
        k = 'authority_cost_default_seconds' if role == 'authority' else 'private_cost_default_seconds'
        return self.config[k], 0, False

    @staticmethod
    def _target(scheduler, session, window):
        return min(round(scheduler._end_seconds(session, window) * scheduler.sample_rate),
                   len(session.audio) // 4)

    @classmethod
    def describe_private_input(cls,scheduler,session,window):
        """Pure description of _make_job's input choice; never executes it."""
        target=cls._target(scheduler,session,window)
        rebase=(session.state.checkpoint_id>session.branch_parent
                and session.state.audio_frontier_window<target)
        return dict(prompt_tokens=list(session.state.prompt_tokens if rebase else session.branch_tokens),
            chunk_id=min(session.segment_start,window-1) if rebase else session.branch_chunk,
            root_frontier=session.state.audio_frontier_window if rebase else session.branch_root_frontier,
            target_frontier=target,parent=session.state.checkpoint_id if rebase else session.branch_parent,
            would_rebase=rebase,canonical_target_already_covered=session.state.audio_frontier_window>=target)

    def _pending(self, scheduler, session, now):
        """Use live lease/job identities and observed phase, not output bodies."""
        candidates = []
        for worker, ids in scheduler.inflight.values():
            for jid in ids:
                job = scheduler.jobs[jid]
                if (job['role'] != 'authority' or job['session_id'] != session.sid
                        or job['parent'] != session.state.checkpoint_id
                        or job['contract_epoch'] != session.state.contract_epoch
                        or job['contract_digest'] != scheduler.contract_digest):
                    continue
                estimate, samples, exact = self._cost('authority', len(ids))
                elapsed = max(0., now - job['enqueue_perf'])
                residual = max(self.config['poll_floor_seconds'], estimate - elapsed)
                candidates.append(dict(job_id=jid, end=job['audio_end_sample'],
                    end_window=job['end_window'], elapsed_seconds=elapsed,
                    remaining_estimate_seconds=residual,
                    estimate_samples=samples, estimate_exact_batch_size=exact,
                    physical_batch_size=len(ids),
                    observed_phase=getattr(worker, 'execution_phase', 'unknown')))
        # Logical row receipt may outlive its physical lease while the owner
        # has not installed it yet. Only read the receipt's job identity here.
        result = getattr(session, 'auth_result', None)
        jid = result.get('job_id') if result is not None else None
        if jid is not None and not any(c['job_id']==jid for c in candidates):
            job = scheduler.jobs[jid]
            if (job['role']=='authority' and job['session_id']==session.sid
                    and job['parent']==session.state.checkpoint_id
                    and job['contract_epoch']==session.state.contract_epoch
                    and job['contract_digest']==scheduler.contract_digest
                    and scheduler.contract.get('proposal_barrier') != 'segment'):
                candidates.append(dict(job_id=jid, end=job['audio_end_sample'],
                    end_window=job['end_window'],
                    elapsed_seconds=max(0.,now-job['enqueue_perf']),
                    remaining_estimate_seconds=self.config['poll_floor_seconds'],
                    estimate_samples=0, estimate_exact_batch_size=False,
                    physical_batch_size=0, observed_phase='owner-result-pending-install'))
        # Single-owner contracts normally leave at most one relevant target.
        # Deterministic minimum remains well-defined for CPU multi-lease tests.
        return min(candidates, key=lambda x: (x['remaining_estimate_seconds'], x['job_id']),
                   default=None)

    def _close(self, scheduler, wait, session, now, reason):
        if wait.closed:
            return
        wait.closed = True
        self._active.pop((wait.sid, wait.window), None)
        if not wait.active:
            return
        projection_changed = tuple(session.state.prompt_tokens) != wait.projection
        covered = session.state.audio_frontier_window >= wait.target
        logical=wait.until
        if session.state.checkpoint_id!=wait.parent:
            installed=getattr(session,'state_available_perf',now)
            if wait.opened<=installed<=now:logical=min(logical,installed)
        if reason=='pending-job-no-longer-leased':logical=min(logical,now)
        wait.logical_release=max(wait.opened,min(logical,now))
        workers=getattr(scheduler,'executors',{}).get('proposal',[])
        scheduler._event('dispatch-wait-release', session_id=wait.sid, window=wait.window,
            reason=reason, waited_seconds=max(0., now-wait.opened),
            policy_suppression_seconds=wait.logical_release-wait.opened,
            logical_release_perf=wait.logical_release,owner_observed_release_perf=now,
            owner_observation_lag_seconds=max(0.,now-wait.logical_release),
            proposal_worker_available=any(w.name not in scheduler.inflight for w in workers),
            original_audio_ready_perf=wait.audio_ready, original_deadline_perf=wait.deadline,
            wait_until_perf=wait.until, opened_parent=wait.parent,
            current_parent=session.state.checkpoint_id,
            canonical_projection_changed=projection_changed, target_now_covered=covered,
            recent_feedback_rule='actual-consumer-D2-AIMD-with-observed-service-cost',
            recent_wait_seconds=self.recent_wait)

    def tick(self,scheduler):
        """Run every owner loop, including when every GPU worker is leased."""
        now = scheduler.clock()
        # _ready may have legally retired or covered a target. Keep its record
        # and close the wait without creating a substitute job or new credit.
        for wait in list(self._active.values()):
            s = scheduler.sessions[wait.sid]
            if s.done or s.fine_window != wait.window:
                self._close(scheduler, wait, s, now, 'target-no-longer-pending')
                continue
            parent_changed=s.state.checkpoint_id!=wait.parent
            result=getattr(s,'auth_result',None)
            received_job=result.get('job_id') if result is not None else None
            pending_disappeared=(wait.pending_job is not None and not any(
                wait.pending_job in ids for _,ids in scheduler.inflight.values())
                and received_job!=wait.pending_job)
            if parent_changed or pending_disappeared or now>=wait.until:
                self._close(scheduler,wait,s,now,'canonical-advanced' if parent_changed else
                    'pending-job-no-longer-leased' if pending_disappeared else 'finite-budget-expired')
        for key in list(self._feedback):
            wait=self.waits[key];s=scheduler.sessions[wait.sid]
            if wait.closed and wait.actual_input is not None and not wait.input_logged:
                before=wait.input_before;after=wait.actual_input
                sameP=None if after['prompt_tokens'] is None else before['prompt_tokens']==after['prompt_tokens']
                scheduler._event('dispatch-wait-input-outcome',session_id=wait.sid,window=wait.window,
                    job_id=wait.actual_job,input_before_wait=before,actual_frozen_input=after,
                    declared_P_changed=None if sameP is None else not sameP,
                    chunk_changed=before['chunk_id']!=after['chunk_id'],
                    root_frontier_changed=before['root_frontier']!=after['root_frontier'],
                    post_release_to_enqueue_seconds=wait.actual_enqueue-wait.logical_release,
                    scope='actual job declaration; processed GPU input equivalence requires independent worker records')
                wait.input_logged=True
            if not wait.closed or wait.consumer_first_legal is None:continue
            covered_without_job=(wait.actual_job is None and s.fine_window!=wait.window
                                 and s.state.audio_frontier_window>=wait.target)
            if wait.actual_service is None and not covered_without_job:continue
            timely=wait.consumer_first_legal<=wait.deadline
            previous=self.recent_wait
            if self.config['policy']=='recent_gain':
                self.recent_wait=(min(self.config['max_wait_seconds'],previous+self.config['recent_step_seconds'])
                                  if timely else previous*self.config['recent_backoff'])
            scheduler._event('dispatch-wait-feedback',session_id=wait.sid,window=wait.window,
                consumer_first_legal_perf=wait.consumer_first_legal,original_deadline_perf=wait.deadline,
                actual_D2_pass=timely,observed_postwait_service_seconds=wait.actual_service,
                initial_service_estimate_seconds=wait.service_estimate,
                observed_minus_predicted_service_seconds=None if wait.actual_service is None else wait.actual_service-wait.service_estimate,
                covered_without_job=covered_without_job,recent_wait_before=previous,recent_wait_after=self.recent_wait,
                rule='additive increase on actual timely legal coverage, multiplicative decrease on actual late coverage',
                counterfactual_saving_claim=False)
            wait.feedback_done=True;del self._feedback[key]

    def filter_candidates(self, scheduler, ready_sessions):
        self.tick(scheduler)
        now=scheduler.clock()
        permitted = []
        proposed_batch_size = min(len(ready_sessions), int(scheduler.contract['microbatch']))
        private_cost, private_samples, private_exact = self._cost('proposal', proposed_batch_size)
        for s in ready_sessions:
            window = s.fine_window
            key = s.sid, window
            wait = self.waits.get(key)
            if wait is not None:
                if wait.closed:
                    permitted.append(s)
                    continue
                parent_changed = s.state.checkpoint_id != wait.parent
                result = getattr(s, 'auth_result', None)
                received_job = result.get('job_id') if result is not None else None
                pending_disappeared = (wait.pending_job is not None and not any(
                    wait.pending_job in ids for _, ids in scheduler.inflight.values())
                    and received_job != wait.pending_job)
                if parent_changed or pending_disappeared or now >= wait.until:
                    self._close(scheduler, wait, s, now,
                                'canonical-advanced' if parent_changed else
                                'pending-job-no-longer-leased' if pending_disappeared else
                                'finite-budget-expired')
                    permitted.append(s)
                # A changed parent releases this one-shot wait. _make_job
                # will read/rebase the current state after this method returns.
                continue
            ready = scheduler._ready_time(s, window)
            deadline = ready + self.config['display_slo_seconds']
            target = self._target(scheduler, s, window)
            input_before=self.describe_private_input(scheduler,s,window)
            reserve = private_cost if self.config['deadline_reserve']=='full_service' else 0.
            # raw_slack only bounds the WAIT by the original deadline. It does
            # not promise that later generation or Consumer application passes
            # D2. All such misses remain in the real offered-audio denominator.
            cap = max(0., min(self.config['max_wait_seconds'], deadline-now-reserve))
            pending = self._pending(scheduler, s, now)
            eta = pending['remaining_estimate_seconds'] if pending else None
            lead = max(0., (target-s.state.audio_frontier_window) /
                       (scheduler.fine*scheduler.sample_rate))
            private_depth = max(0, input_before['chunk_id']-s.segment_start)
            private_differs = tuple(input_before['prompt_tokens']) != tuple(s.state.prompt_tokens)
            predecessor = bool(pending and pending['end'] < target)
            policy = self.config['policy']
            duration = 0.
            reason = 'immediate'
            if cap <= 0:
                reason = 'no-original-deadline-slack'
            elif policy == 'fixed':
                if pending or self.config['fixed_condition'] == 'all_ready':
                    duration = min(cap, self.config['fixed_wait_seconds'])
                    reason = 'fixed-development-budget-' + self.config['fixed_condition']
                else:
                    reason = 'fixed-pending-no-relevant-authority'
            elif policy == 'backpressure':
                if pending and lead >= self.config['lead_threshold_windows']:
                    duration = cap
                    reason = 'lead-and-authority-lease'
                else:
                    reason = 'lead-below-threshold-or-no-pending-authority'
            elif policy in ('pending_eta', 'recent_gain', 'state_aware'):
                chosen_cap = min(cap, self.recent_wait) if policy == 'recent_gain' else cap
                eligible = bool(pending and eta <= chosen_cap)
                if policy == 'state_aware':
                    # These are currently observable dependency relations.
                    # They predict usefulness only and never authorize input.
                    eligible = eligible and predecessor and private_depth > 0 and private_differs
                if eligible:
                    duration = chosen_cap
                    reason = ('pending-eta' if policy == 'pending_eta' else
                              'recent-refresh-feedback' if policy == 'recent_gain' else
                              'pending-predecessor-and-private-lineage')
                else:
                    reason = 'no-estimated-refresh-within-budget-or-state-signal'
            active = duration > 0
            wait = Wait(s.sid, window, target, now, ready, deadline, now+duration,
                        s.state.checkpoint_id, s.state.audio_frontier_window,
                        tuple(s.state.prompt_tokens), pending['job_id'] if pending else None,
                        active, closed=not active)
            wait.input_before=input_before
            wait.service_estimate=private_cost
            self.waits[key] = wait
            if active:
                self._active[key] = wait
                self._feedback[key]=True
            scheduler._event('dispatch-wait-decision', session_id=s.sid, window=window,
                policy=policy, decision='wait' if active else 'dispatch', reason=reason,
                observed_perf=now, original_audio_ready_perf=ready,
                original_deadline_perf=deadline, wait_until_perf=wait.until,
                wait_budget_seconds=duration, canonical_parent=s.state.checkpoint_id,
                pre_wait_effective_private_input=wait.input_before,
                canonical_frontier=s.state.audio_frontier_window,
                target_frontier=target, private_depth=private_depth,
                private_projection_differs=private_differs,
                pending_predecessor=predecessor, pending_authority=pending,
                lead_windows=lead, private_completion_estimate_seconds=private_cost,
                private_estimate_samples=private_samples,
                private_estimate_exact_batch_size=private_exact,
                deadline_reserve=self.config['deadline_reserve'],
                reserved_generation_seconds=reserve,
                output_deadline_guaranteed=False)
            if not active:
                permitted.append(s)
        # One cohort record per membership/decision change, not once per poll.
        # It retains all real _ready outputs including entries held out of the
        # subsequent physical batch, so denominator reconstruction is possible.
        eligible_keys = tuple((s.sid, s.fine_window) for s in ready_sessions)
        released_keys = tuple((s.sid, s.fine_window) for s in permitted)
        held_keys = tuple(k for k in eligible_keys if k not in released_keys)
        signature = eligible_keys, released_keys, held_keys
        if signature != self._last_cohort:
            self._cohort_sequence += 1
            scheduler._event('dispatch-wait-cohort', sequence=self._cohort_sequence,
                observed_perf=now, policy=self.config['policy'],
                eligible=[dict(session_id=sid, window=w) for sid,w in eligible_keys],
                released=[dict(session_id=sid, window=w) for sid,w in released_keys],
                held=[dict(session_id=sid, window=w) for sid,w in held_keys])
            self._last_cohort = signature
        return permitted

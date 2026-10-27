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
                fixed_wait_seconds=.25, display_slo_seconds=2.,
                private_cost_default_seconds=.5,
                authority_cost_default_seconds=1.7,
                service_quantile=.9, history_size=64,
                lead_threshold_windows=2, poll_floor_seconds=.005,
                initial_recent_wait_seconds=.25,
                recent_step_seconds=.05)


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


class DispatchWaitController:
    """Six shared-budget timing policies, with no admission authority.

    filter_candidates(scheduler, effective_ready_sessions) is called ONLY for
    proposals, after the real _ready gates and before _make_job. Its result is
    a subset in the same order. observe_event consumes past owner events.

    recent_gain adapts a budget using observed useful-refresh frequency (a
    changed Canonical projection or covered target). This is an explicitly
    named feedback proxy, not a measured counterfactual GPU saving. state_aware
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
        self.history = defaultdict(lambda: deque(maxlen=c['history_size']))
        self.recent_wait = min(c['max_wait_seconds'], c['initial_recent_wait_seconds'])

    def observe_event(self, row):
        """Accept already observed events, never a worker's future result."""
        kind = row.get('kind')
        if kind == 'batch-dispatched':
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
        useful_refresh = projection_changed or covered
        if self.config['policy'] == 'recent_gain':
            delta = self.config['recent_step_seconds'] * (1 if useful_refresh else -1)
            self.recent_wait = min(self.config['max_wait_seconds'],
                                   max(0., self.recent_wait + delta))
        scheduler._event('dispatch-wait-release', session_id=wait.sid, window=wait.window,
            reason=reason, waited_seconds=max(0., now-wait.opened),
            original_audio_ready_perf=wait.audio_ready, original_deadline_perf=wait.deadline,
            wait_until_perf=wait.until, opened_parent=wait.parent,
            current_parent=session.state.checkpoint_id,
            canonical_projection_changed=projection_changed, target_now_covered=covered,
            recent_feedback_proxy='canonical-refresh-or-covered-target',
            recent_wait_seconds=self.recent_wait)

    def filter_candidates(self, scheduler, ready_sessions):
        now = scheduler.clock()
        # _ready may have legally retired or covered a target. Keep its record
        # and close the wait without creating a substitute job or new credit.
        for wait in list(self._active.values()):
            s = scheduler.sessions[wait.sid]
            if s.done or s.fine_window != wait.window:
                self._close(scheduler, wait, s, now, 'target-no-longer-pending')
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
                if parent_changed or now >= wait.until:
                    self._close(scheduler, wait, s, now,
                                'canonical-advanced' if parent_changed else 'finite-budget-expired')
                    permitted.append(s)
                # A changed parent releases this one-shot wait. _make_job
                # will read/rebase the current state after this method returns.
                continue
            ready = scheduler._ready_time(s, window)
            deadline = ready + self.config['display_slo_seconds']
            target = self._target(scheduler, s, window)
            cap = max(0., min(self.config['max_wait_seconds'], deadline-now-private_cost))
            pending = self._pending(scheduler, s, now)
            eta = pending['remaining_estimate_seconds'] if pending else None
            lead = max(0., (target-s.state.audio_frontier_window) /
                       (scheduler.fine*scheduler.sample_rate))
            private_depth = max(0, s.branch_chunk-s.segment_start)
            private_differs = tuple(s.branch_tokens) != tuple(s.state.prompt_tokens)
            predecessor = bool(pending and pending['end'] < target)
            policy = self.config['policy']
            duration = 0.
            reason = 'immediate'
            if cap <= 0:
                reason = 'no-original-deadline-slack'
            elif policy == 'fixed':
                duration = min(cap, self.config['fixed_wait_seconds'])
                reason = 'fixed-development-budget'
            elif policy == 'backpressure':
                if pending and lead >= self.config['lead_threshold_windows']:
                    duration = cap
                    reason = 'lead-and-authority-lease'
                else:
                    reason = 'lead-below-threshold-or-no-pending-authority'
            elif policy in ('pending_eta', 'recent_gain', 'state_aware'):
                eligible = bool(pending and eta <= cap)
                if policy == 'state_aware':
                    # These are currently observable dependency relations.
                    # They predict usefulness only and never authorize input.
                    eligible = eligible and predecessor and private_depth > 0 and private_differs
                if eligible:
                    duration = cap if policy != 'recent_gain' else min(cap, self.recent_wait)
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
            self.waits[key] = wait
            if active:
                self._active[key] = wait
            scheduler._event('dispatch-wait-decision', session_id=s.sid, window=window,
                policy=policy, decision='wait' if active else 'dispatch', reason=reason,
                observed_perf=now, original_audio_ready_perf=ready,
                original_deadline_perf=deadline, wait_until_perf=wait.until,
                wait_budget_seconds=duration, canonical_parent=s.state.checkpoint_id,
                canonical_frontier=s.state.audio_frontier_window,
                target_frontier=target, private_depth=private_depth,
                private_projection_differs=private_differs,
                pending_predecessor=predecessor, pending_authority=pending,
                lead_windows=lead, private_completion_estimate_seconds=private_cost,
                private_estimate_samples=private_samples,
                private_estimate_exact_batch_size=private_exact)
            if not active:
                permitted.append(s)
        return permitted

"""Same-task optimistic execution with a conservative birth-root fence.

This is the strict birth-version baseline requested for the v16 comparison,
not a reproduction of Retire or a claim about all dependency-version schemes.
The dedicated install generation is a *policy* token.  Owner epochs, session
epochs, physical incarnations, frozen starts and job identities are unchanged.

Early views already admitted by the shared SUP path remain independently
supported.  Rejecting a full result never removes a supported view.  A policy
fence does not assert that the complete input is semantically refuted.
"""
from resilience_policy import ResilientFullSpecCoordinator


POLICY_FENCE_KINDS = frozenset(("birth_root_policy_fence", "inflight_at_install_policy_fence",
                              "dependency_version_policy_fence"))


def is_policy_fence(proof):
    return proof.get("kind") in POLICY_FENCE_KINDS


class SafeVersionedCoordinator(ResilientFullSpecCoordinator):
    policy_name = "safe_versioned_birth_root"

    def __init__(self, **kwargs):
        self.install_generations = {sid: 0 for sid in kwargs["initials"]}
        super().__init__(**kwargs)

    def register(self, **kwargs):
        job = super().register(**kwargs)
        job["birth_install_generation"] = self.install_generations[job["source_id"]]
        self._refresh_active()
        return job

    def _reason(self, job):
        sid = job["source_id"]
        semantic = super()._reason(job)
        # Session replacement remains a real lifecycle fence, with its original
        # immutable identity. It must not masquerade as an install generation.
        if job["dispatch_epoch"] != self.epochs[sid]:
            return semantic
        birth = job.get("birth_install_generation", self.install_generations[sid])
        if birth != self.install_generations[sid]:
            return dict(
                kind="birth_root_policy_fence", job_id=job["job_id"],
                source_id=sid, dispatch_epoch=job["dispatch_epoch"],
                birth_install_generation=birth,
                current_install_generation=self.install_generations[sid],
                birth_canonical_sha=job["birth_canonical_sha"],
                current_canonical_sha=self.canonical(sid).sha256,
                complete_input_equals_current_parent=job["start"].same(self.canonical(sid)),
                complete_input_refutation=semantic,
                policy_only_fence=semantic is None,
                fence_uses_input_refutation=False,
            )
        return semantic

    def _refresh_active(self):
        # A stale job may still own its physical worker. It must not occupy the
        # logical current-parent slot or prevent a replacement on another ready
        # worker. No stale job is relabelled/promoted into this policy version.
        self.active_authority.clear()
        for job in self.jobs.values():
            sid = job["source_id"]
            if self._reason(job) is None and job["start"].same(self.canonical(sid)):
                if sid in self.active_authority:
                    raise ValueError("duplicate in-flight complete current input")
                self.active_authority[sid] = job["job_id"]

    def _commit(self, item):
        # A completed current-parent original is selected under its old token.
        # Advancing the token before this call would discard the very result
        # that produced the new canonical state and make the baseline stall.
        reason = self._reason(item["job"])
        if reason is not None:
            raise ValueError("policy-fenced full result cannot become Canonical")
        result = super()._commit(item)
        sid = item["job"]["source_id"]
        self.install_generations[sid] += 1
        self._refresh_active()
        result["policy_install_generation"] = self.install_generations[sid]
        return result

    def history_stats(self):
        return dict(super().history_stats(), policy_name=self.policy_name,
                    install_generations=dict(self.install_generations))


class ReadyOnlyCoordinator(SafeVersionedCoordinator):
    """Strong memoization control: preserve completed work, fence live work.

    At each selected install, every call without an Owner-admitted complete
    result receives an immutable fence. Results already in the Owner's ready
    bank can still become selected when their exact actual parent is installed.
    A terminal frame completed physically but not yet admitted is not ready at
    this observable policy boundary. A late receipt cannot enter the ready bank.
    SUP views survive independently of complete-call retention.
    """
    policy_name = "ready_only_speculation"

    def __init__(self, **kwargs):
        self.inflight_install_fences = {}
        super().__init__(**kwargs)

    def _reason(self, job):
        semantic = ResilientFullSpecCoordinator._reason(self, job)
        if job["dispatch_epoch"] != self.epochs[job["source_id"]]:
            return semantic
        fence = self.inflight_install_fences.get(job["job_id"])
        return dict(fence) if fence is not None else semantic

    def _commit(self, item):
        result = super()._commit(item)
        sid = item["job"]["source_id"]
        for job_id, job in self.jobs.items():
            if job["source_id"] != sid or job_id in self.inflight_install_fences:
                continue
            if job["dispatch_epoch"] != self.epochs[sid]:
                continue
            semantic = ResilientFullSpecCoordinator._reason(self, job)
            self.inflight_install_fences[job_id] = dict(
                kind="inflight_at_install_policy_fence", job_id=job_id,
                source_id=sid, dispatch_epoch=job["dispatch_epoch"],
                birth_install_generation=job["birth_install_generation"],
                fence_install_generation=self.install_generations[sid],
                birth_canonical_sha=job["birth_canonical_sha"],
                fence_canonical_sha=self.canonical(sid).sha256,
                owner_complete_receipt_before_install=False,
                complete_input_equals_current_parent=job["start"].same(self.canonical(sid)),
                complete_input_refutation=semantic,
                policy_only_fence=semantic is None,
                fence_uses_input_refutation=False,
            )
        self._refresh_active()
        return result

    def collect_history(self, pending_job_ids=()):
        super().collect_history(pending_job_ids=pending_job_ids)
        live = set(self.jobs) | set(self.completed_full)
        for job_id in list(self.inflight_install_fences):
            if job_id not in live:
                del self.inflight_install_fences[job_id]
        return self.history_stats()

    def history_stats(self):
        return dict(super().history_stats(),
                    inflight_install_fences=len(self.inflight_install_fences))


class DependencyVersionedCoordinator(ResilientFullSpecCoordinator):
    """Expected-parent handover with eager transitive branch-version revocation.

    Compatible parent handovers preserve work, so ordinary direct-hop cases
    coincide with RevTrace EL. A frozen *ancestor* mismatch, however, permanently
    revokes that job's dependency version; later complete-input convergence does
    not resurrect it. This is an author-built strong version-DAG control, not an
    implementation of a named external system.
    """
    policy_name = "dependency_versioned_speculation"

    def __init__(self, **kwargs):
        self.dependency_version_fences = {}
        super().__init__(**kwargs)

    def _reason(self, job):
        sid=job["source_id"]
        semantic=super()._reason(job)
        if job["dispatch_epoch"] != self.epochs[sid]:
            return semantic
        frozen=self.dependency_version_fences.get(job["job_id"])
        if frozen is not None:
            return dict(frozen)
        # Actual same-F mismatch/coverage are sufficient without a policy fence.
        if semantic is not None:
            return semantic
        witnesses=self._canonical_witnesses[sid][self.epochs[sid]]
        for dep in job["frozen_dependencies"]:
            actual=witnesses.get(dep.frontier)
            if dep.frontier < job["start"].frontier and actual is not None and not actual.same(dep):
                return dict(kind="dependency_version_policy_fence",
                            job_id=job["job_id"],source_id=sid,
                            dispatch_epoch=job["dispatch_epoch"],
                            witness_frontier=dep.frontier,
                            expected_ancestor_sha=dep.sha256,
                            actual_ancestor_sha=actual.sha256,
                            complete_start_sha=job["start"].sha256,
                            complete_start_frontier=job["start"].frontier,
                            complete_input_equals_current_parent=job["start"].same(self.canonical(sid)),
                            policy_only_fence=True,complete_input_refutation=None,
                            fence_uses_input_refutation=False)
        return None

    def _refresh_active(self):
        self.active_authority.clear()
        for job in self.jobs.values():
            sid=job["source_id"]
            if self._reason(job) is None and job["start"].same(self.canonical(sid)):
                if sid in self.active_authority:
                    raise ValueError("duplicate in-flight complete current input")
                self.active_authority[sid]=job["job_id"]
                if not job["started_on_canonical"] and not job.get("promoted_to_canonical",False):
                    job["promoted_to_canonical"]=True
                    self.promotions.append(dict(job_id=job["job_id"],source_id=sid,
                        birth_canonical_sha=job["birth_canonical_sha"],
                        birth_epoch=job["dispatch_epoch"],actual_parent_sha=self.canonical(sid).sha256))

    def _commit(self,item):
        if self._reason(item["job"]) is not None:
            raise ValueError("dependency-version-fenced full result cannot become Canonical")
        result=super()._commit(item)
        # Freeze every loss at this actual install, even if several complete
        # results are drained in one Owner iteration before hints are sent.
        candidates=list(self.jobs.values())+[v["job"] for v in self.completed_full.values()]
        for job in candidates:
            reason=self._reason(job)
            if reason is not None and reason["kind"]=="dependency_version_policy_fence":
                self.dependency_version_fences.setdefault(job["job_id"],dict(reason))
        self._refresh_active()
        return result

    def collect_history(self,pending_job_ids=()):
        super().collect_history(pending_job_ids=pending_job_ids)
        live=set(self.jobs)|set(self.completed_full)
        for job_id in list(self.dependency_version_fences):
            if job_id not in live:
                del self.dependency_version_fences[job_id]
        return self.history_stats()

    def history_stats(self):
        return dict(super().history_stats(),policy_name=self.policy_name,
                    dependency_version_fences=len(self.dependency_version_fences))

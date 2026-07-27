"""Mathematical helpers for RevGuard execution-shape contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RevisionTicket:
    """Version-bound permission to propose one revision transition."""

    session_id: str
    revision_id: str
    parent_version: int
    next_version: int


class RevisionCommitLedger:
    """Minimal optimistic-concurrency ledger for revision state entry.

    A result can enter the state machine only when its parent version is still
    the committed version for the session.  Replayed and late results fail
    closed instead of overwriting a newer revision.
    """

    def __init__(self) -> None:
        self._versions: dict[str, int] = {}
        self._issued: set[str] = set()
        self._committed: set[str] = set()

    def register(self, session_id: str, initial_version: int = 0) -> None:
        if not session_id:
            raise ValueError("session_id must be non-empty")
        if initial_version < 0:
            raise ValueError("initial_version must be non-negative")
        if session_id in self._versions:
            raise ValueError(f"session already registered: {session_id}")
        self._versions[session_id] = initial_version

    def issue(self, session_id: str, revision_id: str) -> RevisionTicket:
        if session_id not in self._versions:
            raise KeyError(f"unknown session: {session_id}")
        if not revision_id:
            raise ValueError("revision_id must be non-empty")
        if revision_id in self._issued:
            raise ValueError(f"revision already issued: {revision_id}")
        parent = self._versions[session_id]
        ticket = RevisionTicket(
            session_id=session_id,
            revision_id=revision_id,
            parent_version=parent,
            next_version=parent + 1,
        )
        self._issued.add(revision_id)
        return ticket

    def can_commit(self, ticket: RevisionTicket) -> bool:
        return (
            ticket.revision_id in self._issued
            and ticket.revision_id not in self._committed
            and self._versions.get(ticket.session_id) == ticket.parent_version
        )

    def commit(self, ticket: RevisionTicket) -> int:
        if not self.can_commit(ticket):
            raise ValueError(
                "stale, replayed, or unissued revision result: "
                f"{ticket.revision_id}"
            )
        self._versions[ticket.session_id] = ticket.next_version
        self._committed.add(ticket.revision_id)
        return ticket.next_version

    def version(self, session_id: str) -> int:
        if session_id not in self._versions:
            raise KeyError(f"unknown session: {session_id}")
        return self._versions[session_id]


def margin_certifies_argmax(margin: float, perturbation_linf: float) -> bool:
    """Return the standard sufficient condition for top-1 invariance.

    If every log-probability changes by at most ``perturbation_linf`` between
    the batched and canonical executions, a batched top-1/top-2 margin greater
    than twice that bound certifies the same canonical argmax.
    """

    if margin < 0:
        raise ValueError("margin must be non-negative")
    if perturbation_linf < 0:
        raise ValueError("perturbation_linf must be non-negative")
    return margin > 2.0 * perturbation_linf


def pipeline_speedup_lower_bound(
    reference_seconds: float,
    proposer_seconds: float,
    verifier_seconds: float,
) -> float:
    """Ideal two-stage steady-state speedup with no overlap overhead."""

    if min(reference_seconds, proposer_seconds, verifier_seconds) < 0:
        raise ValueError("service times must be non-negative")
    bottleneck = max(proposer_seconds, verifier_seconds)
    if bottleneck == 0:
        return float("inf")
    return reference_seconds / bottleneck


def single_gpu_selective_speedup(
    reference_seconds: float,
    proposer_seconds: float,
    verifier_seconds: float,
) -> float:
    """Sequential proposer-plus-verifier speedup on one GPU."""

    if min(reference_seconds, proposer_seconds, verifier_seconds) < 0:
        raise ValueError("service times must be non-negative")
    policy_seconds = proposer_seconds + verifier_seconds
    if policy_seconds == 0:
        return float("inf")
    return reference_seconds / policy_seconds

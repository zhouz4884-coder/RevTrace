"""Cluster-aware tail-capacity contracts for revision serving.

The statistical unit is a release round, not an individual session event:
all sessions in one synchronous release share the same state-entry latency.
The certificate combines cross-seed tail uncertainty, burst structure,
contract-scoped state risk, and the online authority invariant.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence


_ONE_SIDED_T95 = {
    1: 6.3138,
    2: 2.9200,
    3: 2.3534,
    4: 2.1318,
    5: 2.0150,
    6: 1.9432,
    7: 1.8946,
    8: 1.8595,
    9: 1.8331,
    10: 1.8125,
}


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must lie in [0, 1]")
    ordered = sorted(float(value) for value in values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(len(ordered) - 1, lower + 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def one_sided_t_upper(values: Sequence[float], confidence: float = 0.95) -> float:
    """Return a one-sided t upper confidence bound for a seed-level mean."""

    if confidence != 0.95:
        raise ValueError("only the preregistered 95 percent bound is supported")
    if len(values) < 2:
        return math.inf
    numeric = [float(value) for value in values]
    degrees = len(numeric) - 1
    critical = _ONE_SIDED_T95.get(degrees, 1.6449)
    return statistics.mean(numeric) + critical * statistics.stdev(
        numeric
    ) / math.sqrt(len(numeric))


@dataclass(frozen=True)
class ClusterAwareCapacityCertificate:
    contract_digest: str
    seeds: int
    rounds: int
    event_equivalent_count: int
    seed_p99_seconds: tuple[float, ...]
    seed_p99_mean_seconds: float
    seed_p99_std_seconds: float
    seed_p99_upper_95_seconds: float
    maximum_seed_p99_seconds: float
    terminal_seed_p99_seconds: tuple[float, ...]
    terminal_seed_p99_upper_95_seconds: float | None
    maximum_terminal_seed_p99_seconds: float | None
    nonterminal_seed_p99_seconds: tuple[float, ...]
    nonterminal_seed_p99_upper_95_seconds: float | None
    maximum_nonterminal_seed_p99_seconds: float | None
    round_p99_seconds: float | None
    maximum_round_seconds: float | None
    terminal_round_p99_seconds: float | None
    nonterminal_round_p99_seconds: float | None
    maximum_verified_count: int | None
    maximum_verification_overlap_fraction: float | None
    deadline_miss_rounds: int
    deadline_miss_events: int
    risk_upper_bound: float
    online_selection_authority_violations: int
    deadline_seconds: float
    guard_seconds: float
    allowed_risk: float
    accepted: bool
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_cluster_aware_certificate(
    seed_rows: Sequence[Mapping[str, Any]],
    *,
    contract_digest: str,
    risk_upper_bound: float,
    deadline_seconds: float = 2.0,
    guard_seconds: float = 0.1,
    allowed_risk: float = 0.005,
) -> ClusterAwareCapacityCertificate:
    if len(seed_rows) < 2:
        raise ValueError("a cross-seed certificate needs at least two seeds")
    if not 0.0 <= risk_upper_bound <= 1.0:
        raise ValueError("risk_upper_bound must lie in [0, 1]")
    seed_p99 = [float(row["p99_seconds"]) for row in seed_rows]
    all_rounds = [
        detail
        for row in seed_rows
        for detail in row.get("rounds_detail", [])
    ]
    latencies = [
        float(detail["state_entry_latency_seconds"]) for detail in all_rounds
    ]
    terminal = [
        float(detail["state_entry_latency_seconds"])
        for detail in all_rounds
        if bool(detail["terminal"])
    ]
    nonterminal = [
        float(detail["state_entry_latency_seconds"])
        for detail in all_rounds
        if not bool(detail["terminal"])
    ]
    terminal_seed_p99 = [
        percentile(
            [
                float(detail["state_entry_latency_seconds"])
                for detail in row.get("rounds_detail", [])
                if bool(detail["terminal"])
            ],
            0.99,
        )
        for row in seed_rows
        if any(
            bool(detail["terminal"])
            for detail in row.get("rounds_detail", [])
        )
    ]
    nonterminal_seed_p99 = [
        percentile(
            [
                float(detail["state_entry_latency_seconds"])
                for detail in row.get("rounds_detail", [])
                if not bool(detail["terminal"])
            ],
            0.99,
        )
        for row in seed_rows
        if any(
            not bool(detail["terminal"])
            for detail in row.get("rounds_detail", [])
        )
    ]
    miss_rounds = sum(int(row["deadline_miss_rounds"]) for row in seed_rows)
    miss_events = sum(int(row["deadline_miss_events"]) for row in seed_rows)
    authority_violations = sum(
        int(row.get("online_selection_authority_violations", 0))
        for row in seed_rows
    )
    upper = one_sided_t_upper(seed_p99)
    maximum = max(seed_p99)
    guarded_limit = deadline_seconds - guard_seconds
    reasons = []
    if upper > guarded_limit:
        reasons.append("seed_p99_upper_95_exceeds_guarded_deadline")
    if maximum > guarded_limit:
        reasons.append("maximum_seed_p99_exceeds_guarded_deadline")
    terminal_upper = (
        one_sided_t_upper(terminal_seed_p99)
        if len(terminal_seed_p99) == len(seed_rows)
        else None
    )
    terminal_maximum = (
        max(terminal_seed_p99)
        if len(terminal_seed_p99) == len(seed_rows)
        else None
    )
    nonterminal_upper = (
        one_sided_t_upper(nonterminal_seed_p99)
        if len(nonterminal_seed_p99) == len(seed_rows)
        else None
    )
    nonterminal_maximum = (
        max(nonterminal_seed_p99)
        if len(nonterminal_seed_p99) == len(seed_rows)
        else None
    )
    if terminal_upper is not None and terminal_upper > guarded_limit:
        reasons.append("terminal_seed_p99_upper_95_exceeds_guarded_deadline")
    if terminal_maximum is not None and terminal_maximum > guarded_limit:
        reasons.append("maximum_terminal_seed_p99_exceeds_guarded_deadline")
    if nonterminal_upper is not None and nonterminal_upper > guarded_limit:
        reasons.append(
            "nonterminal_seed_p99_upper_95_exceeds_guarded_deadline"
        )
    if nonterminal_maximum is not None and nonterminal_maximum > guarded_limit:
        reasons.append("maximum_nonterminal_seed_p99_exceeds_guarded_deadline")
    if miss_rounds:
        reasons.append("observed_deadline_miss_rounds")
    if risk_upper_bound > allowed_risk:
        reasons.append("state_risk_bound_exceeds_budget")
    if authority_violations:
        reasons.append("online_selection_authority_violation")
    return ClusterAwareCapacityCertificate(
        contract_digest=contract_digest,
        seeds=len(seed_rows),
        rounds=(
            len(all_rounds)
            if all_rounds
            else sum(int(row.get("rounds", 0)) for row in seed_rows)
        ),
        event_equivalent_count=sum(
            int(row.get("events", 0)) for row in seed_rows
        ),
        seed_p99_seconds=tuple(seed_p99),
        seed_p99_mean_seconds=statistics.mean(seed_p99),
        seed_p99_std_seconds=statistics.stdev(seed_p99),
        seed_p99_upper_95_seconds=upper,
        maximum_seed_p99_seconds=maximum,
        terminal_seed_p99_seconds=tuple(terminal_seed_p99),
        terminal_seed_p99_upper_95_seconds=terminal_upper,
        maximum_terminal_seed_p99_seconds=terminal_maximum,
        nonterminal_seed_p99_seconds=tuple(nonterminal_seed_p99),
        nonterminal_seed_p99_upper_95_seconds=nonterminal_upper,
        maximum_nonterminal_seed_p99_seconds=nonterminal_maximum,
        round_p99_seconds=percentile(latencies, 0.99) if latencies else None,
        maximum_round_seconds=max(latencies) if latencies else None,
        terminal_round_p99_seconds=(
            percentile(terminal, 0.99) if terminal else None
        ),
        nonterminal_round_p99_seconds=(
            percentile(nonterminal, 0.99) if nonterminal else None
        ),
        maximum_verified_count=(
            max(int(detail["verified_count"]) for detail in all_rounds)
            if all_rounds
            else None
        ),
        maximum_verification_overlap_fraction=(
            max(
                float(detail["verification_overlap_fraction"])
                for detail in all_rounds
            )
            if all_rounds
            else None
        ),
        deadline_miss_rounds=miss_rounds,
        deadline_miss_events=miss_events,
        risk_upper_bound=float(risk_upper_bound),
        online_selection_authority_violations=authority_violations,
        deadline_seconds=deadline_seconds,
        guard_seconds=guard_seconds,
        allowed_risk=allowed_risk,
        accepted=not reasons,
        rejection_reasons=tuple(reasons),
    )


def classify_slow_round(detail: Mapping[str, Any]) -> str:
    """Classify the measured critical path without guessing hidden causes."""

    if not bool(detail.get("deadline_miss", False)):
        return "within_slo"
    proposal = float(detail.get("proposal_seconds", 0.0))
    canonical = float(detail.get("canonical_execution_seconds", 0.0))
    collect = float(detail.get("verifier_collect_wall_seconds", 0.0))
    if (
        bool(detail.get("proposal_executed", False))
        and int(detail.get("verified_count", 0)) > 0
        and proposal > 0.0
        and canonical > 0.0
        and not bool(detail.get("preverify_all", False))
    ):
        return "serial_proposer_then_selective_canonical"
    if bool(detail.get("terminal", False)) and canonical > 0.0:
        return "terminal_canonical_path"
    if collect > canonical + 0.05:
        return "queue_ipc_or_scheduler_wait"
    return "unattributed_system_tail"


def age_bucket_summary(
    rounds: Iterable[Mapping[str, Any]],
    *,
    bucket_seconds: int = 30,
) -> list[dict[str, Any]]:
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be positive")
    grouped: dict[int, list[Mapping[str, Any]]] = {}
    for detail in rounds:
        start = int(float(detail["session_age_start_seconds"]))
        grouped.setdefault(start // bucket_seconds, []).append(detail)
    rows = []
    for bucket, items in sorted(grouped.items()):
        latencies = [
            float(item["state_entry_latency_seconds"]) for item in items
        ]
        rows.append(
            {
                "age_start_seconds": bucket * bucket_seconds,
                "age_end_seconds": (bucket + 1) * bucket_seconds,
                "rounds": len(items),
                "p50_seconds": percentile(latencies, 0.50),
                "p95_seconds": percentile(latencies, 0.95),
                "p99_seconds": percentile(latencies, 0.99),
                "maximum_seconds": max(latencies),
                "deadline_miss_rounds": sum(
                    bool(item["deadline_miss"]) for item in items
                ),
                "mean_verified_count": statistics.mean(
                    int(item["verified_count"]) for item in items
                ),
                "maximum_verified_count": max(
                    int(item["verified_count"]) for item in items
                ),
                "mean_proposal_seconds": statistics.mean(
                    float(item["proposal_seconds"]) for item in items
                ),
                "mean_canonical_execution_seconds": statistics.mean(
                    float(item["canonical_execution_seconds"])
                    for item in items
                ),
                "mean_commit_seconds": statistics.mean(
                    float(item["commit_seconds"]) for item in items
                ),
                "mean_selected_token_count": statistics.mean(
                    float(item["mean_selected_token_count"])
                    for item in items
                ),
                "maximum_selected_token_count": max(
                    int(item["maximum_selected_token_count"])
                    for item in items
                ),
            }
        )
    return rows

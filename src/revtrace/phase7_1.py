"""Phase 7.1 provenance, violation-taxonomy, and comparison helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping


@dataclass(frozen=True)
class CanonicalRuntimeProvenance:
    model: str
    configured_weight_dtype: str
    accumulation_dtype: str
    sampling_dtype: str
    attention_backend: str
    fixed_batch_shape: int
    batch_invariant_requested: bool
    temperature: float
    max_tokens: int
    terminal_and_intermediate_same_engine: bool
    intermediate_authority: str = "unspecified"
    terminal_authority: str = "unspecified"

    @property
    def digest(self) -> str:
        payload = json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    def contract_fingerprint(
        self,
        *,
        proposer_dtype: str,
        concurrency: int,
        language: str,
        arrival: str,
        contract_scope: Mapping[str, str] | None = None,
    ) -> str:
        base = (
            f"{self.model}/proposer={proposer_dtype}/c={concurrency}/"
            f"language={language}/arrival={arrival}/canonical={self.digest}"
        )
        if not contract_scope:
            return base
        normalized = []
        for key, value in sorted(contract_scope.items()):
            if not key or not value or "/" in key or "/" in value:
                raise ValueError("contract-scope fields must be non-empty and slash-free")
            normalized.append(f"{key}={value}")
        return base + "/" + "/".join(normalized)


def classify_postrun_disagreements(
    stage: Mapping[str, object],
) -> dict[str, object]:
    """Separate online authority, later replay, and transaction failures.

    The frozen runner stores only disagreement rows from the post-run replay.
    A verified row's selected value is the actual online canonical result, so
    disagreement with the later replay is canonical-repeatability drift.  An
    unverified row has no paired online canonical draw and is reported only as
    selected-vs-postrun disagreement, never as a selection-contract failure.
    """

    rows = list(stage.get("audit_violation_rows", []))
    verified = [row for row in rows if bool(row["verified"])]
    unverified = [row for row in rows if not bool(row["verified"])]
    return {
        "legacy_output_violations_selected_vs_postrun": int(
            stage.get("output_violations", 0)
        ),
        "legacy_state_violations_selected_vs_postrun": int(
            stage.get("state_violations", 0)
        ),
        "online_selection_authority_violations": 0,
        "canonical_replay_output_disagreements": len(verified),
        "canonical_replay_state_disagreements": sum(
            not bool(row["comparison"]["state_projection_token_exact"])
            for row in verified
        ),
        "unverified_selected_vs_postrun_output_disagreements": len(unverified),
        "unverified_selected_vs_postrun_state_disagreements": sum(
            not bool(row["comparison"]["state_projection_token_exact"])
            for row in unverified
        ),
        "transaction_stale_or_wrong_epoch_commits": int(
            stage.get("stale_or_replayed_result_events", 0)
        ),
        "observability_boundary": (
            "Unverified events have no paired online canonical draw; their "
            "post-run comparison is a replay audit, not E_selection."
        ),
    }


def guarded_capacity(
    *, measured_p99_seconds: float, guard_seconds: float, deadline_seconds: float
) -> dict[str, object]:
    guarded = measured_p99_seconds + guard_seconds
    return {
        "measured_p99_seconds": measured_p99_seconds,
        "guard_seconds": guard_seconds,
        "guarded_p99_seconds": guarded,
        "deadline_seconds": deadline_seconds,
        "hard_deadline_met": measured_p99_seconds <= deadline_seconds,
        "headroom_contract_met": guarded <= deadline_seconds,
    }

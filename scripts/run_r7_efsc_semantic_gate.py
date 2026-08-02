#!/usr/bin/env python3
"""Run the architecture-neutral R7.1 semantic gate.

This is a deterministic state-machine test, not a GPU serving experiment.  It
proves that the same controller can govern the distinct Qwen rollback and
Whisper previous-text projections without granting provisional ancestry.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from revtrace.feedback_coherence import (
    EFSCContract,
    ElasticFeedbackController,
    ElasticFeedbackState,
    FeedbackAction,
    FeedbackCandidate,
    FeedbackIdentity,
    QwenRollbackAdapter,
    StaleFeedbackCandidate,
    WhisperHistoryAdapter,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True
    ).strip()


def run_trace(adapter: Any, contract: EFSCContract) -> dict[str, Any]:
    controller = ElasticFeedbackController(contract)
    state = ElasticFeedbackState(
        FeedbackIdentity(adapter.name, 1, 1, 0),
        last_reset_version=0,
    )
    margins = (0.20, 0.01, 0.20, 0.20, 0.20, 0.20)
    rows: list[dict[str, Any]] = []
    violations: list[str] = []
    maximum_debt = 0
    maximum_age = 0
    for index, margin in enumerate(margins):
        state, preparation = controller.prepare_for_proposal(state, adapter)
        if preparation.action is not None:
            rows.append(
                {
                    "index": f"{index}:prepare",
                    "margin": None,
                    "action": preparation.action.value,
                    "reason": preparation.reason,
                    "mode": state.mode.value,
                    "feedback_debt": state.feedback_debt,
                    "prompt_load": state.prompt_load,
                    "ancestor_versions": sorted(state.ancestors),
                    "oldest_ancestor_age": state.oldest_ancestor_age,
                    "candidate_became_ancestor": False,
                    "pre_inference": True,
                }
            )
        before = state
        candidate = FeedbackCandidate(
            session_id=state.identity.session_id,
            contract_epoch=state.identity.contract_epoch,
            policy_version=state.identity.policy_version,
            parent_state_version=state.identity.state_version,
            token_ids=(100 + index, 200 + index),
            minimum_margin=margin,
        )
        state, decision = controller.step(state, candidate, adapter)
        non_commit = decision.action != FeedbackAction.FAST_COMMIT
        if non_commit and not state.ancestors.issubset(before.ancestors):
            violations.append(f"event-{index}: ancestry expanded")
        if (
            decision.action == FeedbackAction.PROVISIONAL_HOLD
            and state.atoms != before.atoms
        ):
            violations.append(f"event-{index}: HOLD mutated feedback")
        if (
            not decision.candidate_became_ancestor
            and state.identity.state_version in state.ancestors
        ):
            violations.append(f"event-{index}: provisional became ancestor")
        maximum_debt = max(maximum_debt, state.feedback_debt)
        maximum_age = max(maximum_age, state.oldest_ancestor_age)
        rows.append(
            {
                "index": index,
                "margin": margin,
                "action": decision.action.value,
                "reason": decision.reason,
                "mode": state.mode.value,
                "feedback_debt": state.feedback_debt,
                "prompt_load": state.prompt_load,
                "ancestor_versions": sorted(state.ancestors),
                "oldest_ancestor_age": state.oldest_ancestor_age,
                "candidate_became_ancestor": (
                    decision.candidate_became_ancestor
                ),
                "pre_inference": False,
            }
        )

    stale_rejected = False
    try:
        controller.step(
            state,
            FeedbackCandidate(
                session_id=state.identity.session_id,
                contract_epoch=state.identity.contract_epoch,
                policy_version=state.identity.policy_version + 1,
                parent_state_version=state.identity.state_version,
                token_ids=(999,),
                minimum_margin=1.0,
            ),
            adapter,
        )
    except StaleFeedbackCandidate:
        stale_rejected = True

    actions = [row["action"] for row in rows]
    required = {item.value for item in FeedbackAction}
    return {
        "adapter": adapter.name,
        "events": rows,
        "action_sequence": actions,
        "action_coverage": sorted(set(actions)),
        "all_actions_observed": set(actions) == required,
        "stale_candidate_rejected": stale_rejected,
        "maximum_feedback_debt": maximum_debt,
        "maximum_ancestor_age": maximum_age,
        "violations": violations,
        "pass": (
            not violations
            and stale_rejected
            and set(actions) == required
            and maximum_debt <= contract.maximum_feedback_debt
            and maximum_age <= contract.maximum_influence_windows
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/revtrace_r7_efsc_gate.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/r7_efsc/semantic_gate.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = REPO_ROOT
    config_path = (root / args.config).resolve()
    output_path = (root / args.output).resolve()
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    frozen = payload["shared_controller"]["frozen_non_threshold_parameters"]
    # Normalized margins exercise controller semantics only.  Deployment
    # thresholds are generated by R7.2 and are never read from these values.
    semantic_contract = EFSCContract(
        enter_margin=0.05,
        exit_margin=0.10,
        minimum_hold_windows=int(frozen["minimum_hold_windows"]),
        safe_streak_required=int(frozen["safe_streak_required"]),
        maximum_quarantine_windows=int(
            frozen["maximum_quarantine_windows"]
        ),
        maximum_feedback_debt=int(frozen["maximum_feedback_debt"]),
        maximum_influence_windows=int(
            frozen["maximum_influence_windows"]
        ),
        maximum_prompt_tokens=224,
        decay_suffix_tokens=32,
    )
    results = [
        run_trace(QwenRollbackAdapter(), semantic_contract),
        run_trace(WhisperHistoryAdapter(223), semantic_contract),
    ]
    action_sequences = {tuple(item["action_sequence"]) for item in results}
    source_path = root / "src/revtrace/feedback_coherence.py"
    report = {
        "experiment_id": "revtrace-r7.1-cross-architecture-semantic-gate",
        "evidence_tier": "deterministic semantic state-machine test",
        "not_serving_evidence": True,
        "config_path": str(config_path.relative_to(root)),
        "config_sha256": sha256_file(config_path),
        "controller_source_path": str(source_path.relative_to(root)),
        "controller_source_sha256": sha256_file(source_path),
        "controller_class_source_sha256": hashlib.sha256(
            inspect.getsource(ElasticFeedbackController).encode("utf-8")
        ).hexdigest(),
        "git_commit_at_run": git_value(root, "rev-parse", "HEAD"),
        "git_worktree_dirty_at_run": bool(
            git_value(root, "status", "--porcelain")
        ),
        "semantic_contract": asdict(semantic_contract),
        "architectures": results,
        "shared_action_sequence": len(action_sequences) == 1,
        "qwen_gate_is_mandatory_before_whisper_performance": (
            payload["phases"]["R7.Q0"]["must_complete_before"] == "R7.3"
        ),
        "decision": (
            "PASS_R7_1_SEMANTICS"
            if all(item["pass"] for item in results)
            and len(action_sequences) == 1
            else "FAIL_R7_1_SEMANTICS"
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(report["decision"] != "PASS_R7_1_SEMANTICS")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Replay the frozen 21 Whisper state pairs through the W state ledger.

This is a control-plane regression, not a new model experiment.  The paired
model outputs were produced by the legal Phase 4 singleton/batch intervention;
the test verifies that Prompt-State Holdback admits only the recorded
singleton authority and rejects stale/wrong-parent commits.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from revtrace.whisper_state import (
    PromptState,
    PromptTransition,
    StalePromptTransition,
    WhisperVersion,
    append_prompt_tokens,
    commit_prompt_transition,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiny-pairs", type=Path, required=True)
    parser.add_argument("--base-pairs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-of-previous-token", type=int, default=50360)
    parser.add_argument("--max-prompt-tokens", type=int, default=224)
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    rows: list[dict[str, Any]] = []
    stale_rejections = 0
    terminal_authority = 0
    for path in (args.tiny_pairs, args.base_pairs):
        payload = load(path)
        for index, pair in enumerate(payload["pairs"]):
            if bool(pair["terminal_difference"]):
                terminal_authority += 1
                rows.append({
                    "model": payload["model"],
                    "pair_sha256": pair["pair_sha256"],
                    "state_eligible": False,
                    "protected": True,
                    "output_authority": "singleton-canonical",
                    "canonical_text": pair["canonical"]["text"],
                    "proposal_text": pair["proposer"]["text"],
                })
                continue
            version = WhisperVersion(
                f"{payload['model']}:{index}", 1, 1, 0
            )
            state = PromptState(version, (), "")
            canonical = pair["canonical"]
            proposal = pair["proposer"]
            canonical_state = append_prompt_tokens(
                (),
                tuple(canonical["token_ids"]),
                start_of_previous_token=args.start_of_previous_token,
                maximum_tokens=args.max_prompt_tokens,
            )
            proposal_state = append_prompt_tokens(
                (),
                tuple(proposal["token_ids"]),
                start_of_previous_token=args.start_of_previous_token,
                maximum_tokens=args.max_prompt_tokens,
            )
            # The pair is known-unsafe by construction.  Holdback exposes the
            # proposal only provisionally and commits the authority outcome.
            transition = PromptTransition(
                parent=version,
                selected_token_ids=canonical_state,
                selected_text=str(canonical["text"]),
                source="singleton-canonical-known-pair",
                terminal=bool(pair["terminal_difference"]),
                minimum_margin=None,
            )
            committed = commit_prompt_transition(state, transition)
            protected = (
                committed.prompt_token_ids
                == canonical_state
                and committed.prompt_text == canonical["text"]
            )
            try:
                commit_prompt_transition(state, PromptTransition(
                    parent=WhisperVersion(
                        version.session_id,
                        version.contract_epoch,
                        version.policy_version,
                        version.state_version + 1,
                    ),
                    selected_token_ids=proposal_state,
                    selected_text=str(proposal["text"]),
                    source="stale-proposal",
                    terminal=False,
                    minimum_margin=None,
                ))
            except StalePromptTransition:
                stale_rejections += 1
            rows.append({
                "model": payload["model"],
                "pair_sha256": pair["pair_sha256"],
                "state_eligible": True,
                "protected": protected,
                "canonical_text": canonical["text"],
                "proposal_text": proposal["text"],
            })
    state_rows = [row for row in rows if row["state_eligible"]]
    protected = sum(bool(row["protected"]) for row in state_rows)
    passed = (
        len(rows) == 21
        and len(state_rows) == protected == stale_rejections == 15
        and terminal_authority == 6
    )
    result = {
        "schema_version": 1,
        "study": "W2 frozen Whisper pair state-adapter regression",
        "decision": (
            "W2_KNOWN_PAIR_REGRESSION_PASS"
            if passed else "W2_KNOWN_PAIR_REGRESSION_FAIL"
        ),
        "counts": {
            "known_pairs": len(rows),
            "state_eligible_pairs": len(state_rows),
            "known_pairs_protected": protected,
            "stale_parent_commits_rejected": stale_rejections,
            "terminal_authority_pairs": terminal_authority,
        },
        "config": {
            "start_of_previous_token": args.start_of_previous_token,
            "max_prompt_tokens": args.max_prompt_tokens,
            "state_semantics": (
                "raw-segment-token-history-v5-deferred-authority"
            ),
        },
        "rows": rows,
        "claim_boundary": (
            "This projects frozen Phase 4 real-weight segment outcomes into "
            "the current raw-token state adapter to test the W control plane; "
            "terminal-only pairs receive singleton-canonical stable-output "
            "authority but no future-state authority; "
            "it does not reuse the legacy text-prompt semantics as W3 "
            "mechanism evidence and does not add prevalence evidence."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "decision": result["decision"], **result["counts"]
    }, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

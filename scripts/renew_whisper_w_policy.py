#!/usr/bin/env python3
"""Renew a Whisper policy epoch from an audit-caught failure root."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--adaptation-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    audit = json.loads(
        args.adaptation_audit.read_text(encoding="utf-8")
    )
    caught = [
        row for row in audit["audit_rows"] if row["state_error"]
    ]
    if not caught:
        raise ValueError("adaptation audit contains no caught failure root")
    old = float(policy["selected_policy"]["threshold"])
    floor = max(float(row["minimum_margin"]) for row in caught) + 1e-6
    renewed = max(old, floor)
    output = {
        "schema_version": 1,
        "study": "Whisper contract-scoped policy renewal",
        "decision": "POLICY_EPOCH_RENEWED_REQUIRES_INDEPENDENT_VALIDATION",
        "contract": policy["contract"],
        "old_threshold": old,
        "caught_failure_floor": floor,
        "renewed_threshold": renewed,
        "caught_roots": caught,
        "source_files": [
            {"path": str(args.policy), "sha256": sha256(args.policy)},
            {
                "path": str(args.adaptation_audit),
                "sha256": sha256(args.adaptation_audit),
            },
        ],
        "claim_boundary": (
            "Adaptation rows only raise the failure floor. They are excluded "
            "from the independent validation confidence sequence."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "old_threshold": old,
        "caught_failure_floor": floor,
        "renewed_threshold": renewed,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

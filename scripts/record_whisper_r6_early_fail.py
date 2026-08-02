#!/usr/bin/env python3
"""Record an irreversible zero-error risk-gate failure from audit checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, action="append", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkpoints = [json.loads(path.read_text(encoding="utf-8")) for path in args.checkpoint]
    caught = [row for item in checkpoints for row in item.get("caught_rows", [])]
    if not caught:
        raise ValueError("early failure requires at least one caught state error")
    output = {
        "schema_version": 1,
        "study": "Whisper c16 R6 independent risk audit early stop",
        "decision": "RISK_GATE_EARLY_FAIL",
        "predeclared_gate": "caught_state_errors == 0",
        "counts": {
            "risk_eligible_entries": sum(int(item["risk_entries"]) for item in checkpoints),
            "pre_outcome_randomized_audits": sum(int(item["audits"]) for item in checkpoints),
            "caught_state_errors": len(caught),
            "streams": len(checkpoints),
        },
        "caught_rows": caught,
        "source_files": [
            {"role": "audit-checkpoint", "path": str(path), "sha256": sha256(path)}
            for path in args.checkpoint
        ] + [{"role": "policy", "path": str(args.policy), "sha256": sha256(args.policy)}],
        "claim_boundary": (
            "The target 30k entries per stream was not completed because one "
            "repeat-stable caught error irreversibly violated the predeclared "
            "zero-caught-error gate. This is failure evidence, not a risk certificate."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": output["decision"], **output["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

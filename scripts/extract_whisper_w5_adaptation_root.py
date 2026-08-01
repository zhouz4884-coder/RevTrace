#!/usr/bin/env python3
"""Extract fail-closed W5 state mismatches as adaptation-only W4 roots.

The extracted rows may renew a contextual risk policy, but the source W5
epoch and these roots must never contribute to the renewed confidence
certificate or the final performance matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    rows = []
    for event in payload.get("events", []):
        if not bool(event.get("post_timing_stable_state_mismatch", False)):
            continue
        row = dict(event)
        # The renewal builder consumes the legal same-input canonical outcome
        # through this explicit adaptation-only state-error label.
        row["state_error"] = True
        rows.append(row)
    if not rows:
        raise ValueError("no fail-closed stable-state mismatch in W5 input")
    if any(bool(row.get("terminal", False)) for row in rows):
        raise ValueError("terminal mismatches require full terminal authority")

    output = {
        "schema_version": 1,
        "study": "Whisper W5 fail-closed adaptation root extraction",
        "decision": "ADAPTATION_ROOTS_EXTRACTED_EXCLUDE_SOURCE_EPOCH",
        "claim_boundary": (
            "adaptation-only; excluded from renewed risk certificate and "
            "final W5 performance evidence"
        ),
        "source": {
            "path": str(args.input),
            "sha256": sha256(args.input),
            "seed": payload.get("config", {}).get("seed"),
            "model": payload.get("model"),
        },
        "counts": {"adaptation_roots": len(rows)},
        "audit_rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

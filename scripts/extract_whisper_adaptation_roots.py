#!/usr/bin/env python3
"""Project repeat-stable workload mismatches into adaptation-only roots.

The output is deliberately not a risk certificate. It contains only failures
that the workload's delayed same-state canonical replay reproduced while its
second singleton replay remained stable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    roots: list[dict[str, Any]] = []
    sources: list[dict[str, str]] = []
    for path in args.workload:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sources.append({"path": str(path), "sha256": sha256(path)})
        for row in payload["events"]:
            if not bool(row.get("post_timing_stable_state_mismatch")):
                continue
            if bool(row.get("post_timing_canonical_repeat_state_mismatch")):
                raise ValueError(
                    f"canonical repeat is unstable for {path}: "
                    f"session={row['session_id']} window={row['window_index']}"
                )
            roots.append({
                "episode": len(roots),
                "session_id": int(row["session_id"]),
                "window_index": int(row["window_index"]),
                "minimum_margin": float(row["minimum_margin"]),
                "prior_prompt_tokens": int(row["prior_prompt_tokens"]),
                "next_prompt_tokens": int(row["next_prompt_tokens"]),
                "terminal": bool(row["terminal"]),
                "state_error": True,
                "output_error": bool(
                    row.get("post_timing_stable_output_mismatch")
                ),
                "canonical_repeat_stable": True,
                "source_workload_sha256": sha256(path),
            })
    if not roots:
        raise ValueError("no repeat-stable workload state mismatches")

    output = {
        "schema_version": 1,
        "study": "adaptation-only roots from delayed same-state workload replay",
        "audit_rows": roots,
        "counts": {"caught_state_errors": len(roots)},
        "source_files": sources,
        "claim_boundary": (
            "These repeat-stable roots may adapt a later policy epoch but are "
            "excluded from its independent risk certificate."
        ),
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

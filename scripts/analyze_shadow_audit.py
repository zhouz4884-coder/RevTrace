from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze caught-error diagnostics from a shadow audit."
    )
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows: list[dict[str, Any]] = []
    for path in args.inputs:
        record = json.loads(path.read_text(encoding="utf-8"))
        config = record["config"]
        for audit in record["audit_records"]:
            if not (audit["output_error"] or audit["state_error"]):
                continue
            rows.append(
                {
                    "source": path.as_posix(),
                    "model": record["model"],
                    "concurrency": config["concurrency"],
                    "seed": config["seed"],
                    "ticket": audit["ticket"],
                    "session_id": audit.get("session_id", ""),
                    "episode": audit.get("episode", ""),
                    "chunk_index": audit.get("chunk_index", ""),
                    "minimum_margin": audit["minimum_margin"],
                    "output_error": audit["output_error"],
                    "state_error": audit["state_error"],
                    "job_sha256": audit["job_sha256"],
                    "proposer_projection_sha256": audit[
                        "proposer_projection_sha256"
                    ],
                    "canonical_projection_sha256": audit[
                        "canonical_projection_sha256"
                    ],
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source",
        "model",
        "concurrency",
        "seed",
        "ticket",
        "session_id",
        "episode",
        "chunk_index",
        "minimum_margin",
        "output_error",
        "state_error",
        "job_sha256",
        "proposer_projection_sha256",
        "canonical_projection_sha256",
    ]
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"caught_records": len(rows), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

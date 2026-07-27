#!/usr/bin/env python3
"""Finalize and hash-audit the RevTrace Phase 3A evidence bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result-root",
        type=Path,
        default=ROOT / "results" / "phase3" / "adaptive_control",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=ROOT / "artifact" / "phase3-adaptive-control-v1",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def main() -> int:
    args = parse_args()
    semantic = read_json(args.result_root / "semantic_gate.json")
    envelope_paths = {
        "initial_0p6b_c16": (
            args.result_root / "envelopes" / "initial-0p6b-c16.json"
        ),
        "unsafe_0p6b_c64": (
            args.result_root / "envelopes" / "unsafe-0p6b-c64.json"
        ),
        "model_1p7b_c16": (
            args.result_root / "envelopes" / "model-1p7b-c16.json"
        ),
        "return_0p6b_c16": (
            args.result_root / "envelopes" / "return-0p6b-c16.json"
        ),
    }
    envelopes = {
        name: read_json(path) for name, path in envelope_paths.items()
    }
    deployed = read_json(args.result_root / "deployed" / "summary.json")
    selected = {
        name: payload["selected_policy"]["threshold"]
        for name, payload in envelopes.items()
    }
    envelope_pass = all(
        payload["decision"] == "ADAPTIVE_POLICY_ENVELOPE_PASS"
        for payload in envelopes.values()
    )
    repair_pass = (
        selected["initial_0p6b_c16"] == 0.05
        and selected["unsafe_0p6b_c64"] >= 0.10
        and selected["model_1p7b_c16"] >= 0.10
        and selected["return_0p6b_c16"] == 0.05
    )
    failure_ledger_pass = (
        envelopes["unsafe_0p6b_c64"]["frozen_caught_margins"]
        == [0.078125]
        and envelopes["model_1p7b_c16"]["frozen_caught_margins"]
        == [0.0625]
    )
    deployed_pass = (
        deployed["decision"] == "PHASE3A_DEPLOYED_SEQUENCE_PASS"
        and deployed["metrics"]["minimum_gpu_normalized_speedup"] >= 2.0
        and deployed["metrics"]["total_deadline_misses"] == 0
        and deployed["metrics"]["total_observed_violations"] == 0
    )
    passed = (
        semantic["decision"] == "PHASE3A_SEMANTIC_CONTROL_PASS"
        and envelope_pass
        and repair_pass
        and failure_ledger_pass
        and deployed_pass
    )
    policy_rows = []
    for stage, payload in envelopes.items():
        for item in payload["policies"]:
            policy_rows.append(
                {
                    "stage": stage,
                    "model": payload["source_model"],
                    "concurrency": payload["source_config"][
                        "concurrency"
                    ],
                    **item,
                    "selected": (
                        item["threshold"]
                        == payload["selected_policy"]["threshold"]
                    ),
                }
            )
    args.result_root.mkdir(parents=True, exist_ok=True)
    table_path = args.result_root / "POLICY_TABLE.csv"
    with table_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(policy_rows[0])
        )
        writer.writeheader()
        writer.writerows(policy_rows)
    summary = {
        "schema_version": 1,
        "study": "RevTrace Phase 3A adaptive risk control",
        "decision": (
            "PHASE3A_ADAPTIVE_CONTROL_PASS"
            if passed
            else "PHASE3A_ADAPTIVE_CONTROL_FAIL"
        ),
        "source_commit": source_commit(),
        "selected_thresholds": selected,
        "gates": {
            "semantic_control": semantic["decision"],
            "simultaneous_envelopes": envelope_pass,
            "automatic_policy_repair": repair_pass,
            "failure_ledger_retained": failure_ledger_pass,
            "deployed_sequence": deployed["decision"],
        },
        "deployed_metrics": deployed["metrics"],
        "claim_boundaries": [
            "Threshold selection is performed inside a preregistered simultaneous policy envelope.",
            "The finite grid is an implementation approximation to risk-priced control, not the method definition.",
            "Previously caught real failures are hard policy exclusions and are never diluted by later safe events.",
            "The c64 contract remains fail closed during certification because its terminal arithmetic path is not certified.",
            "Shadow-audit time is excluded from serving performance.",
            "The result is a statistical state-disagreement contract, not deterministic floating-point exactness.",
        ],
    }
    (args.result_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = f"""# RevTrace Phase 3A report

Decision: **{summary['decision']}**

## Automatic policy sequence

| Stage | Selected threshold |
|---|---:|
| 0.6B / c16 initial | {selected['initial_0p6b_c16']:.3f} |
| 0.6B / c64 | {selected['unsafe_0p6b_c64']:.3f} |
| 1.7B / c16 | {selected['model_1p7b_c16']:.3f} |
| 0.6B / c16 fresh return epoch | {selected['return_0p6b_c16']:.3f} |

The controller retained the frozen c64 error at margin 0.078125 and the 1.7B
error at margin 0.0625 as hard exclusions.  Later zero-error audits cannot
erase those failures.

## Deployed recovery

- Minimum wall speedup: {deployed['metrics']['minimum_wall_speedup']:.3f}x
- Minimum GPU-normalized speedup: {deployed['metrics']['minimum_gpu_normalized_speedup']:.3f}x
- Deadline misses: {deployed['metrics']['total_deadline_misses']}
- Observed output/state/stale violations: {deployed['metrics']['total_observed_violations']}

## Evidence boundary

The shadow studies establish a simultaneous, time-uniform statistical contract
over execution events.  They are not latency experiments and do not establish
bitwise deterministic inference.  The c64 stage is fail closed until a c64
terminal canonical path is independently certified.
"""
    (args.result_root / "REPORT.md").write_text(
        report, encoding="utf-8"
    )

    if args.artifact_root.exists():
        shutil.rmtree(args.artifact_root)
    for directory in (
        "config",
        "docs",
        "results",
        "scripts",
        "src",
    ):
        (args.artifact_root / directory).mkdir(
            parents=True, exist_ok=True
        )
    shutil.copy2(
        ROOT / "configs" / "revtrace_adaptive_control_gate.json",
        args.artifact_root / "config",
    )
    shutil.copy2(
        ROOT / "docs" / "protocols" / "ADAPTIVE_CONTROL_CONTRACT.md",
        args.artifact_root / "docs",
    )
    shutil.copytree(
        args.result_root,
        args.artifact_root / "results",
        dirs_exist_ok=True,
    )
    for source in (
        ROOT / "scripts" / "compile_policy_envelope.py",
        ROOT / "scripts" / "simulate_phase3a_control.py",
        ROOT / "scripts" / "remote" / "run_phase3a_deployed_sequence.py",
        ROOT / "scripts" / "remote" / "run_phase3a_shadow_sequence.sh",
    ):
        shutil.copy2(source, args.artifact_root / "scripts")
    for source in (
        ROOT / "src" / "revtrace" / "control.py",
        ROOT / "src" / "revtrace" / "risk.py",
    ):
        shutil.copy2(source, args.artifact_root / "src")
    (args.artifact_root / "README.md").write_text(
        report, encoding="utf-8"
    )
    manifest_files = []
    for path in sorted(args.artifact_root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            manifest_files.append(
                {
                    "path": path.relative_to(args.artifact_root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    manifest = {
        "schema_version": 1,
        "source_commit": summary["source_commit"],
        "files": manifest_files,
    }
    (args.artifact_root / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

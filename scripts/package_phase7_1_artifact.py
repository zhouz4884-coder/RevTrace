#!/usr/bin/env python3
"""Build the compact, hash-audited Phase 7.1 correction artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "artifact" / "phase7-1-evidence-repair-v1"
FILES = [
    "README.md",
    "docs/CLAIM_BOUNDARIES.md",
    "docs/reports/phase7_1_corrections_and_performance.md",
    "docs/reports/phase7_reviewer_defense_report.md",
    "docs/research/phase7_related_work_collision_matrix.md",
    "results/phase7/PAPER_TABLES.md",
    "results/phase7/summary.json",
    "results/phase7/sota/matrix.json",
    "results/phase7/c64_queue/summary.json",
    "results/phase7_1/PERFORMANCE_COMPARISON.md",
    "results/phase7_1/summary.json",
    "results/phase7_1/performance_comparison.json",
    "results/phase7_1/canonical_provenance_audit.json",
    "results/phase7_1/capacity_audit.json",
    "results/phase7_1/c14_capacity/raw.json",
    "results/phase7_1/c14_capacity/run.log",
    "src/revtrace/phase7.py",
    "src/revtrace/phase7_1.py",
    "scripts/finalize_phase7_c64_queue.py",
    "scripts/run_phase7_reviewer_defense.py",
    "scripts/run_phase7_1_audit.py",
    "scripts/remote/run_phase5a_live_adaptive.py",
    "scripts/remote/run_phase7_1_c14_capacity.sh",
    "tests/test_phase7.py",
    "tests/test_phase7_1.py",
]


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    entries = {}
    for relative in FILES:
        source = ROOT / relative
        if not source.exists():
            raise FileNotFoundError(relative)
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        entries[relative] = {
            "bytes": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    manifest = {
        "schema_version": 1,
        "artifact": "phase7-1-evidence-repair-v1",
        "claim_boundary": (
            "The c14 result is a live guarded-capacity point. Published SOTA "
            "headlines remain contextual because their workloads differ. "
            "Phase 7D replay disagreement is not an online transaction error."
        ),
        "files": entries,
    }
    (DEST / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

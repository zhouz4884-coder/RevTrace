#!/usr/bin/env python3
"""Build the compact, hash-audited Phase 7 artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "artifact" / "phase7-reviewer-defense-v1"
FILES = [
    "README.md",
    "configs/revtrace_phase7_reviewer_defense_gate.json",
    "docs/reports/phase7_reviewer_defense_report.md",
    "docs/research/phase7_related_work_collision_matrix.md",
    "results/phase7/summary.json",
    "results/phase7/PAPER_TABLES.md",
    "results/phase7/SOURCE_ARCHIVE_MANIFEST.json",
    "results/phase7/SOURCE_PROBE_MANIFEST.json",
    "results/phase7/sota/matrix.json",
    "results/phase7/sota/revision_adaptations.json",
    "results/phase7/ablation/summary.json",
    "results/phase7/risk_sensitivity/summary.json",
    "results/phase7/c64_queue/summary.json",
    "results/phase7/c64_queue/raw-active16-waves-en.json",
    "results/phase7/c64_queue/raw-invalid-mixed-cert.json",
    "results/phase7/source_probes/summary.json",
    "src/revtrace/phase6.py",
    "src/revtrace/phase7.py",
    "scripts/run_phase7_reviewer_defense.py",
    "scripts/finalize_phase7_c64_queue.py",
    "scripts/remote/run_phase7d_c64_queue.sh",
    "tests/test_phase6.py",
    "tests/test_phase7.py",
]


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    entries = []
    for relative in FILES:
        source = ROOT / relative
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        entries.append(
            {
                "path": relative,
                "bytes": source.stat().st_size,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "schema_version": 1,
        "artifact": "phase7-reviewer-defense-v1",
        "claim_boundary": "Compact code/results artifact; external source archives and model weights are referenced by hash, not redistributed.",
        "files": entries,
    }
    (DEST / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

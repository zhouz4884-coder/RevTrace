#!/usr/bin/env python3
"""Build the compact, hash-auditable tail-robust closure artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifact" / "tail-robust-admission-closure-v1"

FILES = (
    "README.md",
    "configs/revtrace_tail_robust_closure.json",
    "docs/CLAIM_BOUNDARIES.md",
    "docs/protocols/TAIL_ROBUST_ADMISSION_CONTRACT.md",
    "docs/reports/tail_robust_admission_closure.md",
    "docs/reports/tail_robust_change_diagnosis.md",
    "docs/roadmap/PHASES.md",
    "results/tail_robust/REPORT.md",
    "results/tail_robust/summary.json",
    "results/tail_robust/root_cause_diagnosis.json",
    "results/tail_robust/capacity_contracts.json",
    "results/tail_robust/operating_envelope.csv",
    "results/tail_robust/age_profile.csv",
    "scripts/build_tail_robust_artifact.py",
    "scripts/audit_tail_robust_artifact.py",
    "scripts/finalize_tail_robust_closure.py",
    "scripts/remote/run_phase5a_live_adaptive.py",
    "scripts/remote/run_tail_robust_closure.sh",
    "scripts/remote/run_tail_c12_age_profile.sh",
    "src/revtrace/capacity.py",
    "src/revtrace/phase6.py",
    "tests/test_capacity.py",
    "tests/test_phase6.py",
    "tests/test_tail_robust_finalizer.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    missing = [relative for relative in FILES if not (ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError(f"artifact inputs missing: {missing}")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    manifest_files = {}
    for relative in FILES:
        source = ROOT / relative
        destination = OUTPUT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        manifest_files[relative] = {
            "bytes": destination.stat().st_size,
            "sha256": digest(destination),
        }
    manifest = {
        "schema_version": 1,
        "artifact": OUTPUT.name,
        "claim_boundary": (
            "The artifact separates the rejected c14 tail point, the fixed "
            "c12 held-out capacity contract, and the optional 120-second age "
            "boundary. Statistical admission is not deterministic inference."
        ),
        "files": manifest_files,
    }
    (OUTPUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"artifact": str(OUTPUT), "files": len(FILES)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

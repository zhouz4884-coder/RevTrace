#!/usr/bin/env python3
"""Build a compact, hash-audited Phase 4 evidence artifact."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifact" / "phase4-adaptation-generality-v1"

FILES = [
    "README.md",
    "docs/CLAIM_BOUNDARIES.md",
    "docs/reports/phase4_adaptation_generality_report.md",
    "configs/revtrace_phase4a_risk_window_gate.json",
    "configs/revtrace_phase4b_whisper_feedback_gate.json",
    "configs/revtrace_phase4d_active_mining_gate.json",
    "configs/experiment_registry.json",
    "results/phase4/summary.json",
    "results/phase4/PAPER_TABLES.md",
    "results/phase4/risk_window/summary.json",
    "results/phase4/slackguard/summary.json",
    "results/phase4/damage_population/summary.json",
    "results/phase4/whisper_feedback_expanded/whisper-tiny-en.json",
    "results/phase4/whisper_feedback_expanded/whisper-base-en.json",
    "results/phase4/active_mining/qwen3-asr-0.6b.json",
    "results/phase4/active_mining/qwen3-asr-1.7b.json",
    "scripts/evaluate_phase4a_risk_window.py",
    "scripts/evaluate_phase4c_slackguard_feasibility.py",
    "scripts/evaluate_phase4d_damage_population.py",
    "scripts/finalize_phase4.py",
    "scripts/remote/run_whisper_feedback_gate.py",
    "scripts/remote/run_phase4b_whisper_expanded.sh",
    "scripts/remote/run_phase4d_active_mining.py",
    "scripts/remote/run_phase4d_active_mining.sh",
    "src/revtrace/risk_window.py",
    "src/revtrace/feedback_metrics.py",
    "src/revtrace/amplification.py",
    "src/revtrace/mining.py",
    "tests/test_risk_window.py",
    "tests/test_whisper_feedback_metrics.py",
    "tests/test_contamination_tail.py",
    "tests/test_active_mining.py",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    missing = [item for item in FILES if not (ROOT / item).is_file()]
    if missing:
        raise FileNotFoundError(f"artifact inputs missing: {missing}")
    if OUT.exists():
        resolved = OUT.resolve()
        artifact_root = (ROOT / "artifact").resolve()
        if artifact_root not in resolved.parents:
            raise RuntimeError(f"refusing to replace path outside artifact: {OUT}")
        shutil.rmtree(OUT)
    for relative in FILES:
        source = ROOT / relative
        target = OUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    readme = """# RevTrace Phase 4 adaptation and generality artifact

This compact artifact contains the Phase 4 configurations, executable analysis
and remote-runner code, semantic tests, exact compact result records, and the
claim-boundary report.

Evidence tiers remain separate:

- `risk_window` is split-sample controller replay, not a live c16/c64 service;
- Whisper results use real weights and legal execution-shape interventions;
- SlackGuard records a physical NO-GO for full-request audit quanta;
- active-mining yield is targeted mechanism coverage, not production
  prevalence.

Run the local checks from the repository root:

```powershell
python -m pytest -q
python scripts/finalize_phase4.py
python scripts/validate_repository.py
```
"""
    (OUT / "ARTIFACT_README.md").write_text(readme, encoding="utf-8")
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    entries = []
    for path in sorted(
        item for item in OUT.rglob("*") if item.is_file()
    ):
        entries.append(
            {
                "path": path.relative_to(OUT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
        )
    manifest = {
        "schema_version": 1,
        "artifact": "phase4-adaptation-generality-v1",
        "source_commit_before_freeze": commit,
        "files": entries,
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "artifact": str(OUT),
                "files": len(entries),
                "source_commit": commit,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

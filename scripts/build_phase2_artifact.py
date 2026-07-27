from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifact" / "phase2-risk-tail-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    mappings = {
        ROOT / "docs" / "reports" / "phase2_risk_tail_report.md":
            OUTPUT / "REPORT.md",
        ROOT / "docs" / "CLAIM_BOUNDARIES.md":
            OUTPUT / "CLAIM_BOUNDARIES.md",
        ROOT / "configs" / "revtrace_terminal_canonical_gate.json":
            OUTPUT / "config" / "terminal_gate.json",
        ROOT / "results" / "phase2" / "MANIFEST.json":
            OUTPUT / "results" / "SOURCE_MANIFEST.json",
        ROOT / "scripts" / "simulate_anytime_risk.py":
            OUTPUT / "scripts" / "simulate_anytime_risk.py",
        ROOT / "scripts" / "analyze_shadow_audit.py":
            OUTPUT / "scripts" / "analyze_shadow_audit.py",
        ROOT / "scripts" / "remote" / "run_shadow_risk_audit.py":
            OUTPUT / "scripts" / "run_shadow_risk_audit.py",
        ROOT / "scripts" / "remote" / "run_revtrace_dual_gpu.py":
            OUTPUT / "scripts" / "run_revtrace_dual_gpu.py",
        ROOT / "src" / "revtrace" / "risk.py":
            OUTPUT / "src" / "risk.py",
    }
    result_root = ROOT / "results" / "phase2"
    for source in result_root.rglob("*"):
        if not source.is_file() or "logs" in source.parts:
            continue
        mappings[source] = (
            OUTPUT
            / "results"
            / "evidence"
            / source.relative_to(result_root)
        )
    for source, target in mappings.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    files = sorted(path for path in OUTPUT.rglob("*") if path.is_file())
    manifest = {
        "schema_version": 1,
        "scope": (
            "Phase 2 real two-GPU terminal-tail results, randomized risk "
            "audit evidence, negative interventions, code, and bounded report"
        ),
        "files": [
            {
                "path": path.relative_to(OUTPUT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    (OUTPUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"files": len(files), "output": str(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

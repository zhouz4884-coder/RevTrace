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
        ROOT / "configs" / "revtrace_terminal_reserved_gate.json":
            OUTPUT / "config" / "terminal_reserved_gate.json",
        ROOT / "configs" / "revtrace_risk_audit_gate.json":
            OUTPUT / "config" / "risk_v1_gate.json",
        ROOT / "configs" / "revtrace_risk_audit_v2_gate.json":
            OUTPUT / "config" / "risk_v2_gate.json",
        ROOT / "docs" / "protocols" / "ANYTIME_RISK_CONTRACT.md":
            OUTPUT / "PROTOCOL.md",
        ROOT / "deployment" / "phase2_environment.json":
            OUTPUT / "deployment" / "environment.json",
        ROOT / "results" / "phase2" / "MANIFEST.json":
            OUTPUT / "results" / "SOURCE_MANIFEST.json",
        ROOT / "scripts" / "simulate_anytime_risk.py":
            OUTPUT / "scripts" / "simulate_anytime_risk.py",
        ROOT / "scripts" / "finalize_phase2.py":
            OUTPUT / "scripts" / "finalize_phase2.py",
        ROOT / "scripts" / "build_phase2_artifact.py":
            OUTPUT / "scripts" / "build_phase2_artifact.py",
        ROOT / "scripts" / "analyze_shadow_audit.py":
            OUTPUT / "scripts" / "analyze_shadow_audit.py",
        ROOT / "scripts" / "remote" / "run_shadow_risk_audit.py":
            OUTPUT / "scripts" / "run_shadow_risk_audit.py",
        ROOT / "scripts" / "remote" / "run_revtrace_dual_gpu.py":
            OUTPUT / "scripts" / "run_revtrace_dual_gpu.py",
        ROOT / "scripts" / "remote" / "run_phase2_risk_v2_repair.sh":
            OUTPUT / "scripts" / "run_phase2_risk_v2_repair.sh",
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
    summary = json.loads(
        (
            ROOT / "results" / "phase2" / "risk_v1" / "summary.json"
        ).read_text(encoding="utf-8")
    )
    readme = f"""# RevTrace Phase 2 frozen artifact

Decision: `{summary["decision"]}`

This bundle contains compact real two-RTX-3090 system records, five-run
replication tables, randomized shadow-audit evidence, negative interventions,
the frozen risk protocol, exact runner sources, and SHA-256 manifests.

Evidence boundaries:

- performance numbers are measured wall-clock and GPU-normalized results;
- natural audit rows are repeated execution events, not independent utterances;
- the risk bound is disagreement with a frozen canonical execution, not WER;
- zero observed errors are not a deterministic arithmetic certificate;
- v1 failures remain evidence and are not relabeled as v2 validation;
- full logs, models, caches, and environments remain on the experiment disk.

Validate from the repository root:

```powershell
python -m pytest -q
python scripts/validate_repository.py
```
"""
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8")
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

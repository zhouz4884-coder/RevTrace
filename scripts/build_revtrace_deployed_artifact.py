from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifact" / "phase1-deployed-system-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    mappings = {
        ROOT / "docs" / "reports" / "revtrace_deployed_system_report.md":
            OUTPUT / "REPORT.md",
        ROOT / "configs" / "revtrace_deployed_gate.json":
            OUTPUT / "config" / "gate.json",
        ROOT / "results" / "phase1" / "deployed_v1" / "summary.json":
            OUTPUT / "results" / "summary.json",
        ROOT / "results" / "phase1" / "deployed_v1" / "MANIFEST.json":
            OUTPUT / "results" / "SOURCE_MANIFEST.json",
        ROOT / "scripts" / "remote" / "run_revtrace_dual_gpu.py":
            OUTPUT / "scripts" / "run_dual_gpu.py",
        ROOT / "scripts" / "remote" / "run_revtrace_dual_gpu_gate.sh":
            OUTPUT / "scripts" / "run_dual_gpu_gate.sh",
        ROOT / "scripts" / "remote" / "run_revtrace_flip_stress.py":
            OUTPUT / "scripts" / "run_flip_stress.py",
        ROOT / "src" / "revtrace" / "core.py":
            OUTPUT / "src" / "revguard.py",
    }
    result_root = ROOT / "results" / "phase1" / "deployed_v1"
    for source in result_root.rglob("*"):
        if source.is_file() and source.name not in {
            "summary.json",
            "MANIFEST.json",
        }:
            mappings[source] = (
                OUTPUT
                / "results"
                / "evidence"
                / source.relative_to(result_root)
            )
    for source, target in mappings.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    files = sorted(path for path in OUTPUT.rglob("*") if path.is_file())
    manifest = {
        "schema_version": 1,
        "scope": (
            "deployed two-GPU results, flip-rich stress, D0 logs, "
            "scripts, config, and bounded report"
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
    write_json(OUTPUT / "MANIFEST.json", manifest)
    print(json.dumps({"files": len(files), "output": str(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_manifest(root: Path, manifest_path: Path, repo_relative: bool) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    base = ROOT if repo_relative else root
    for item in manifest["files"]:
        path = base / item["path"]
        if not path.is_file():
            failures.append(f"missing:{path}")
            continue
        if path.stat().st_size != item["bytes"]:
            failures.append(f"size:{path}")
        if sha256(path) != item["sha256"]:
            failures.append(f"sha256:{path}")
    return failures


def main() -> int:
    required = [
        "README.md",
        "AGENTS.md",
        "configs/experiment_registry.json",
        "docs/CLAIM_BOUNDARIES.md",
        "docs/roadmap/PHASES.md",
        "results/phase0",
        "results/phase1/deployed_v1/summary.json",
        "artifact/phase1-deployed-system-v1/MANIFEST.json",
        "results/phase2/risk_v1/summary.json",
        "results/phase2/terminal_canonical/summary.json",
        "artifact/phase2-risk-tail-v1/MANIFEST.json",
        "src/revtrace/core.py",
        "src/revtrace/risk.py",
    ]
    failures = [
        f"missing-required:{path}"
        for path in required
        if not (ROOT / path).exists()
    ]

    registry = json.loads(
        (ROOT / "configs" / "experiment_registry.json").read_text(
            encoding="utf-8"
        )
    )
    for experiment in registry["experiments"]:
        for key in ("config", "result", "artifact"):
            if not (ROOT / experiment[key]).exists():
                failures.append(
                    f"registry:{experiment['id']}:{key}:{experiment[key]}"
                )

    failures.extend(
        check_manifest(
            ROOT / "results" / "phase1" / "deployed_v1",
            ROOT / "results" / "phase1" / "deployed_v1" / "MANIFEST.json",
            repo_relative=False,
        )
    )
    failures.extend(
        check_manifest(
            ROOT / "results" / "phase2",
            ROOT / "results" / "phase2" / "MANIFEST.json",
            repo_relative=True,
        )
    )
    failures.extend(
        check_manifest(
            ROOT / "artifact" / "phase2-risk-tail-v1",
            ROOT
            / "artifact"
            / "phase2-risk-tail-v1"
            / "MANIFEST.json",
            repo_relative=False,
        )
    )
    failures.extend(
        check_manifest(
            ROOT / "artifact" / "phase1-deployed-system-v1",
            ROOT
            / "artifact"
            / "phase1-deployed-system-v1"
            / "MANIFEST.json",
            repo_relative=False,
        )
    )

    print(
        json.dumps(
            {
                "project": "RevTrace",
                "registered_experiments": len(registry["experiments"]),
                "failures": failures,
                "status": "PASS" if not failures else "FAIL",
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

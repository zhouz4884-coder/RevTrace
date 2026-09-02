"""Build a deterministic, reviewer-facing RevTrace evidence archive."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Paper_TC" / "submission" / "RevTrace_TC_review_artifact.zip"


EXACT_FILES = (
    "configs/final_evaluation_closure.json",
    "docs/CLAIM_BOUNDARIES.md",
    "docs/reports/phase4_adaptation_generality_report.md",
    "docs/reports/r10_same_workload_dgft_ablation.md",
    "docs/reports/r9e_online_submission_closure.md",
    "Paper/figures/source_data/f7_v100_dual_plane.csv",
    "Paper_TC/NO_NEW_EXPERIMENT_DECISION.md",
    "Paper_TC/reports/TRANSACTION_OVERHEAD.md",
    "results/phase4/summary.json",
    "results/phase4/whisper_feedback/README.md",
    "results/phase4/whisper_feedback/whisper-tiny-en.json",
    "results/phase4/whisper_feedback/whisper-base-en.json",
    "results/paper_review_closure/transaction_fuzz.json",
    "results/r9_dgft/FINAL_REPORT.json",
    "results/r9_dgft/FINAL_REPORT_ONLINE.json",
    "results/r9_dgft/online_closure/coverage-replay.json",
    "results/r10_qwen_cross_adapter/summary.json",
    "results/r10_qwen_cross_adapter/summary.md",
    "results/r10_qwen_cross_adapter/ablation_summary.json",
    "results/v100_v1_v4/results/v1_v4/178168.manager/AUDIT.json",
    "results/v100_v1_v4/results/v1_v4/178168.manager/AUDIT.md",
    "results/v100_v1_v4/results/v1_v4/178168.manager/V1_V4_REPORT.md",
    "results/v100_v1_v4/results/v1_v4/178168.manager/environment.json",
    "results/v100_v1_v4/results/v1_v4/178168.manager/v1_v4_summary.json",
    "results/v100_v5_headline/178169.manager/V5_HEADLINE_REPORT.md",
    "results/v100_v5_headline/178169.manager/environment.json",
    "results/v100_v5_headline/178169.manager/v5_headline_summary.json",
    "scripts/audit_tc_submission.py",
    "scripts/finalize_r10_dgft_ablation.py",
    "scripts/finalize_r10_qwen_cross_adapter.py",
    "scripts/finalize_r9_online_closure.py",
    "scripts/run_tc_transaction_overhead.py",
    "scripts/validate_tc_transaction_overhead.py",
    "scripts/v100/audit_v100_headline_repeats.py",
    "scripts/v100/audit_v100_matrix.py",
    "scripts/v100/finalize_v100_matrix.py",
    "scripts/v100/run_v100_headline_repeats.py",
    "scripts/v100/run_v100_matrix.py",
)

GLOBS = (
    "src/revtrace/**/*.py",
    "tests/**/*.py",
    "results/tc_transaction_overhead/*",
    "results/r10_qwen_cross_adapter/*.json",
    "results/r9_dgft/online_closure/contracts/*.json",
    "results/r9_dgft/service/online_closure_matrix/*.json",
    "results/final_closure/quality/*.json",
    "results/final_closure/quality/*.csv",
    "results/final_closure/quality/raw/*.json",
    "results/v100_v1_v4/results/v1_v4/178168.manager/raw/*.json",
    "results/v100_v5_headline/178169.manager/raw/*.json",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def tracked_tree_dirty() -> bool:
    return subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--"], cwd=ROOT, check=False
    ).returncode != 0


def collect() -> list[Path]:
    paths = {ROOT / relative for relative in EXACT_FILES}
    for pattern in GLOBS:
        paths.update(ROOT.glob(pattern))
    missing = sorted(
        str(path.relative_to(ROOT)) for path in paths if not path.is_file()
    )
    if missing:
        raise FileNotFoundError("review artifact inputs missing: " + ", ".join(missing))
    return sorted(paths, key=lambda path: path.relative_to(ROOT).as_posix())


def write_member(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 9, 3, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def main() -> int:
    paths = collect()
    records = []
    payloads: list[tuple[str, bytes]] = []
    for path in paths:
        name = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        payloads.append((name, data))
        records.append({"path": name, "bytes": len(data), "sha256": sha256(data)})

    readme = """# RevTrace TC review artifact

This archive contains the production transaction code, tests, frozen summary
and selected raw result records, and the scripts needed to audit the claims in
the accompanying IEEE Transactions on Computers manuscript.

Scope boundaries:

- no model weights or redistributable speech corpora are included;
- the archive does not claim to reproduce GPU runs on arbitrary hardware;
- Qwen and Whisper quality estimands are family-specific and never pooled;
- V100 and RTX 3090 timing contracts are not pooled;
- the CPU transaction microbenchmark is host-side protocol-cost evidence, not
  GPU or end-to-end serving evidence.

Quick checks from the repository root:

```powershell
E:\\Anaconda\\python.exe scripts\\validate_tc_transaction_overhead.py
E:\\Anaconda\\python.exe -m pytest -q
```

See `docs/CLAIM_BOUNDARIES.md` and the JSON/CSV records for exact denominators,
contracts, environment fingerprints, and hashes.
""".encode("utf-8")

    manifest = {
        "schema_version": 1,
        "purpose": "review-only evidence archive for the RevTrace TC submission",
        "git_commit": git_output("rev-parse", "HEAD"),
        "tracked_tree_dirty_at_build": tracked_tree_dirty(),
        "files": records,
    }
    manifest_data = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w") as archive:
        write_member(archive, "README.md", readme)
        write_member(archive, "MANIFEST.json", manifest_data)
        for name, data in payloads:
            write_member(archive, name, data)

    with zipfile.ZipFile(OUTPUT) as archive:
        names = set(archive.namelist())
        if len(names) != len(payloads) + 2:
            raise RuntimeError("review artifact contains duplicate or missing entries")
        for record in records:
            data = archive.read(record["path"])
            if sha256(data) != record["sha256"]:
                raise RuntimeError(f"hash mismatch: {record['path']}")

    print(json.dumps({
        "output": str(OUTPUT),
        "bytes": OUTPUT.stat().st_size,
        "sha256": sha256(OUTPUT.read_bytes()),
        "files": len(payloads),
        "status": "PASS",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a compact, hash-audited Whisper cross-family artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


STATIC_FILES = (
    "README.md",
    "configs/revtrace_whisper_w0_prior_art.json",
    "configs/revtrace_whisper_w0_w7.json",
    "docs/CLAIM_BOUNDARIES.md",
    "docs/reports/revtrace_paper_identity.md",
    "docs/reports/whisper_w5_protocol_repair.md",
    "scripts/build_whisper_w0_w7_artifact.py",
    "scripts/build_whisper_w_state_age_policy.py",
    "scripts/extract_whisper_w5_adaptation_root.py",
    "scripts/finalize_revtrace_paper_evidence.py",
    "scripts/finalize_whisper_w0_w7.py",
    "scripts/renew_whisper_w_policy.py",
    "scripts/select_whisper_w_policy.py",
    "scripts/validate_whisper_w_known_pairs.py",
    "scripts/remote/build_whisper_w_quality_manifest.py",
    "scripts/remote/finish_whisper_w0_w7_v2.sh",
    "scripts/remote/finish_whisper_w4_contracts.sh",
    "scripts/remote/run_whisper_w3_parallel.sh",
    "scripts/remote/run_whisper_w4_audits.sh",
    "scripts/remote/run_whisper_w4_contract.sh",
    "scripts/remote/run_whisper_w4_dynamic_work_recert.sh",
    "scripts/remote/run_whisper_w5_parallel.sh",
    "scripts/remote/run_whisper_w5_authority_scheduler_ablation.sh",
    "scripts/remote/run_whisper_w5_state_contract_crossscale.sh",
    "scripts/remote/run_whisper_w5_state_lane_ablation.sh",
    "scripts/remote/run_whisper_w5_terminal_scheduler_ablation.sh",
    "scripts/remote/run_whisper_w5_transaction_ablation.sh",
    "scripts/remote/run_whisper_w6_parallel.sh",
    "scripts/remote/run_whisper_w6_base_prerun_current.sh",
    "scripts/remote/run_whisper_w6_failure_attribution.sh",
    "scripts/remote/run_whisper_w6_budget_authority_dev.sh",
    "scripts/remote/run_whisper_w6_state_root_diagnostic.sh",
    "scripts/remote/run_whisper_w6_state_contract_dev.sh",
    "scripts/remote/diagnose_whisper_w6_canonical_trace.py",
    "scripts/remote/release_whisper_w5_after_dynamic_preflight.sh",
    "scripts/remote/run_whisper_w7_finalize.sh",
    "scripts/remote/resume_whisper_w5_w6_after_recert.sh",
    "scripts/remote/resume_whisper_w5_w6_state_contract.sh",
    "scripts/remote/run_whisper_w_concurrent_probe.py",
    "scripts/remote/run_whisper_w_matrix.sh",
    "scripts/remote/run_whisper_w_mechanism.py",
    "scripts/remote/run_whisper_w_quality.py",
    "scripts/remote/run_whisper_w_smoke.py",
    "scripts/remote/run_whisper_w_system.py",
    "scripts/remote/whisper_batched_executor.py",
    "src/revtrace/whisper_state.py",
    "tests/test_whisper_policy_selection.py",
    "tests/test_whisper_prompt_state.py",
    "tests/test_whisper_w0_w7_finalizer.py",
    "tests/test_whisper_w5_adaptation_root.py",
)

RESULT_FILES = (
    "results/whisper_w0_w7/w1-smoke-base-final.json",
    "results/whisper_w0_w7/w1-smoke-small-final.json",
    "results/whisper_w0_w7/w2-known-pairs-v4.json",
    "results/whisper_w0_w7/w3-mechanism-base.json",
    "results/whisper_w0_w7/w3-mechanism-small.json",
    "results/whisper_w0_w7/w-concurrent-base-l2-gpu1.json",
    "results/whisper_w0_w7/w-concurrent-base-l3-gpu1.json",
    "results/whisper_w0_w7/w-concurrent-base-l4.json",
    "results/whisper_w0_w7/w-concurrent-small-l2-gpu1.json",
    "results/whisper_w0_w7/w6-quality-base.json",
    "results/whisper_w0_w7/w6-quality-small.json",
    "results/whisper_w0_w7/model-fingerprints.json",
    "results/whisper_w0_w7/w7-summary.json",
    "results/whisper_w0_w7/w7-report.md",
    "results/paper_evidence/summary.json",
    "results/paper_evidence/REPORT.md",
)

TEXT_SUFFIXES = {".json", ".md", ".py", ".sh"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifact/whisper-cross-family-closure-v1"),
    )
    return parser.parse_args()


def normalized_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in TEXT_SUFFIXES:
        target.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
    else:
        shutil.copy2(source, target)


def risk_dependency_files(
    root: Path,
    risk_files: tuple[str, ...],
) -> tuple[str, ...]:
    """Collect each final certificate's policy and hashed policy sources."""

    result_root = root / "results/whisper_w0_w7"
    collected: set[str] = set()
    for relative in risk_files:
        result = json.loads(
            (root / relative).read_text(encoding="utf-8")
        )
        policy = result_root / Path(
            result["config"]["policy_source"]
        ).name
        if not policy.is_file():
            raise FileNotFoundError(policy)
        if sha256(policy) != result["config"]["policy_sha256"]:
            raise RuntimeError(
                f"final risk certificate policy hash mismatch: {policy}"
            )
        collected.add(str(policy.relative_to(root)).replace("\\", "/"))
        payload = json.loads(policy.read_text(encoding="utf-8"))
        for source in payload.get("source_files", []):
            dependency = result_root / Path(source["path"]).name
            if dependency.is_file():
                if sha256(dependency) != source["sha256"]:
                    raise RuntimeError(
                        "risk-policy source hash mismatch: "
                        f"{dependency}"
                    )
                collected.add(
                    str(dependency.relative_to(root)).replace("\\", "/")
                )
    return tuple(sorted(collected))


def main() -> int:
    args = parse_args()
    root = Path.cwd().resolve()
    output = args.output.resolve()
    if output == root or root not in output.parents:
        raise ValueError("artifact output must stay inside the repository")
    if output.exists():
        shutil.rmtree(output)

    final_path = root / "results/whisper_w0_w7/w7-summary.json"
    paper_path = root / "results/paper_evidence/summary.json"
    final = json.loads(final_path.read_text(encoding="utf-8"))
    paper = json.loads(paper_path.read_text(encoding="utf-8"))
    if final["decision"] != "W7_CROSS_FAMILY_STRONG_PASS":
        raise RuntimeError("refusing to freeze an incomplete W7 result")
    if paper["decision"] != "PAPER_EVIDENCE_COMPLETE":
        raise RuntimeError("refusing to freeze incomplete paper evidence")
    risk_files = tuple(
        "results/whisper_w0_w7/" + row["final_result_file"]
        for contracts in final["risk"].values()
        for row in contracts.values()
    )
    risk_dependencies = risk_dependency_files(root, risk_files)

    files: dict[str, dict[str, int | str]] = {}
    for relative in (
        *STATIC_FILES,
        *RESULT_FILES,
        *risk_files,
        *risk_dependencies,
    ):
        source = (root / relative).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        target = output / relative
        normalized_copy(source, target)
        files[relative] = {
            "bytes": target.stat().st_size,
            "sha256": sha256(target),
        }

    readme = output / "README.md"
    readme.write_text(
        "\n".join([
            "# RevTrace Whisper cross-family closure",
            "",
            "Decision: `W7_CROSS_FAMILY_STRONG_PASS`.",
            "",
            "This compact artifact contains the final W0-W7 summaries, the",
            "four independently certified W4 risk contracts, paired W6",
            "quality evidence, model fingerprints, current source, and tests.",
            "The full W5 run matrix is content-addressed by `w7-summary.json`",
            "rather than duplicated here. Excluded protocol-development",
            "epochs are retained in the full results tree and never contribute",
            "to the final certificate.",
            "",
            "The paper claim is method-driven state-certified revision",
            "serving. Whisper supplies cross-family and cross-scale evidence;",
            "ordinary batching, dtype choice, adapters, and queue code are",
            "engineering substrate rather than claimed contributions.",
            "",
        ]) + "\n",
        encoding="utf-8",
    )
    files["README.md"] = {
        "bytes": readme.stat().st_size,
        "sha256": sha256(readme),
    }

    manifest = {
        "schema_version": 1,
        "artifact": "whisper-cross-family-closure-v1",
        "decision": final["decision"],
        "paper_decision": paper["decision"],
        "scope": (
            "compact cross-family evidence and current reproduction source; "
            "the complete W5 matrix remains hash-bound by w7-summary.json"
        ),
        "files": files,
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for relative, record in files.items():
        if sha256(output / relative) != record["sha256"]:
            raise AssertionError(f"artifact verification failed: {relative}")
    print(json.dumps({
        "decision": manifest["decision"],
        "files": len(files),
        "manifest_sha256": sha256(manifest_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

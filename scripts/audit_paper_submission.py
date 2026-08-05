#!/usr/bin/env python3
"""Build the three offline pre-submission audits for the RevTrace paper."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def collect_digest_fields(value: Any, prefix: str = "") -> dict[str, str]:
    found: dict[str, str] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            if (
                isinstance(child, str)
                and (key.endswith("digest") or key.endswith("sha256"))
            ):
                found[name] = child
            else:
                found.update(collect_digest_fields(child, name))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.update(collect_digest_fields(child, f"{prefix}[{index}]"))
    return found


def artifact(path_text: str, *, role: str) -> dict[str, Any]:
    path = ROOT / path_text
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = load(path) if path.suffix == ".json" else None
    row: dict[str, Any] = {
        "path": relative(path),
        "role": role,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    if payload is not None:
        if "decision" in payload:
            row["decision"] = payload["decision"]
        digests = collect_digest_fields(payload)
        if digests:
            row["embedded_digests"] = digests
    return row


def denominator_audit() -> dict[str, Any]:
    sources = [
        ROOT / "results/phase4/whisper_feedback_expanded/whisper-base-en.json",
        ROOT / "results/phase4/whisper_feedback_expanded/whisper-tiny-en.json",
    ]
    pairs: list[tuple[str, dict[str, Any]]] = []
    source_rows: list[dict[str, Any]] = []
    for path in sources:
        payload = load(path)
        source_rows.append({
            "path": relative(path),
            "model": payload["model"],
            "pairs": len(payload["pairs"]),
            "sha256": sha256(path),
            "selection": {
                "batch_sizes": payload["config"]["batch_sizes"],
                "future_windows": payload["config"]["future_windows"],
                "max_candidates": payload["config"]["max_candidates"],
                "singleton_repeat_mismatches": payload["counts"][
                    "singleton_repeat_mismatches"
                ],
            },
        })
        pairs.extend((payload["model"], pair) for pair in payload["pairs"])

    pair_hashes = [pair["pair_sha256"] for _, pair in pairs]
    feedback_on = [
        (model, pair)
        for model, pair in pairs
        if any(int(value) > 0 for value in pair["feedback_on_distances"][1:])
    ]
    feedback_off = [
        (model, pair)
        for model, pair in pairs
        if any(int(value) > 0 for value in pair["feedback_off_distances"])
    ]
    persistent = [
        (model, pair)
        for model, pair in pairs
        if bool(pair["persistent_at_horizon"])
    ]
    persistent_raf = [float(pair["raf"]) for _, pair in persistent]

    manuscript_files = sorted((ROOT / "Paper").rglob("*.tex"))
    manuscript_files.extend([ROOT / "Paper/README.md"])
    forbidden: list[dict[str, Any]] = []
    boundary_mentions: list[dict[str, Any]] = []
    for path in manuscript_files:
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if re.search(r"(?<!\d)8\s*/\s*8(?!\d)", line):
                row = {
                    "path": relative(path),
                    "line": number,
                    "text": line.strip(),
                }
                if re.search(r"never|forbid|incorrect|not use", line, re.I):
                    boundary_mentions.append(row)
                else:
                    forbidden.append(row)

    checks = {
        "distinct_pair_hashes": len(set(pair_hashes)) == len(pair_hashes),
        "legal_pair_denominator_is_21": len(pairs) == 21,
        "feedback_on_propagating_pairs_is_8": len(feedback_on) == 8,
        "feedback_off_propagating_pairs_is_0": len(feedback_off) == 0,
        "persistent_pairs_is_6": len(persistent) == 6,
        "persistent_maximum_raf_is_153": max(persistent_raf) == 153.0,
        "no_manuscript_8_over_8_claim": not forbidden,
    }
    return {
        "schema_version": 1,
        "decision": (
            "PASS_PAPER_DENOMINATOR_AUDIT"
            if all(checks.values()) else "FAIL_PAPER_DENOMINATOR_AUDIT"
        ),
        "statistical_unit": (
            "a distinct legal singleton-versus-batch state pair produced by "
            "an execution-shape intervention, with future audio held fixed"
        ),
        "selection_boundary": (
            "Pair yield is a targeted causal stress sample, not a production "
            "prevalence estimate. RAF is summarized only on pairs persistent "
            "at the measured horizon."
        ),
        "counts": {
            "legal_pairs": len(pairs),
            "feedback_on_propagating_pairs": len(feedback_on),
            "feedback_off_propagating_pairs": len(feedback_off),
            "persistent_pairs": len(persistent),
            "persistent_maximum_raf": max(persistent_raf),
        },
        "persistent_pair_sources": [
            {
                "model": model,
                "pair_sha256": pair["pair_sha256"],
                "raf": pair["raf"],
                "feedback_on_distances": pair["feedback_on_distances"],
                "feedback_off_distances": pair["feedback_off_distances"],
            }
            for model, pair in persistent
        ],
        "sources": source_rows,
        "manuscript_scan": {
            "files": len(manuscript_files),
            "forbidden_claims": forbidden,
            "boundary_warnings": boundary_mentions,
        },
        "checks": checks,
    }


def contract_inventory() -> dict[str, Any]:
    r9_contracts = [
        artifact(
            f"results/r9_dgft/online_closure/contracts/whisper-{size}.en-contract.json",
            role=f"Whisper {size}.en frozen R9.E service contract",
        )
        for size in ("tiny", "base", "small")
    ]
    groups = [
        {
            "id": "r9e_whisper_service",
            "scope": {
                "family": "Whisper",
                "models": ["tiny.en", "base.en", "small.en"],
                "mechanism": "DGFT coarse authority with selective replay",
                "workload": "16 sessions, c16, 90 s, sync and Poisson arrivals",
                "timing": "virtual causal arrivals; real GPU wall time and NVML energy",
                "claim_boundary": "16 service executions; exhaustive trace, not iid risk",
            },
            "artifacts": [
                artifact(
                    "results/r9_dgft/FINAL_REPORT_ONLINE.json",
                    role="R9.E service and Whisper quality closure",
                ),
                artifact(
                    "results/r9_dgft/online_closure/coverage-replay.json",
                    role="2,050-segment coverage regression",
                ),
                *r9_contracts,
            ],
        },
        {
            "id": "r10_qwen_service",
            "scope": {
                "family": "Qwen3-ASR",
                "models": ["0.6B", "1.7B"],
                "mechanism": "Coarse and Hybrid DGFT; SG same-workload ablation",
                "workload": "16 bilingual 30 s sessions, c16, 480 s audio",
                "canonical_paths": (
                    "FP32 batched authority for Coarse/Hybrid; FP16 singleton "
                    "authority for SG; paths are versioned and not bitwise identical"
                ),
                "claim_boundary": "preflight excluded from service timing",
            },
            "artifacts": [
                artifact(
                    "results/r10_qwen_cross_adapter/summary.json",
                    role="R10 production matrix",
                ),
                artifact(
                    "results/r10_qwen_cross_adapter/ablation_summary.json",
                    role="same-workload six-cell SG/Coarse/Hybrid ablation",
                ),
            ],
        },
        {
            "id": "v100_qwen_scaleout",
            "scope": {
                "family": "Qwen3-ASR",
                "models": ["0.6B", "1.7B"],
                "mechanism": "SG and DGFT replica scale-out",
                "workload": "bilingual 30 s sessions, c16--c128",
                "hardware": "one 8xTesla-V100-32GB PCIe node",
                "backend": "Transformers eager; PyTorch 2.4.1/CUDA 12.1",
                "claim_boundary": (
                    "independent of RTX3090/vLLM; single-node scale-out only; "
                    "c64 is the measured 2 s-SLO capacity and c128 is overload"
                ),
            },
            "artifacts": [
                artifact(
                    "results/v100_v1_v4/results/v0/178164.manager/smoke.json",
                    role="V100 legality and repeated-input smoke",
                ),
                artifact(
                    "results/v100_v1_v4/results/v1_v4/178168.manager/environment.json",
                    role="V100 environment and runner fingerprint",
                ),
                artifact(
                    "results/v100_v1_v4/results/v1_v4/178168.manager/v1_v4_summary.json",
                    role="complete 84-cell V1--V4 matrix",
                ),
                artifact(
                    "results/v100_v1_v4/results/v1_v4/178168.manager/AUDIT.json",
                    role="independent 479-check matrix audit",
                ),
            ],
        },
        {
            "id": "sg_anytime_risk",
            "scope": {
                "family": "Qwen3-ASR",
                "models": ["0.6B", "1.7B"],
                "mechanism": "same-granularity numerical-risk adapter only",
                "estimand": "disagreement with frozen canonical execution",
                "confidence": "95% time-uniform",
                "claim_boundary": "does not transfer to Coarse/Hybrid DGFT paths",
            },
            "artifacts": [
                artifact(
                    "results/phase2/risk_v1/summary.json",
                    role="two-scale SG anytime-risk summary",
                ),
                artifact(
                    "results/phase2/risk_v1/natural-shadow-Qwen3-ASR-0.6B.json",
                    role="0.6B frozen-policy randomized audit",
                ),
                artifact(
                    "results/phase2/risk_v2/natural-shadow-Qwen3-ASR-1.7B-tau0.10.json",
                    role="1.7B independently validated randomized audit",
                ),
            ],
        },
        {
            "id": "qwen_quality",
            "scope": {
                "family": "Qwen3-ASR",
                "models": ["0.6B", "1.7B"],
                "languages": ["English", "Chinese"],
                "estimand": "normalized WER/CER and terminal mismatch against paired singleton reference",
                "claim_boundary": "independent holdout; empirical intervals, not equivalence proof",
            },
            "artifacts": [
                artifact(
                    "results/final_closure/quality/summary.json",
                    role="Qwen bilingual paired quality gate",
                ),
                artifact(
                    "results/final_closure/quality/holdout_manifest.json",
                    role="independent Qwen quality holdout",
                ),
            ],
        },
        {
            "id": "whisper_quality",
            "scope": {
                "family": "Whisper",
                "models": ["tiny.en", "base.en", "small.en"],
                "estimand": "paired WER delta versus unprotected feedback execution",
                "cohorts": ["development", "third untouched confirmation"],
                "claim_boundary": "not pooled with Qwen canonical-reference edit rates",
            },
            "artifacts": [
                artifact(
                    "results/r9_dgft/FINAL_REPORT_ONLINE.json",
                    role="six-cell Whisper quality closure with service bindings",
                ),
                artifact(
                    "results/r9_dgft/final_holdout3-pre-execution-audit.json",
                    role="untouched confirmation pre-execution audit",
                ),
            ],
        },
    ]
    canonical_contracts = artifact(
        "results/final_closure/canonical_contracts.json",
        role="cross-contract provenance boundary",
    )
    payload = {
        "schema_version": 1,
        "decision": "PASS_PAPER_CONTRACT_INVENTORY",
        "generated_by": "scripts/audit_paper_submission.py",
        "invariant": (
            "Evidence groups have separate execution contracts and estimands. "
            "Hashes bind artifacts; no risk or quality guarantee transfers "
            "between groups unless explicitly stated."
        ),
        "global_contract_boundary": canonical_contracts,
        "groups": groups,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["inventory_digest"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    return payload


def render_report(
    coverage: dict[str, Any], denominator: dict[str, Any], inventory: dict[str, Any]
) -> str:
    counts = denominator["counts"]
    return "\n".join([
        "# RevTrace pre-submission offline audits",
        "",
        f"Overall: **{'PASS' if coverage['decision'].startswith('PASS') and denominator['decision'].startswith('PASS') and inventory['decision'].startswith('PASS') else 'FAIL'}**",
        "",
        "## A. CJK-aware coverage replay",
        "",
        f"- Decision: `{coverage['decision']}`",
        f"- Replayed: {coverage['segments']} segments from {coverage['files']} files.",
        f"- Latin-only: {coverage['latin_only_segments']}; CJK-containing: {coverage['cjk_segments']}.",
        f"- Recorded-decision changes: {coverage['recorded_decision_changes']}.",
        f"- Legacy-vs-current Latin-only changes: {coverage['legacy_current_latin_decision_changes']}.",
        "- Boundary: this is a regression test on English Whisper traces, not a Chinese-quality experiment.",
        "",
        "## B. Motivation denominator audit",
        "",
        f"- Decision: `{denominator['decision']}`",
        f"- Legal state pairs: {counts['legal_pairs']}.",
        f"- Feedback-on propagation: {counts['feedback_on_propagating_pairs']}/{counts['legal_pairs']}.",
        f"- Feedback-off propagation: {counts['feedback_off_propagating_pairs']}/{counts['legal_pairs']}.",
        f"- Persistent pairs: {counts['persistent_pairs']}; maximum measured RAF: {counts['persistent_maximum_raf']:.0f}.",
        f"- Manuscript 8/8 claim violations: {len(denominator['manuscript_scan']['forbidden_claims'])}.",
        "",
        "## C. Contract inventory",
        "",
        f"- Decision: `{inventory['decision']}`",
        f"- Evidence groups: {len(inventory['groups'])}.",
        f"- Inventory digest: `{inventory['inventory_digest']}`.",
        "- Groups: R9.E Whisper service, R10 Qwen service/ablation, SG anytime risk, Qwen quality, Whisper quality.",
        "- Risk and quality estimands remain family/path scoped and are not pooled.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--coverage", type=Path,
        default=ROOT / "results/r9_dgft/online_closure/coverage-replay.json",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "Paper/audits"
    )
    args = parser.parse_args()
    coverage = load(args.coverage)
    denominator = denominator_audit()
    inventory = contract_inventory()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "cjk_coverage_replay.json": coverage,
        "denominator_audit.json": denominator,
        "contract_inventory.json": inventory,
    }
    for name, payload in outputs.items():
        (args.output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (args.output_dir / "REPORT.md").write_text(
        render_report(coverage, denominator, inventory), encoding="utf-8"
    )
    passed = (
        coverage["decision"].startswith("PASS")
        and denominator["decision"].startswith("PASS")
        and inventory["decision"].startswith("PASS")
    )
    print(json.dumps({
        "decision": "PASS" if passed else "FAIL",
        "coverage": coverage["decision"],
        "denominator": denominator["decision"],
        "contract_inventory": inventory["decision"],
        "output_dir": relative(args.output_dir),
    }, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())

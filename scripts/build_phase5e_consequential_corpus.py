#!/usr/bin/env python3
"""Build the deduplicated consequential state-pair corpus."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from revtrace.phase5 import contamination_damage, pair_digest


QWEN_RUNS = (
    ("natural", "results/phase3/rir_population/qwen3-asr-0.6b.json"),
    ("natural", "results/phase3/rir_population/qwen3-asr-1.7b.json"),
    ("natural", "results/phase3/rir_population/qwen3-asr-0.6b-librispeech.json"),
    ("natural", "results/phase3/rir_population/qwen3-asr-1.7b-librispeech.json"),
    ("stress", "results/phase3/rir_population/qwen3-asr-0.6b-stress.json"),
    ("stress", "results/phase3/rir_population/qwen3-asr-1.7b-stress.json"),
    ("stress", "results/phase3/rir_population/qwen3-asr-0.6b-c64.json"),
    ("stress", "results/phase3/rir_population/qwen3-asr-1.7b-c64.json"),
    ("targeted", "results/phase4/active_mining/qwen3-asr-0.6b.json"),
    ("targeted", "results/phase4/active_mining/qwen3-asr-1.7b.json"),
)

WHISPER_RUNS = (
    "results/phase4/whisper_feedback_expanded/whisper-tiny-en.json",
    "results/phase4/whisper_feedback_expanded/whisper-base-en.json",
)


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def qwen_record(
    source_kind: str,
    source_path: str,
    run: dict[str, Any],
    pair: dict[str, Any],
) -> dict[str, Any]:
    trajectory = pair["trajectory"]
    distances = [float(item["distance"]) for item in trajectory]
    initial = max(1.0, distances[0])
    raf = sum(value / initial for value in distances)
    persistent = bool(distances and distances[-1] > 0)
    terminal = persistent
    canonical = pair.get(
        "canonical_output_token_ids", pair.get("canonical_token_ids", [])
    )
    divergent = pair.get(
        "divergent_output_token_ids", pair.get("divergent_token_ids", [])
    )
    source = str(
        pair.get("source")
        or f"{source_path}:{pair.get('session_id', '')}:"
        f"{pair.get('chunk_index', '')}"
    )
    semantic = {
        "architecture": "Qwen3-ASR",
        "model": run["model"],
        "canonical": canonical,
        "divergent": divergent,
        "trajectory": [
            {
                "canonical": item["canonical_state_sha256"],
                "divergent": item["divergent_state_sha256"],
            }
            for item in trajectory
        ],
    }
    return {
        "pair_hash": pair_digest(semantic),
        "audio_hash": hash_text(source),
        "model_family": "Qwen3-ASR",
        "model": run["model"],
        "source_kind": source_kind,
        "source_run": source_path,
        "source_identifier": source,
        "canonical_output_token_ids": canonical,
        "batched_output_token_ids": divergent,
        "margin": pair.get(
            "canonical_minimum_margin",
            pair.get("features", {}).get("minimum_margin"),
        ),
        "trajectory_distances": distances,
        "raf": raf,
        "persistent": persistent,
        "terminal_effect": terminal,
        "damage_score": contamination_damage(
            state_disagreement=True,
            raf=raf,
            persistent=persistent,
            terminal_difference=terminal,
        ),
    }


def whisper_record(
    source_path: str,
    run: dict[str, Any],
    pair: dict[str, Any],
) -> dict[str, Any]:
    distances = [float(value) for value in pair["feedback_on_distances"]]
    semantic = {
        "architecture": "Whisper-feedback",
        "model": run["model"],
        "canonical": pair["canonical"]["token_ids"],
        "divergent": pair["proposer"]["token_ids"],
        "distances": distances,
    }
    return {
        "pair_hash": pair_digest(semantic),
        "audio_hash": hash_text(
            f"{source_path}:{pair['session_index']}:{pair['source_window']}"
        ),
        "model_family": "Whisper-feedback",
        "model": run["model"],
        "source_kind": "natural",
        "source_run": source_path,
        "source_identifier": (
            f"session={pair['session_index']};"
            f"window={pair['source_window']}"
        ),
        "canonical_output_token_ids": pair["canonical"]["token_ids"],
        "batched_output_token_ids": pair["proposer"]["token_ids"],
        "margin": None,
        "trajectory_distances": distances,
        "raf": float(pair["raf"]),
        "persistent": bool(pair["persistent_at_horizon"]),
        "terminal_effect": bool(pair["terminal_difference"]),
        "damage_score": contamination_damage(
            state_disagreement=True,
            raf=float(pair["raf"]),
            persistent=bool(pair["persistent_at_horizon"]),
            terminal_difference=bool(pair["terminal_difference"]),
        ),
    }


def main() -> int:
    candidates: list[dict[str, Any]] = []
    for source_kind, source_path in QWEN_RUNS:
        path = ROOT / source_path
        run = json.loads(path.read_text(encoding="utf-8"))
        candidates.extend(
            qwen_record(source_kind, source_path, run, pair)
            for pair in run["pairs"]
        )
    for source_path in WHISPER_RUNS:
        path = ROOT / source_path
        run = json.loads(path.read_text(encoding="utf-8"))
        candidates.extend(
            whisper_record(source_path, run, pair)
            for pair in run["pairs"]
        )
    unique = {record["pair_hash"]: record for record in candidates}
    records = sorted(
        unique.values(),
        key=lambda item: (
            item["model_family"],
            item["model"],
            item["pair_hash"],
        ),
    )
    by_family: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for record in records:
        by_family[record["model_family"]] = (
            by_family.get(record["model_family"], 0) + 1
        )
        by_source[record["source_kind"]] = (
            by_source.get(record["source_kind"], 0) + 1
        )
    payload = {
        "schema_version": 1,
        "study": "RevTrace consequential state-pair corpus",
        "decision": "PHASE5E_CONSEQUENTIAL_CORPUS_COMPLETE",
        "candidate_records": len(candidates),
        "distinct_records": len(records),
        "duplicates_removed": len(candidates) - len(records),
        "by_family": by_family,
        "by_source": by_source,
        "records": records,
        "claim_boundaries": [
            "the corpus is deduplicated by semantic state-pair identity",
            "targeted and stress records are not production prevalence",
            "damage scores rank observed consequences and are not probabilities",
            "audio hashes are stable source identifiers, not redistributed audio",
        ],
    }
    output = (
        ROOT
        / "results"
        / "phase5"
        / "consequential_corpus"
        / "corpus.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "decision": payload["decision"],
                "candidate_records": len(candidates),
                "distinct_records": len(records),
                "by_family": by_family,
                "by_source": by_source,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

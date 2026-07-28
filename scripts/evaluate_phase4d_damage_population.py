#!/usr/bin/env python3
"""Re-account Phase 3C with persistent-tail and diversity-aware metrics."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from revtrace.amplification import (  # noqa: E402
    RevisionImpulsePair,
    summarize_contamination_tail,
)


SOURCE = ROOT / "results" / "phase3" / "rir_population"
OUT = ROOT / "results" / "phase4" / "damage_population"


def load_pairs(path: Path) -> list[RevisionImpulsePair]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    pairs = []
    for item in payload.get("pairs", []):
        pairs.append(
            RevisionImpulsePair(
                pair_id=item["pair_id"],
                distances=tuple(
                    float(step["distance"])
                    for step in item["trajectory"]
                ),
                terminal_different=bool(
                    item["trajectory"][-1]["distance"] > 0
                ),
            )
        )
    return pairs


def initial_pair_signature(item: dict) -> str:
    first = item["trajectory"][0]
    payload = [
        first["canonical_state_token_ids"],
        first["divergent_state_token_ids"],
    ]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main() -> int:
    rows = []
    for path in sorted(SOURCE.glob("qwen3-asr-*.json")):
        pairs = load_pairs(path)
        if not pairs:
            continue
        tail = summarize_contamination_tail(pairs)
        source = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "file": path.name,
                "model": source["model"],
                "distinct_pairs": len(pairs),
                "candidate_revisions": source["search"][
                    "candidate_revisions"
                ],
                "replicated_rows": source["search"]["replicated_rows"],
                "duplicate_state_pairs": source["search"][
                    "duplicate_state_pairs"
                ],
                "tail": tail.to_dict(),
                "pair_yield_per_1000_replicated_rows": (
                    1000 * len(pairs)
                    / max(1, source["search"]["replicated_rows"])
                ),
            }
        )
    totals: dict[str, dict[str, object]] = {}
    unique_signatures: dict[str, set[str]] = {}
    for row in rows:
        family = (
            "Qwen3-ASR-0.6B"
            if "0.6B" in row["model"]
            else "Qwen3-ASR-1.7B"
        )
        item = totals.setdefault(
            family,
            {
                "distinct_pairs": 0,
                "replicated_rows": 0,
                "duplicate_state_pairs": 0,
            },
        )
        item["replicated_rows"] += row["replicated_rows"]
        item["duplicate_state_pairs"] += row[
            "duplicate_state_pairs"
        ]
        source = json.loads(
            (SOURCE / row["file"]).read_text(encoding="utf-8")
        )
        unique_signatures.setdefault(family, set()).update(
            initial_pair_signature(pair)
            for pair in source.get("pairs", [])
        )
    for family, signatures in unique_signatures.items():
        totals[family]["distinct_pairs"] = len(signatures)
    gate_pass = all(
        item["distinct_pairs"] >= 50 for item in totals.values()
    )
    payload = {
        "schema_version": 1,
        "study": "Phase 4D contamination-tail and mining-accounting gate",
        "decision": (
            "PHASE4D_EXISTING_POPULATION_GATE_PASS"
            if gate_pass
            else "PHASE4D_DAMAGE_METRICS_PASS_ACTIVE_500_CANDIDATE_RUN_UNRESOLVED"
        ),
        "runs": rows,
        "model_totals": totals,
        "gates": {
            "pcm_and_tail_raf_computed": True,
            "fifty_distinct_pairs_per_model": gate_pass,
            "active_500_candidate_gpu_run": False,
        },
        "root_cause": (
            "slot/repeat expansion repeatedly rediscovers the same state "
            "pair; existing files contain only 19 and 15 deduplicated pairs."
        ),
        "frozen_active_policy": {
            "objective": "new consequential state pairs per GPU-hour",
            "candidate_cap_per_model": 500,
            "pair_cap_per_model": 50,
            "priority": [
                "low canonical margin",
                "unseen state projection signature",
                "EOS or output-length frontier damage proxy",
                "acoustic uncertainty",
            ],
            "duplicate_action": "stop all remaining slot/repeat probes",
        },
        "claim_boundaries": [
            "tail summaries describe observed targeted pairs",
            "targeted mining cannot estimate production prevalence",
            "the unexecuted 500-candidate budget is not a population result",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
# Development-only same-seed ablation for speculative revision transactions.
set -u

if [[ "$#" -ne 4 ]]; then
  echo "usage: $0 ROOT MODEL MANIFEST OUT" >&2
  exit 2
fi
ROOT="$1"
MODEL="$2"
MANIFEST="$3"
OUT="$4"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
DEV="$OUT/development/revision-transaction-ablation"
ORACLE="$OUT/development/terminal-scheduler-ablation/oracle-seed20272590.json"
mkdir -p "$DEV"
export PYTHONPATH="$PROJ/src"

threshold="$(cat "$OUT/w4-final-threshold-base-c16.txt")"
late_window="$(cat "$OUT/w4-final-late-window-base-c16.txt")"
late_threshold="$(cat "$OUT/w4-final-late-threshold-base-c16.txt")"
load_prompt="$(cat "$OUT/w4-final-high-load-prompt-base-c16.txt")"
load_threshold="$(cat "$OUT/w4-final-high-load-threshold-base-c16.txt")"
context_args=()
if [[ "$late_window" != none ]]; then
  context_args+=(--late-window-index "$late_window")
  context_args+=(--late-margin-threshold "$late_threshold")
fi
if [[ "$load_prompt" != none ]]; then
  context_args+=(--high-load-prompt-tokens "$load_prompt")
  context_args+=(--high-load-margin-threshold "$load_threshold")
fi

run_variant() {
  local name="$1"
  local lanes="$2"
  local depth="$3"
  local terminal_contract="$4"
  "$PY" "$RUNNER" workload \
    --model "$MODEL" --model-name whisper-base.en \
    --manifest "$MANIFEST" --output "$DEV/${name}.json" \
    --oracle-cache "$ORACLE" \
    --system revtrace --sessions 16 --duration-seconds 90 \
    --window-seconds 10 --concurrency 16 --arrival sync \
    --seed 20272590 --margin-threshold "$threshold" \
    "${context_args[@]}" --max-new-tokens 96 \
    --audit-probability 0.021 --slo-seconds 2.0 \
    --proposer-device cuda:0 --verifier-device cuda:1 \
    --verifier-lanes "$lanes" \
    --speculative-prefetch-depth "$depth" \
    --terminal-contract "$terminal_contract" \
    >"$DEV/${name}.log" 2>&1
}

run_variant exact-lane1-prefetch 1 1 canonical-output
run_variant state-lane1 1 0 state-only
run_variant state-lane1-prefetch 1 1 state-only
run_variant state-lane2-prefetch 2 1 state-only

"$PY" - "$DEV" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for name in (
    "exact-lane1-prefetch",
    "state-lane1",
    "state-lane1-prefetch",
    "state-lane2-prefetch",
):
    row = json.load(open(root / f"{name}.json"))
    assert row["counts"]["state_violations"] == 0
    assert row["counts"]["stale_commits"] == 0
    assert row["config"]["warmup"]["verifier_lane_exact"] is True
    rows.append({
        "variant": name,
        "terminal_contract": row["config"]["terminal_contract"],
        "wall_speedup": row["metrics"]["wall_speedup"],
        "gpu_normalized_speedup": row["metrics"][
            "gpu_normalized_speedup"
        ],
        "p99": row["metrics"]["latency_p99"],
        "deadline_misses": row["counts"]["deadline_misses"],
        "state_violations": row["counts"]["state_violations"],
        "output_violations": row["counts"]["output_violations"],
        "prefetches": row["counts"]["speculative_prefetches"],
        "prefetch_reuses": row["counts"][
            "speculative_prefetch_reuses"
        ],
        "prefetch_discards": row["counts"][
            "speculative_prefetch_discards"
        ],
    })
(root / "summary.json").write_text(
    json.dumps({
        "schema_version": 1,
        "study": "development-only revision transaction ablation",
        "claim_boundary": (
            "mechanism selection evidence; excluded from final W5 seed epoch"
        ),
        "rows": rows,
    }, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(rows, sort_keys=True))
PY

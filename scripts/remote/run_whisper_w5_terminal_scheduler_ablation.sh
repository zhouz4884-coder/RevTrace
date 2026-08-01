#!/usr/bin/env bash
# Development-only same-seed ablation for canonical terminal scheduling.
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
DEV="$OUT/development/terminal-scheduler-ablation"
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
  local spillover="$3"
  local extra=()
  if [[ "$spillover" == true ]]; then
    extra+=(--terminal-spillover-on-proposer)
  fi
  "$PY" "$RUNNER" workload \
    --model "$MODEL" --model-name whisper-base.en \
    --manifest "$MANIFEST" \
    --output "$DEV/${name}.json" \
    --oracle-cache "$DEV/oracle-seed20272590.json" \
    --system revtrace --sessions 16 --duration-seconds 90 \
    --window-seconds 10 --concurrency 16 --arrival sync \
    --seed 20272590 --margin-threshold "$threshold" \
    "${context_args[@]}" --max-new-tokens 96 \
    --audit-probability 0.021 --slo-seconds 2.0 \
    --proposer-device cuda:0 --verifier-device cuda:1 \
    --verifier-lanes "$lanes" "${extra[@]}" \
    >"$DEV/${name}.log" 2>&1
}

run_variant lane1 1 false
run_variant lane2 2 false
run_variant lane2-spillover 2 true

"$PY" - "$DEV" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for name in ("lane1", "lane2", "lane2-spillover"):
    row = json.load(open(root / f"{name}.json"))
    assert row["counts"]["state_violations"] == 0
    assert row["counts"]["output_violations"] == 0
    assert row["counts"]["stale_commits"] == 0
    assert row["config"]["warmup"]["verifier_lane_exact"] is True
    rows.append({
        "variant": name,
        "wall_speedup": row["metrics"]["wall_speedup"],
        "gpu_normalized_speedup": row["metrics"]["gpu_normalized_speedup"],
        "p99": row["metrics"]["latency_p99"],
        "deadline_misses": row["counts"]["deadline_misses"],
        "terminal_spillover_authorities": row["counts"].get(
            "terminal_spillover_authorities", 0
        ),
    })
(root / "summary.json").write_text(
    json.dumps({
        "schema_version": 1,
        "study": "development-only terminal scheduler ablation",
        "claim_boundary": (
            "mechanism selection evidence; excluded from final W5 seed epoch"
        ),
        "rows": rows,
    }, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(rows, sort_keys=True))
PY

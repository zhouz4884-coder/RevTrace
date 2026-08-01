#!/usr/bin/env bash
# Development-only cross-scale gate for the state-entry terminal contract.
set -u
ROOT="$1"; MANIFEST="$2"; OUT="$3"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
DEV="$OUT/development/state-contract-crossscale"
mkdir -p "$DEV"
export PYTHONPATH="$PROJ/src"

run_model() {
  local family="$1" model="$2" max_new="$3"
  local threshold late_window late_threshold load_prompt load_threshold
  threshold="$(cat "$OUT/w4-final-threshold-${family}-c16.txt")"
  late_window="$(cat "$OUT/w4-final-late-window-${family}-c16.txt")"
  late_threshold="$(cat "$OUT/w4-final-late-threshold-${family}-c16.txt")"
  load_prompt="$(cat "$OUT/w4-final-high-load-prompt-${family}-c16.txt")"
  load_threshold="$(cat "$OUT/w4-final-high-load-threshold-${family}-c16.txt")"
  local context_args=()
  if [[ "$late_window" != none ]]; then
    context_args+=(--late-window-index "$late_window")
    context_args+=(--late-margin-threshold "$late_threshold")
  fi
  if [[ "$load_prompt" != none ]]; then
    context_args+=(--high-load-prompt-tokens "$load_prompt")
    context_args+=(--high-load-margin-threshold "$load_threshold")
  fi
  "$PY" "$RUNNER" workload \
    --model "$model" --model-name "whisper-${family}.en" \
    --manifest "$MANIFEST" --output "$DEV/${family}.json" \
    --oracle-cache "$DEV/oracle-${family}.json" \
    --system revtrace --sessions 16 --duration-seconds 90 \
    --window-seconds 10 --concurrency 16 --arrival sync \
    --seed 20272591 --margin-threshold "$threshold" \
    "${context_args[@]}" --max-new-tokens "$max_new" \
    --audit-probability 0.021 --slo-seconds 2.0 \
    --proposer-device cuda:0 --verifier-device cuda:1 \
    --verifier-lanes 1 --terminal-contract state-only \
    >"$DEV/${family}.log" 2>&1
}

run_model base "$ROOT/models/whisper-base.en" 96
run_model small "$ROOT/models/whisper-small.en" 80

"$PY" - "$DEV" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); rows=[]
for model in ("base","small"):
    x=json.load(open(root/f"{model}.json"))
    rows.append({
        "model":model,
        "wall_speedup":x["metrics"]["wall_speedup"],
        "gpu_normalized_speedup":x["metrics"]["gpu_normalized_speedup"],
        "stable_state_p99":x["metrics"]["latency_p99"],
        "display_p99":x["metrics"]["display_latency_p99"],
        "display_slo_goodput_speedup":x["metrics"][
            "display_slo_goodput_speedup"
        ],
        "state_violations":x["counts"]["state_violations"],
        "output_violations":x["counts"]["output_violations"],
    })
(root/"summary.json").write_text(json.dumps({
    "schema_version":1,
    "study":"development-only state contract cross-scale gate",
    "rows":rows,
},indent=2,sort_keys=True)+"\n")
print(json.dumps(rows,sort_keys=True))
PY

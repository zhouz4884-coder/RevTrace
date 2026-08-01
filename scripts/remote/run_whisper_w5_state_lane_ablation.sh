#!/usr/bin/env bash
# Development-only state-entry contract lane scaling ablation.
set -u
ROOT="$1"; MODEL="$2"; MANIFEST="$3"; OUT="$4"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
DEV="$OUT/development/state-lane-ablation"
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
for lanes in 2 3 4; do
  "$PY" "$RUNNER" workload \
    --model "$MODEL" --model-name whisper-base.en \
    --manifest "$MANIFEST" --output "$DEV/lane${lanes}.json" \
    --oracle-cache "$ORACLE" --system revtrace \
    --sessions 16 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --arrival sync --seed 20272590 \
    --margin-threshold "$threshold" "${context_args[@]}" \
    --max-new-tokens 96 --audit-probability 0.021 --slo-seconds 2.0 \
    --proposer-device cuda:0 --verifier-device cuda:1 \
    --verifier-lanes "$lanes" --terminal-contract state-only \
    >"$DEV/lane${lanes}.log" 2>&1
done
"$PY" - "$DEV" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1]); rows=[]
for lanes in (2,3,4):
    row=json.load(open(root/f"lane{lanes}.json"))
    assert row["counts"]["state_violations"] == 0
    assert row["counts"]["stale_commits"] == 0
    rows.append({
        "lanes":lanes,
        "wall_speedup":row["metrics"]["wall_speedup"],
        "gpu_normalized_speedup":row["metrics"]["gpu_normalized_speedup"],
        "p99":row["metrics"]["latency_p99"],
        "deadline_misses":row["counts"]["deadline_misses"],
    })
(root/"summary.json").write_text(json.dumps({
    "schema_version":1,
    "study":"development-only state contract lane scaling",
    "rows":rows,
},indent=2,sort_keys=True)+"\n")
print(json.dumps(rows,sort_keys=True))
PY

#!/usr/bin/env bash
# Replay admitted W6 state writes after timing to extract repeat-stable roots.
set -euo pipefail

ROOT="$1"
OUT="$2"
MODEL_SLUG="${3:-small}"
DEVICE="${4:-cuda:1}"
WAIT_PID="${5:-}"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_quality.py"
DEV="$OUT/development/w6-state-root-${MODEL_SLUG}"
mkdir -p "$DEV"
export PYTHONPATH="$PROJ/src"
if [[ -n "$WAIT_PID" ]]; then
  while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 20; done
fi

tau="$(cat "$OUT/w4-final-threshold-${MODEL_SLUG}-c16.txt")"
lw="$(cat "$OUT/w4-final-late-window-${MODEL_SLUG}-c16.txt")"
lt="$(cat "$OUT/w4-final-late-threshold-${MODEL_SLUG}-c16.txt")"
hp="$(cat "$OUT/w4-final-high-load-prompt-${MODEL_SLUG}-c16.txt")"
ht="$(cat "$OUT/w4-final-high-load-threshold-${MODEL_SLUG}-c16.txt")"
context=()
if [[ "$lw" != none ]]; then
  context+=(--late-window-index "$lw" --late-margin-threshold "$lt")
fi
if [[ "$hp" != none ]]; then
  context+=(
    --high-load-prompt-tokens "$hp"
    --high-load-margin-threshold "$ht"
  )
fi
max_new=96
if [[ "$MODEL_SLUG" == small ]]; then max_new=80; fi

set +e
"$PY" "$RUNNER" \
  --model "$ROOT/models/whisper-${MODEL_SLUG}.en" \
  --model-name "whisper-${MODEL_SLUG}.en" \
  --manifest "$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json" \
  --output "$DEV/result.json" \
  --sessions-per-split 32 \
  --duration-seconds 90 \
  --window-seconds 10 \
  --concurrency 16 \
  --margin-threshold "$tau" "${context[@]}" \
  --seed 20272592 \
  --bootstrap-seed 20272593 \
  --bootstrap-replicates 5000 \
  --max-new-tokens "$max_new" \
  --reference-max-new-tokens 96 \
  --no-deferred-terminal-authority \
  --diagnostic-post-timing-state \
  --device "$DEVICE" >"$DEV/run.log" 2>&1
rc="$?"
set -e
"$PY" - "$DEV/result.json" <<'PY'
import json
import sys
row = json.load(open(sys.argv[1]))
print(json.dumps({
    "quality_decision": row["decision"],
    "catastrophic_outliers": row["counts"]["catastrophic_outliers"],
    "mean_wer_delta_pp": row["metrics"]["mean_wer_delta_pp"],
    "post_timing_state_diagnostic": row[
        "post_timing_state_diagnostic"
    ],
}, indent=2, sort_keys=True))
PY
echo "runner_rc=$rc"
touch "$OUT/.w6-state-root-${MODEL_SLUG}-complete"

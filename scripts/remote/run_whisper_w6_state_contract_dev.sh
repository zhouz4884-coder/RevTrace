#!/usr/bin/env bash
# Development-only W6 quality gate for the state-only terminal contract.
set -u
ROOT="$1"; OUT="$2"; MODEL_SLUG="$3"; DEVICE="$4"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_quality.py"
DEV="$OUT/development/w6-state-contract-${MODEL_SLUG}"
mkdir -p "$DEV"
export PYTHONPATH="$PROJ/src"
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
"$PY" "$RUNNER" \
  --model "$ROOT/models/whisper-${MODEL_SLUG}.en" \
  --model-name "whisper-${MODEL_SLUG}.en" \
  --manifest "$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json" \
  --output "$DEV/result.json" --sessions-per-split 32 \
  --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --margin-threshold "$tau" "${context[@]}" \
  --seed 20272592 --bootstrap-seed 20272593 \
  --bootstrap-replicates 5000 --max-new-tokens "$max_new" \
  --reference-max-new-tokens 96 --no-deferred-terminal-authority \
  --device "$DEVICE" >"$DEV/run.log" 2>&1

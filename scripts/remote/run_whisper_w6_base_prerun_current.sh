#!/usr/bin/env bash
# Produce the final-protocol base.en W6 quality prerun on an otherwise idle GPU.
set -u

ROOT="$1"
BASE_MODEL="$2"
OUT="$3"
QUALITY_MANIFEST="${4:-$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json}"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_quality.py"

tau="$(cat "$OUT/w4-final-threshold-base-c16.txt")"
late_w="$(cat "$OUT/w4-final-late-window-base-c16.txt")"
late_tau="$(cat "$OUT/w4-final-late-threshold-base-c16.txt")"
load_p="$(cat "$OUT/w4-final-high-load-prompt-base-c16.txt")"
load_tau="$(cat "$OUT/w4-final-high-load-threshold-base-c16.txt")"
context=()
if [[ "$late_w" != none && "$late_tau" != none ]]; then
  context+=(--late-window-index "$late_w" --late-margin-threshold "$late_tau")
fi
if [[ "$load_p" != none && "$load_tau" != none ]]; then
  context+=(
    --high-load-prompt-tokens "$load_p"
    --high-load-margin-threshold "$load_tau"
  )
fi

export PYTHONPATH="$PROJ/src"
"$PY" "$RUNNER" \
  --model "$BASE_MODEL" \
  --model-name whisper-base.en \
  --manifest "$QUALITY_MANIFEST" \
  --output "$OUT/w6-quality-base-prerun.json" \
  --sessions-per-split 64 \
  --duration-seconds 90 \
  --window-seconds 10 \
  --concurrency 16 \
  --margin-threshold "$tau" \
  "${context[@]}" \
  --seed 20260811 \
  --bootstrap-seed 20260812 \
  --bootstrap-replicates 10000 \
  --max-new-tokens 96 \
  --authority-max-new-tokens 96 \
  --reference-max-new-tokens 96 \
  --no-deferred-terminal-authority \
  --device cuda:0

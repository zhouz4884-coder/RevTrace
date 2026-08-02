#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft/untouched"
MANIFEST="$ROOT/datasets/revtrace/librispeech/r9-untouched-50s.json"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

run_model() {
  local gpu=$1 model=$2
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_cross_granularity_probe.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" \
    --coarse-result "$OUT/$model-tailfix15-30-diagnostic.json" \
    --output "$OUT/$model-cross-granularity-development.json" \
    --sessions-per-split 64 --duration-seconds 50 --window-seconds 10 \
    --seed 2026091001 --device cuda:0 --concurrency 16 \
    >"$OUT/$model-cross-granularity-development.log" 2>&1
}

run_model 0 tiny & tiny_pid=$!
run_model 1 base & base_pid=$!
wait "$tiny_pid"
wait "$base_pid"
run_model 0 small

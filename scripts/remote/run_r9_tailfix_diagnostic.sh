#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft/untouched"
MANIFEST="$ROOT/datasets/revtrace/librispeech/r9-untouched-50s.json"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

run_model() {
  local gpu=$1 model=$2 boot=$3
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" --source-quality "$OUT/$model-untouched-source.json" \
    --output "$OUT/$model-tailfix15-30-diagnostic.json" \
    --sessions-per-split 64 --duration-seconds 50 --window-seconds 10 \
    --seed 2026091001 --bootstrap-seed "$boot" --device cuda:0 \
    --concurrency 16 --modes adaptive15_30_batch \
    --adaptive-min-seconds 15 --adaptive-max-seconds 30 \
    --segment-salvage-yield-threshold 1.0 \
    --session-salvage-on-conflict --quality-only \
    >"$OUT/$model-tailfix15-30-diagnostic.log" 2>&1
}

run_model 0 tiny 2026091601 & tiny_pid=$!
run_model 1 base 2026091701 & base_pid=$!
wait "$tiny_pid"
wait "$base_pid"
run_model 0 small 2026091801

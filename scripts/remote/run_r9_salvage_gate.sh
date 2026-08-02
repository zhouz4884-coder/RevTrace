#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality-r8-pristine-confirm.json"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

run_model() {
  local gpu=$1 model=$2 seed=$3 boot=$4 source=$5 continuous=$6
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" \
    --source-quality "$ROOT/results/revtrace/r8_csdr/$source" \
    --continuous-result "$ROOT/results/revtrace/r8_csdr/$continuous" \
    --output "$OUT/$model-adaptive-salvage-v2-dev.json" \
    --seed "$seed" --bootstrap-seed "$boot" --device cuda:0 \
    --concurrency 16 --modes adaptive15_30_batch \
    --segment-salvage-yield-threshold 1.0 \
    --session-salvage-on-conflict \
    >"$OUT/$model-adaptive-salvage-v2-dev.log" 2>&1
}

run_model 0 tiny 2026083101 2026090181 \
  r8-pristine-tiny-confirm-source.json \
  r8-pristine-tiny-confirm-samepromptfix.json &
tiny_pid=$!
run_model 1 small 2026083001 2026090191 \
  r8-pristine-small-confirm-source.json \
  r8-pristine-small-confirm-samepromptfix.json &
small_pid=$!
wait "$tiny_pid"
wait "$small_pid"
run_model 0 base 2026083001 2026090201 \
  r8-pristine-confirm-source.json \
  r8-pristine-confirm-samepromptfix.json

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
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_coverage_fallback.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" --source-quality "$OUT/$model-untouched-source.json" \
    --coarse-result "$OUT/$model-tailfix15-30-diagnostic.json" \
    --coverage-probe "$OUT/$model-cross-granularity-development.json" \
    --output "$OUT/$model-asym37-display-development.json" \
    --coverage-threshold 0.37 --coverage-asymmetry-margin 0.10 \
    --structural-coverage-threshold 0.30 \
    --coverage-scope segment \
    --repair-mode display-segment \
    --post-rebase-forward-threshold 0.20 \
    --post-rebase-reverse-ceiling 0.20 \
    --sessions-per-split 64 \
    --duration-seconds 50 --window-seconds 10 --seed 2026091001 \
    --bootstrap-seed "$boot" --device cuda:0 \
    >"$OUT/$model-asym37-display-development.log" 2>&1
}

run_model 0 tiny 2026091901 & tiny_pid=$!
run_model 1 base 2026092001 & base_pid=$!
wait "$tiny_pid" || true
wait "$base_pid" || true
run_model 0 small 2026092101 || true

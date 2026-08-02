#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft/revised_rule_validation"
DEV="$ROOT/results/revtrace/r9_dgft"
FINAL1="$DEV/final_holdout"
mkdir -p "$OUT"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

run_model() {
  local gpu=$1 model=$2 boot=$3
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_coverage_fallback.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$ROOT/datasets/revtrace/librispeech/r9-untouched-50s.json" \
    --source-quality "$DEV/untouched/$model-untouched-source.json" \
    --coarse-result "$DEV/local_salvage/$model-conditional-development.json" \
    --coverage-probe "$DEV/untouched/$model-cross-granularity-development.json" \
    --output "$OUT/$model-development-asym20.json" \
    --coverage-threshold 0.20 --coverage-asymmetry-margin 0.10 \
    --structural-coverage-threshold 0.20 --coverage-scope segment \
    --repair-mode display-segment --post-rebase-forward-threshold 0.20 \
    --post-rebase-reverse-ceiling 0.20 --sessions-per-split 64 \
    --duration-seconds 50 --window-seconds 10 --seed 2026091001 \
    --bootstrap-seed "$boot" --device cuda:0 \
    >"$OUT/$model-development-asym20.log" 2>&1 || true

  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_coverage_fallback.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$ROOT/datasets/revtrace/librispeech/r9-final-untouched.json" \
    --source-quality "$FINAL1/$model-source.json" \
    --coarse-result "$FINAL1/$model-coarse.json" \
    --coverage-probe "$FINAL1/$model-coverage-probe.json" \
    --output "$OUT/$model-validation-asym20.json" \
    --coverage-threshold 0.20 --coverage-asymmetry-margin 0.10 \
    --structural-coverage-threshold 0.20 --coverage-scope segment \
    --repair-mode display-segment --post-rebase-forward-threshold 0.20 \
    --post-rebase-reverse-ceiling 0.20 --sessions-per-split 20 \
    --duration-seconds 30 --window-seconds 10 --seed 2026100101 \
    --bootstrap-seed "$((boot + 100))" --device cuda:0 \
    >"$OUT/$model-validation-asym20.log" 2>&1 || true
}

run_model 0 tiny 2026101101 & p0=$!
run_model 1 base 2026101201 & p1=$!
wait "$p0"
wait "$p1"
run_model 0 small 2026101301


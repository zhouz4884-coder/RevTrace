#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft/semantic_escalation_validation"
DEV="$ROOT/results/revtrace/r9_dgft"
mkdir -p "$OUT"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

run_model() {
  local gpu=$1 model=$2 boot=$3
  # The coarse input contains local 10-second salvage but deliberately no
  # automatic full-session fallback.  Semantic escalation is decided only by
  # boundary-adjusted directional evidence after local salvage.
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_coverage_fallback.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$ROOT/datasets/revtrace/librispeech/r9-untouched-50s.json" \
    --source-quality "$DEV/untouched/$model-untouched-source.json" \
    --coarse-result "$DEV/local_salvage/$model-development.json" \
    --coverage-probe "$DEV/untouched/$model-cross-granularity-development.json" \
    --output "$OUT/$model-development-semantic-escalation.json" \
    --coverage-threshold 0.20 --coverage-asymmetry-margin 0.15 \
    --structural-coverage-threshold 0.20 --coverage-scope segment \
    --repair-mode display-segment --post-rebase-forward-threshold 0.20 \
    --post-rebase-reverse-ceiling 0.20 --sessions-per-split 64 \
    --duration-seconds 50 --window-seconds 10 --seed 2026091001 \
    --bootstrap-seed "$boot" --device cuda:0 \
    >"$OUT/$model-development-semantic-escalation.log" 2>&1 || true
}

run_model 0 tiny 2026103101 & p0=$!
run_model 1 base 2026103201 & p1=$!
wait "$p0"
wait "$p1"
run_model 0 small 2026103301

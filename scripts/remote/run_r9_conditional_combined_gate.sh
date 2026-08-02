#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft/local_salvage"
SOURCE="$ROOT/results/revtrace/r9_dgft/untouched"
MANIFEST="$ROOT/datasets/revtrace/librispeech/r9-untouched-50s.json"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

run_model() {
  local model=$1 boot=$2
  "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" --output "$OUT/$model-conditional-development.json" \
    --sessions-per-split 64 --duration-seconds 50 --window-seconds 10 \
    --seed 2026091001 --bootstrap-seed "$boot" --device cuda:0 \
    --concurrency 16 --modes adaptive15_30_batch \
    --adaptive-min-seconds 15 --adaptive-max-seconds 30 \
    --segment-salvage-yield-threshold 1.0 \
    --session-salvage-on-conflict --quality-only \
    >"$OUT/$model-conditional-development.log" 2>&1
  "$PY" "$PROJ/scripts/remote/run_r9_coverage_fallback.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" \
    --source-quality "$SOURCE/$model-untouched-source.json" \
    --coarse-result "$OUT/$model-conditional-development.json" \
    --coverage-probe "$SOURCE/$model-cross-granularity-development.json" \
    --output "$OUT/$model-conditional-combined-development.json" \
    --coverage-threshold 0.37 --coverage-asymmetry-margin 0.10 \
    --structural-coverage-threshold 0.30 --coverage-scope segment \
    --repair-mode display-segment --post-rebase-forward-threshold 0.20 \
    --post-rebase-reverse-ceiling 0.20 --sessions-per-split 64 \
    --duration-seconds 50 --window-seconds 10 --seed 2026091001 \
    --bootstrap-seed "$((boot + 100))" --device cuda:0 \
    >"$OUT/$model-conditional-combined-development.log" 2>&1
}

for model in "$@"; do
  case "$model" in
    tiny) run_model tiny 2026093001 ;;
    base) run_model base 2026093101 ;;
    small) run_model small 2026093201 ;;
    *) echo "unknown model: $model" >&2; exit 2 ;;
  esac
done

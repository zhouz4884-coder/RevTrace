#!/usr/bin/env bash
set -u
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft/service/conditional_matrix"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality-r8-pristine-confirm.json"
mkdir -p "$OUT"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

run_one() {
  local model=$1 arrival=$2 seed=$3
  local name="$model-$arrival-$seed"
  "$PY" "$PROJ/scripts/remote/run_r9_dgft_service.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" --output "$OUT/$name.json" \
    --sessions 16 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --arrival "$arrival" --arrival-scale-seconds 0.02 \
    --coalesce-seconds 0.5 --seed "$seed" \
    --proposer-device cuda:0 --authority-device cuda:1 \
    --coverage-threshold 0.20 --coverage-asymmetry-margin 0.10 \
    --structural-coverage-threshold 0.20 \
    --session-salvage-on-conflict \
    --post-rebase-forward-threshold 0.20 \
    --post-rebase-reverse-ceiling 0.20 \
    >"$OUT/$name.log" 2>&1 || true
}

for arrival in sync poisson; do
  for seed in 2026101001 2026101002 2026101003 2026101004 2026101005; do
    run_one base "$arrival" "$seed"
  done
done
for model in tiny small; do
  for seed in 2026102001 2026102002 2026102003; do
    run_one "$model" sync "$seed"
  done
done

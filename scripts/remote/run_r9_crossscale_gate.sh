#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality-r8-pristine-confirm.json"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

CUDA_VISIBLE_DEVICES=0 "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
  --model "$ROOT/models/whisper-tiny.en" --model-name whisper-tiny.en \
  --manifest "$MANIFEST" \
  --source-quality "$ROOT/results/revtrace/r8_csdr/r8-pristine-tiny-confirm-source.json" \
  --continuous-result "$ROOT/results/revtrace/r8_csdr/r8-pristine-tiny-confirm-samepromptfix.json" \
  --output "$OUT/tiny-adaptive-reset-batched-dev.json" \
  --seed 2026083101 --bootstrap-seed 2026090141 --device cuda:0 \
  --concurrency 16 --modes adaptive15_30_reset_batch \
  >"$OUT/tiny-adaptive-reset-batched-dev.log" 2>&1 &
tiny_pid=$!

CUDA_VISIBLE_DEVICES=1 "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
  --model "$ROOT/models/whisper-small.en" --model-name whisper-small.en \
  --manifest "$MANIFEST" \
  --source-quality "$ROOT/results/revtrace/r8_csdr/r8-pristine-small-confirm-source.json" \
  --continuous-result "$ROOT/results/revtrace/r8_csdr/r8-pristine-small-confirm-samepromptfix.json" \
  --output "$OUT/small-adaptive-reset-batched-dev.json" \
  --seed 2026083001 --bootstrap-seed 2026090151 --device cuda:0 \
  --concurrency 16 --modes adaptive15_30_reset_batch \
  >"$OUT/small-adaptive-reset-batched-dev.log" 2>&1 &
small_pid=$!

echo "tiny_pid=$tiny_pid small_pid=$small_pid"
wait "$tiny_pid"
wait "$small_pid"

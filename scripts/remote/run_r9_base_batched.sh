#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"
CUDA_VISIBLE_DEVICES=0 "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
  --model "$ROOT/models/whisper-base.en" --model-name whisper-base.en \
  --manifest "$ROOT/datasets/revtrace/librispeech/whisper-w-quality-r8-pristine-confirm.json" \
  --source-quality "$ROOT/results/revtrace/r8_csdr/r8-pristine-confirm-source.json" \
  --continuous-result "$ROOT/results/revtrace/r8_csdr/r8-pristine-confirm-samepromptfix.json" \
  --output "$OUT/base-adaptive-batched-v1.json" \
  --seed 2026083001 --bootstrap-seed 2026090131 --device cuda:0 \
  --concurrency 16 \
  --modes adaptive15_30_batch adaptive15_30_reset_batch \
  >"$OUT/base-adaptive-batched-v1.log" 2>&1

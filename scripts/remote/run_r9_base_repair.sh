#!/usr/bin/env bash
set -euo pipefail

ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality-r8-pristine-confirm.json"
SOURCE="$ROOT/results/revtrace/r8_csdr/r8-pristine-confirm-source.json"
CONTINUOUS="$ROOT/results/revtrace/r8_csdr/r8-pristine-confirm-samepromptfix.json"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"
mkdir -p "$OUT"

CUDA_VISIBLE_DEVICES=0 "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
  --model "$ROOT/models/whisper-base.en" \
  --model-name whisper-base.en \
  --manifest "$MANIFEST" \
  --source-quality "$SOURCE" \
  --continuous-result "$CONTINUOUS" \
  --output "$OUT/base-sequential-v2.json" \
  --seed 2026083001 \
  --bootstrap-seed 2026090111 \
  --device cuda:0 \
  --modes sequential \
  >"$OUT/base-sequential-v2.log" 2>&1 &
seq_pid=$!

CUDA_VISIBLE_DEVICES=1 "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
  --model "$ROOT/models/whisper-base.en" \
  --model-name whisper-base.en \
  --manifest "$MANIFEST" \
  --source-quality "$SOURCE" \
  --continuous-result "$CONTINUOUS" \
  --output "$OUT/base-adaptive-v1.json" \
  --seed 2026083001 \
  --bootstrap-seed 2026090121 \
  --device cuda:0 \
  --modes adaptive15_30 adaptive15_30_reset \
  >"$OUT/base-adaptive-v1.log" 2>&1 &
adaptive_pid=$!

echo "sequential_pid=$seq_pid adaptive_pid=$adaptive_pid"
wait "$seq_pid"
wait "$adaptive_pid"

#!/usr/bin/env bash
set -euo pipefail
ROOT=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
PROJECT="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json"
POLICY="$ROOT/results/revtrace/r7_efsc/whisper_base_preflight/frozen_policy.json"
OUT="$ROOT/results/revtrace/r8_csdr/service-budgeted-cutset-p32r48"
mkdir -p "$OUT"
cd "$PROJECT"
export PYTHONPATH="$PROJECT/src:$PROJECT/scripts/remote"
for arrival in sync poisson; do
  if [[ "$arrival" == sync ]]; then base=2026082500; suite=w1; else base=2026082600; suite=w2; fi
  for index in 1 2 3 4 5; do
    seed=$((base + index))
    "$PY" scripts/remote/run_r8_dual_lane_service.py \
      --model "$MODEL" \
      --manifest "$MANIFEST" \
      --efsc-policy "$POLICY" \
      --output "$OUT/${suite}-seed${seed}.json" \
      --sessions 16 --duration-seconds 90 --window-seconds 10 \
      --concurrency 16 --arrival "$arrival" --seed "$seed" \
      --max-new-tokens 96 --proposer-step-budget 32 \
      --replay-prompt-tokens 223 --replay-step-budget 48 \
      --proposer-device cuda:0 --replay-device cuda:1 || true
  done
done
touch "$OUT/READY"

#!/usr/bin/env bash
set -euo pipefail

# Zero-shot scale-transfer audit.  This script intentionally reuses the
# Whisper-base EFSC/CSM policies and the same disjoint confirmation manifest;
# no threshold is tuned for whisper-tiny.en.
ROOT=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
PROJECT="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-tiny.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality-r8-pristine-confirm.json"
EFSC_POLICY="$ROOT/results/revtrace/r7_efsc/whisper_base_preflight/frozen_policy.json"
CSM_POLICY="$ROOT/results/revtrace/r8_csdr/csm-frozen-forest.json"
OUT="$ROOT/results/revtrace/r8_csdr"
SOURCE="$OUT/r8-pristine-tiny-confirm-source.json"
QUALITY="$OUT/r8-pristine-tiny-confirm-budget48-fullcontext.json"
SERVICE="$OUT/service-budgeted-cutset-p32r48/tiny-transfer-seed2026083101.json"
LOG="$ROOT/logs/revtrace/r8-tiny-transfer.log"

mkdir -p "$OUT/service-budgeted-cutset-p32r48" "$(dirname "$LOG")"
cd "$PROJECT"
export PYTHONPATH="$PROJECT/src:$PROJECT/scripts/remote"

{
  echo "[tiny-transfer] source quality"
  if [[ ! -s "$SOURCE" ]]; then
    CUDA_VISIBLE_DEVICES=0 "$PY" scripts/remote/run_r7_whisper_quality.py \
      --model "$MODEL" --model-name whisper-tiny.en \
      --manifest "$MANIFEST" --policy "$EFSC_POLICY" --output "$SOURCE" \
      --sessions-per-split 64 --duration-seconds 90 --window-seconds 10 \
      --concurrency 16 --max-new-tokens 96 --seed 2026083101 \
      --bootstrap-seed 2026083102 --bootstrap-replicates 10000 --device cuda:0 || true
  fi

  echo "[tiny-transfer] R8 quality"
  CUDA_VISIBLE_DEVICES=0 "$PY" scripts/remote/run_r8_csdr_quality.py \
    --model "$MODEL" --manifest "$MANIFEST" --source-quality "$SOURCE" \
    --efsc-policy "$EFSC_POLICY" --csm-policy "$CSM_POLICY" \
    --output "$QUALITY" --sessions-per-split 64 --duration-seconds 90 \
    --window-seconds 10 --concurrency 16 --max-new-tokens 96 \
    --replay-step-budget 48 --seed 2026083101 \
    --bootstrap-seed 2026083103 --bootstrap-replicates 10000 --device cuda:0 \
    --selector canonical-replay --structural-rule-mode absolute \
    --agreement-threshold 1.0 --recovery-score-threshold 0.05 \
    --csm-trigger-threshold 0.79 --lineage-reconciliation \
    --continuous-lineage-replay --replay-prompt-tokens 223 || true

  echo "[tiny-transfer] two-GPU service"
  "$PY" scripts/remote/run_r8_dual_lane_service.py \
    --model "$MODEL" --manifest "$MANIFEST" --efsc-policy "$EFSC_POLICY" \
    --output "$SERVICE" --sessions 16 --duration-seconds 90 \
    --window-seconds 10 --concurrency 16 --arrival sync \
    --seed 2026083101 --max-new-tokens 96 --proposer-step-budget 32 \
    --replay-prompt-tokens 223 --replay-step-budget 48 \
    --proposer-device cuda:0 --replay-device cuda:1 --slo-seconds 1.9
} 2>&1 | tee "$LOG"

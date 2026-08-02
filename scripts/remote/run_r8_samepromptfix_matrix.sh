#!/usr/bin/env bash
set -euo pipefail

ROOT=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
PROJECT="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality-r8-pristine-confirm.json"
EFSC="$ROOT/results/revtrace/r7_efsc/whisper_base_preflight/frozen_policy.json"
CSM="$ROOT/results/revtrace/r8_csdr/csm-frozen-forest.json"
OUT="$ROOT/results/revtrace/r8_csdr"
LOG="$ROOT/logs/revtrace"

cd "$PROJECT"
export PYTHONPATH="$PROJECT/src:$PROJECT/scripts/remote"

run_quality() {
  local gpu=$1
  local model=$2
  local source=$3
  local output=$4
  local seed=$5
  local log=$6
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" scripts/remote/run_r8_csdr_quality.py \
    --model "$model" --manifest "$MANIFEST" --source-quality "$source" \
    --efsc-policy "$EFSC" --csm-policy "$CSM" --output "$output" \
    --sessions-per-split 64 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --max-new-tokens 96 --replay-step-budget 48 \
    --seed "$seed" --bootstrap-seed "$((seed + 2))" \
    --bootstrap-replicates 10000 --device cuda:0 \
    --selector canonical-replay --structural-rule-mode absolute \
    --agreement-threshold 1.0 --recovery-score-threshold 0.05 \
    --csm-trigger-threshold 0.79 --lineage-reconciliation \
    --continuous-lineage-replay --replay-prompt-tokens 223 \
    >"$log" 2>&1 || true
}

run_quality 0 "$ROOT/models/whisper-base.en" \
  "$OUT/r8-pristine-confirm-source.json" \
  "$OUT/r8-pristine-confirm-samepromptfix.json" 2026083001 \
  "$LOG/r8-base-samepromptfix.log" &
base_pid=$!
run_quality 1 "$ROOT/models/whisper-tiny.en" \
  "$OUT/r8-pristine-tiny-confirm-source.json" \
  "$OUT/r8-pristine-tiny-confirm-samepromptfix.json" 2026083101 \
  "$LOG/r8-tiny-samepromptfix.log" &
tiny_pid=$!
wait "$base_pid" "$tiny_pid"

run_quality 0 "$ROOT/models/whisper-small.en" \
  "$OUT/r8-pristine-small-confirm-source.json" \
  "$OUT/r8-pristine-small-confirm-samepromptfix.json" 2026083001 \
  "$LOG/r8-small-samepromptfix.log"

touch "$OUT/SAMEPROMPTFIX_READY"


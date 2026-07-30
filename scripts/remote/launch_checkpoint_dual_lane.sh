#!/usr/bin/env bash
set -uo pipefail

MODE="${1:?mode required: patch|crosslane|calibrate|audit|seed|quality}"
ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
REPO="$ROOT/projects/revtrace"
PY="$ROOT/envs/revbatch-cu128/bin/python"
MODEL="$ROOT/models/Qwen3-ASR-0.6B"
MANIFEST="$ROOT/datasets/revtrace/long_horizon_annotated_128.json"
OUTDIR="${REVTRACE_OUTDIR:-$REPO/results/checkpoint_dual_lane}"
CROSSLANE="$OUTDIR/cross_lane_gate.json"
CHECKPOINT_SECONDS="${REVTRACE_CHECKPOINT_SECONDS:-30}"
mkdir -p "$OUTDIR"
cd "$REPO"

status=0
case "$MODE" in
  patch)
    "$PY" scripts/remote/patch_vllm_batch_invariant_logsoftmax.py \
      --output "$OUTDIR/vllm_batch_invariant_logsoftmax_patch.json" \
      || status=$?
    ;;
  crosslane)
    REVTRACE_CODE_COMMIT="${REVTRACE_CODE_COMMIT:-C2_SERVICE_MATCH}" \
      "$PY" scripts/remote/run_cross_lane_checkpoint_gate.py \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --output "$CROSSLANE" \
      --duration-seconds 120 \
      --checkpoint-seconds "$CHECKPOINT_SECONDS" \
      --concurrency 12 \
      --gpu0 0 \
      --gpu1 1 || status=$?
    ;;
  quality)
    "$PY" scripts/remote/run_checkpoint_rebase_quality.py \
      --experiment-id CHECKPOINT-DUAL-LANE-QUALITY-C6 \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --output "$OUTDIR/checkpoint_rebase_quality_16x2.json" \
      --duration-seconds 120 \
      --checkpoint-seconds "$CHECKPOINT_SECONDS" \
      --sessions-per-language 16 \
      --evaluation-batch-size 8 \
      --gpu 0 \
      --maximum-primary-error-delta 0.02 \
      --maximum-catastrophic-outliers 0 \
      --bootstrap-replicates 10000 \
      --bootstrap-seed 20260806 || status=$?
    ;;
  calibrate)
    "$PY" scripts/remote/run_phase5a_live_adaptive.py \
      --experiment-id CHECKPOINT-DUAL-LANE-CALIBRATION-C4 \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --output "$OUTDIR/calibration.json" \
      --minimum-audits 1350 \
      --episode-seconds 120 \
      --episode-seed-base 20260807 \
      --proposer-gpu 0 \
      --verifier-gpu 1 \
      --canonical-batch-size 12 \
      --canonical-dtype float16 \
      --service-mode full-selective \
      --intermediate-authority singleton \
      --dual-lane-intermediate-authority \
      --cross-lane-compatibility-artifact "$CROSSLANE" \
      --audio-construction distinct-sequence \
      --inter-utterance-silence-ms 250 \
      --checkpoint-seconds "$CHECKPOINT_SECONDS" \
      --declared-maximum-prefix-tokens 512 \
      --declared-maximum-input-tokens 4096 \
      --max-model-length 4096 \
      --statistical-risk-gate \
      --suppress-certified-terminal-proposer \
      --continue-same-contract-stages \
      --non-gating-stage calibration \
      --stage calibration:12:2:mixed \
      --stage heldout:12:1:mixed || status=$?
    ;;
  audit)
    threshold="${REVTRACE_FROZEN_THRESHOLD:?set REVTRACE_FROZEN_THRESHOLD}"
    "$PY" scripts/remote/run_checkpoint_dual_lane_shadow_audit.py \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --cross-lane-compatibility-artifact "$CROSSLANE" \
      --output "$OUTDIR/anytime_risk_audit.json" \
      --target-risk-entries 30000 \
      --duration-seconds 120 \
      --checkpoint-seconds "$CHECKPOINT_SECONDS" \
      --concurrency 12 \
      --margin-threshold "$threshold" \
      --audit-probability 0.021 \
      --alpha 0.05 \
      --delta 0.005 \
      --seed 20260808 || status=$?
    ;;
  seed)
    seed="${REVTRACE_SEED:?set REVTRACE_SEED}"
    threshold="${REVTRACE_FROZEN_THRESHOLD:?set REVTRACE_FROZEN_THRESHOLD}"
    "$PY" scripts/remote/run_phase5a_live_adaptive.py \
      --experiment-id "CHECKPOINT-DUAL-LANE-SEED-${seed}" \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --output "$OUTDIR/seed_${seed}.json" \
      --minimum-audits 1350 \
      --episode-seconds 120 \
      --episode-seed-base "$seed" \
      --proposer-gpu 0 \
      --verifier-gpu 1 \
      --canonical-batch-size 12 \
      --canonical-dtype float16 \
      --service-mode full-selective \
      --intermediate-authority singleton \
      --dual-lane-intermediate-authority \
      --cross-lane-compatibility-artifact "$CROSSLANE" \
      --audio-construction distinct-sequence \
      --inter-utterance-silence-ms 250 \
      --checkpoint-seconds "$CHECKPOINT_SECONDS" \
      --declared-maximum-prefix-tokens 512 \
      --declared-maximum-input-tokens 4096 \
      --max-model-length 4096 \
      --statistical-risk-gate \
      --suppress-certified-terminal-proposer \
      --frozen-threshold "heldout:${threshold}" \
      --stage heldout:12:1:mixed || status=$?
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    status=64
    ;;
esac
printf '%s\n' "$status" > "$OUTDIR/$MODE.exit"
exit "$status"

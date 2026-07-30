#!/usr/bin/env bash
set -uo pipefail

MODE="${1:?mode required: calibrate|audit|seed|quality}"
ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
REPO="$ROOT/projects/revtrace"
PY="$ROOT/envs/revbatch-cu128/bin/python"
MODEL="$ROOT/models/Qwen3-ASR-0.6B"
MANIFEST="$ROOT/datasets/revtrace/long_horizon_annotated_128.json"
OUTDIR="${REVTRACE_OUTDIR:-$REPO/results/checkpoint20_ordinary_authority}"
CHECKPOINT_SECONDS=20
mkdir -p "$OUTDIR"
cd "$REPO"

status=0
case "$MODE" in
  calibrate)
    # The 0.03125 counterexample was observed by the same-input causal probe
    # for this exact proposer/checkpoint contract. It is adaptation evidence,
    # not held-out evidence, and therefore only seeds the calibration stage.
    "$PY" scripts/remote/run_phase5a_live_adaptive.py \
      --experiment-id CHECKPOINT20-ORDINARY-AUTHORITY-CALIBRATION \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --output "$OUTDIR/calibration.json" \
      --minimum-audits 1350 \
      --episode-seconds 120 \
      --episode-seed-base 20260812 \
      --proposer-gpu 0 \
      --verifier-gpu 1 \
      --canonical-batch-size 12 \
      --canonical-dtype float16 \
      --service-mode full-selective \
      --intermediate-authority singleton \
      --audio-construction distinct-sequence \
      --inter-utterance-silence-ms 250 \
      --checkpoint-seconds "$CHECKPOINT_SECONDS" \
      --declared-maximum-prefix-tokens 512 \
      --declared-maximum-input-tokens 4096 \
      --max-model-length 4096 \
      --statistical-risk-gate \
      --suppress-certified-terminal-proposer \
      --phase6-asymmetric-memory \
      --failure-floor calibration:0.03125 \
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
      --output "$OUTDIR/anytime_risk_audit.json" \
      --target-risk-entries 30000 \
      --duration-seconds 120 \
      --checkpoint-seconds "$CHECKPOINT_SECONDS" \
      --concurrency 12 \
      --margin-threshold "$threshold" \
      --audit-probability 0.021 \
      --alpha 0.05 \
      --delta 0.005 \
      --seed 20260818 || status=$?
    ;;
  seed)
    seed="${REVTRACE_SEED:?set REVTRACE_SEED}"
    threshold="${REVTRACE_FROZEN_THRESHOLD:?set REVTRACE_FROZEN_THRESHOLD}"
    "$PY" scripts/remote/run_phase5a_live_adaptive.py \
      --experiment-id "CHECKPOINT20-ORDINARY-AUTHORITY-SEED-${seed}" \
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
      --audio-construction distinct-sequence \
      --inter-utterance-silence-ms 250 \
      --checkpoint-seconds "$CHECKPOINT_SECONDS" \
      --declared-maximum-prefix-tokens 512 \
      --declared-maximum-input-tokens 4096 \
      --max-model-length 4096 \
      --statistical-risk-gate \
      --suppress-certified-terminal-proposer \
      --skip-post-stage-replay \
      --frozen-threshold "heldout:${threshold}" \
      --stage heldout:12:1:mixed || status=$?
    ;;
  quality)
    "$PY" scripts/remote/run_checkpoint_rebase_quality.py \
      --experiment-id CHECKPOINT20-ORDINARY-AUTHORITY-QUALITY \
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
      --bootstrap-seed 20260819 || status=$?
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    status=64
    ;;
esac
printf '%s\n' "$status" > "$OUTDIR/$MODE.exit"
exit "$status"

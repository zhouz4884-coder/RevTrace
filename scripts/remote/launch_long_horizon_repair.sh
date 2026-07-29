#!/usr/bin/env bash
set -uo pipefail

MODE="${1:?mode required: frozen|quality|continuous|rebase|rebase-confirm}"
ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
REPO="$ROOT/projects/revtrace"
PY="$ROOT/envs/revbatch-cu128/bin/python"
MODEL="$ROOT/models/Qwen3-ASR-0.6B"
MANIFEST="$ROOT/datasets/revtrace/long_horizon_annotated_128.json"
OUTDIR="$REPO/results/long_horizon"
mkdir -p "$OUTDIR"
cd "$REPO"

status=0
case "$MODE" in
  frozen)
    "$PY" scripts/remote/run_frozen_age_concurrency_matrix.py \
      --experiment-id LHR-FROZEN-MATRIX-20260729 \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --output "$OUTDIR/frozen_age_concurrency.json" \
      --trace-concurrency 12 \
      --concurrency 1,4,8,12 \
      --ages 30,60,90,120 \
      --repetitions 5 \
      --gpu 0 || status=$?
    ;;
  quality)
    "$PY" scripts/remote/run_checkpoint_rebase_quality.py \
      --experiment-id LHR-REBASE-QUALITY-20260729 \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --output "$OUTDIR/checkpoint_rebase_quality.json" \
      --duration-seconds 120 \
      --checkpoint-seconds 30 \
      --sessions-per-language 4 \
      --gpu 1 \
      --maximum-primary-error-delta 0.02 \
      --maximum-catastrophic-outliers 0 || status=$?
    ;;
  continuous|rebase|rebase-confirm)
    checkpoint_args=()
    controller_args=()
    stage_args=(
      --continue-same-contract-stages
      --non-gating-stage calibration
      --stage calibration:12:2:mixed
      --stage heldout:12:1:mixed
    )
    output_name="full_selective_continuous"
    experiment_id="LHR-CONTINUOUS-SELECTIVE-20260729"
    if [[ "$MODE" == "rebase" || "$MODE" == "rebase-confirm" ]]; then
      checkpoint_args=(--checkpoint-seconds 30)
      output_name="full_selective_rebase"
      experiment_id="LHR-REBASE-SELECTIVE-20260729"
    fi
    if [[ "$MODE" == "rebase-confirm" ]]; then
      confirm_suffix="${REVTRACE_CONFIRM_SUFFIX:-confirmed}"
      failure_margin="${REVTRACE_FAILURE_MARGIN:-0.015625}"
      confirm_seed="${REVTRACE_EPISODE_SEED_BASE:-20260731}"
      output_name="full_selective_rebase_${confirm_suffix}"
      experiment_id="LHR-REBASE-${confirm_suffix^^}-20260729"
      controller_args=(
        --phase6-asymmetric-memory
        --failure-floor "adaptation:${failure_margin}"
        --episode-seed-base "$confirm_seed"
      )
      stage_args=(
        --continue-same-contract-stages
        --non-gating-stage adaptation
        --stage adaptation:12:2:mixed
        --stage heldout:12:1:mixed
      )
    fi
    REVTRACE_CODE_COMMIT="${REVTRACE_CODE_COMMIT:-WORKTREE_PROTOCOL_REPAIR}" \
      "$PY" scripts/remote/run_phase5a_live_adaptive.py \
      --experiment-id "$experiment_id" \
      --model "$MODEL" \
      --model-name Qwen3-ASR-0.6B \
      --data-manifest "$MANIFEST" \
      --output "$OUTDIR/$output_name.json" \
      --minimum-audits 1350 \
      --episode-seconds 120 \
      --proposer-gpu 0 \
      --verifier-gpu 1 \
      --canonical-batch-size 12 \
      --canonical-dtype float16 \
      --service-mode full-selective \
      --intermediate-authority singleton \
      --audio-construction distinct-sequence \
      --inter-utterance-silence-ms 250 \
      --declared-maximum-prefix-tokens 512 \
      --declared-maximum-input-tokens 4096 \
      --max-model-length 4096 \
      --statistical-risk-gate \
      --suppress-certified-terminal-proposer \
      "${controller_args[@]}" \
      "${stage_args[@]}" \
      "${checkpoint_args[@]}" || status=$?
    ;;
  *)
    echo "unknown mode: $MODE" >&2
    status=64
    ;;
esac
printf '%s\n' "$status" > "$OUTDIR/$MODE.exit"
exit "$status"

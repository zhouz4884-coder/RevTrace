#!/usr/bin/env bash
# Sequential Phase 5A/B/D queue. Gate failures are recorded and do not prevent
# independent later stages from running.
set -u

ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT="${ROOT}/projects/revtrace"
PYTHON="${ROOT}/envs/revbatch-cu128/bin/python"
WAIT_PID="${1:-}"
STATUS_DIR="${ROOT}/results/revtrace/phase5/run_status"
LOG_DIR="${ROOT}/logs/revtrace/phase5"
mkdir -p "${STATUS_DIR}" "${LOG_DIR}/live_adaptive" \
  "${LOG_DIR}/whisper_protection" "${LOG_DIR}/slack_packing"

if [[ -n "${WAIT_PID}" ]]; then
  while kill -0 "${WAIT_PID}" 2>/dev/null; do
    sleep 5
  done
fi

cd "${PROJECT}" || exit 1
export PYTHONPATH="${PROJECT}/src:${PROJECT}/scripts/remote"

run_gate() {
  local label="$1"
  shift
  "$@"
  local status=$?
  printf '%s\n' "${status}" > "${STATUS_DIR}/${label}.status"
  return 0
}

run_gate phase5a_static_oracle \
  "${PYTHON}" scripts/remote/run_phase5a_live_adaptive.py \
    --model "${ROOT}/models/Qwen3-ASR-0.6B" \
    --model-name Qwen3-ASR-0.6B \
    --data-manifest "${ROOT}/datasets/revbatch/manifest.json" \
    --output "${ROOT}/results/revtrace/phase5/live_adaptive/static-oracle-v2.json" \
    --minimum-audits 1350 \
    --episode-seconds 10 \
    --stage c16_initial:16:8 \
    --stage c64_drift:64:5 \
    --stage c16_return:16:8 \
    --frozen-threshold c16_initial:0.0625 \
    --frozen-threshold c64_drift:0.109375 \
    --frozen-threshold c16_return:0.0625 \
    --canonical-dtype float32 \
    --proposer-gpu 0 \
    --verifier-gpu 1 \
    --episode-seed-base 20260801 \
    --suppress-certified-terminal-proposer \
  > "${LOG_DIR}/live_adaptive/static-oracle-v2.log" 2>&1

run_gate phase5b_tiny_protected \
  env CUDA_VISIBLE_DEVICES=0 \
  "${PYTHON}" scripts/remote/run_phase5b_whisper_protected.py \
    --model "${ROOT}/models/whisper-tiny.en" \
    --model-name whisper-tiny.en \
    --manifest "${ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json" \
    --phase4-pairs "${ROOT}/results/revtrace/phase4/whisper_feedback_expanded/whisper-tiny-en.json" \
    --output "${ROOT}/results/revtrace/phase5/whisper_protection/whisper-tiny-en-v2.json" \
    --sessions 100 \
    --protection-mode all-state-entry \
  > "${LOG_DIR}/whisper_protection/whisper-tiny-en-v2.log" 2>&1 &
tiny_pid=$!

run_gate phase5b_base_protected \
  env CUDA_VISIBLE_DEVICES=1 \
  "${PYTHON}" scripts/remote/run_phase5b_whisper_protected.py \
    --model "${ROOT}/models/whisper-base.en" \
    --model-name whisper-base.en \
    --manifest "${ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json" \
    --phase4-pairs "${ROOT}/results/revtrace/phase4/whisper_feedback_expanded/whisper-base-en.json" \
    --output "${ROOT}/results/revtrace/phase5/whisper_protection/whisper-base-en-v2.json" \
    --sessions 100 \
    --protection-mode all-state-entry \
  > "${LOG_DIR}/whisper_protection/whisper-base-en-v2.log" 2>&1 &
base_pid=$!
wait "${tiny_pid}"
wait "${base_pid}"

run_gate phase5b_tiny_feedback_off \
  env CUDA_VISIBLE_DEVICES=0 \
  "${PYTHON}" scripts/remote/run_phase5b_whisper_feedback_off.py \
    --model "${ROOT}/models/whisper-tiny.en" \
    --model-name whisper-tiny.en \
    --manifest "${ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json" \
    --output "${ROOT}/results/revtrace/phase5/whisper_protection/whisper-tiny-en-feedback-off.json" \
    --sessions 100 \
    --batch-size 16 \
  > "${LOG_DIR}/whisper_protection/whisper-tiny-en-feedback-off.log" 2>&1 &
tiny_off_pid=$!

run_gate phase5b_base_feedback_off \
  env CUDA_VISIBLE_DEVICES=1 \
  "${PYTHON}" scripts/remote/run_phase5b_whisper_feedback_off.py \
    --model "${ROOT}/models/whisper-base.en" \
    --model-name whisper-base.en \
    --manifest "${ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json" \
    --output "${ROOT}/results/revtrace/phase5/whisper_protection/whisper-base-en-feedback-off.json" \
    --sessions 100 \
    --batch-size 16 \
  > "${LOG_DIR}/whisper_protection/whisper-base-en-feedback-off.log" 2>&1 &
base_off_pid=$!
wait "${tiny_off_pid}"
wait "${base_off_pid}"

run_gate phase5d_live_slack_packing \
  "${PYTHON}" scripts/remote/run_phase5d_live_slack_packing.py \
    --model "${ROOT}/models/Qwen3-ASR-0.6B" \
    --model-name Qwen3-ASR-0.6B \
    --manifest "${ROOT}/datasets/revbatch/manifest.json" \
    --output "${ROOT}/results/revtrace/phase5/slack_packing/live-c8.json" \
    --gpu 1 \
    --concurrency 8 \
    --rounds 20 \
    --audit-calibration-requests 20 \
  > "${LOG_DIR}/slack_packing/live-c8.log" 2>&1

printf 'complete\n' > "${STATUS_DIR}/remaining.complete"

#!/usr/bin/env bash
# Re-run Phase 5B after correcting two protocol inputs:
# (1) Whisper requires the 16 kHz LibriSpeech manifest, not the Qwen 48 kHz
#     smoke manifest; and
# (2) the Phase 4 paired-world evidence is stored under the data results root.
set -u

ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT="${ROOT}/projects/revtrace"
PYTHON="${ROOT}/envs/revbatch-cu128/bin/python"
STATUS_DIR="${ROOT}/results/revtrace/phase5/run_status"
LOG_DIR="${ROOT}/logs/revtrace/phase5/whisper_protection"
MANIFEST="${ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
PAIR_DIR="${ROOT}/results/revtrace/phase4/whisper_feedback_expanded"
OUT_DIR="${ROOT}/results/revtrace/phase5/whisper_protection"

mkdir -p "${STATUS_DIR}" "${LOG_DIR}" "${OUT_DIR}"
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

run_gate phase5b_tiny_protected \
  env CUDA_VISIBLE_DEVICES=0 \
  "${PYTHON}" scripts/remote/run_phase5b_whisper_protected.py \
    --model "${ROOT}/models/whisper-tiny.en" \
    --model-name whisper-tiny.en \
    --manifest "${MANIFEST}" \
    --phase4-pairs "${PAIR_DIR}/whisper-tiny-en.json" \
    --output "${OUT_DIR}/whisper-tiny-en-v2.json" \
    --sessions 100 \
    --protection-mode all-state-entry \
  > "${LOG_DIR}/whisper-tiny-en-v2.log" 2>&1 &
tiny_pid=$!

run_gate phase5b_base_protected \
  env CUDA_VISIBLE_DEVICES=1 \
  "${PYTHON}" scripts/remote/run_phase5b_whisper_protected.py \
    --model "${ROOT}/models/whisper-base.en" \
    --model-name whisper-base.en \
    --manifest "${MANIFEST}" \
    --phase4-pairs "${PAIR_DIR}/whisper-base-en.json" \
    --output "${OUT_DIR}/whisper-base-en-v2.json" \
    --sessions 100 \
    --protection-mode all-state-entry \
  > "${LOG_DIR}/whisper-base-en-v2.log" 2>&1 &
base_pid=$!
wait "${tiny_pid}"
wait "${base_pid}"

run_gate phase5b_tiny_feedback_off \
  env CUDA_VISIBLE_DEVICES=0 \
  "${PYTHON}" scripts/remote/run_phase5b_whisper_feedback_off.py \
    --model "${ROOT}/models/whisper-tiny.en" \
    --model-name whisper-tiny.en \
    --manifest "${MANIFEST}" \
    --output "${OUT_DIR}/whisper-tiny-en-feedback-off.json" \
    --sessions 100 \
    --batch-size 16 \
  > "${LOG_DIR}/whisper-tiny-en-feedback-off.log" 2>&1 &
tiny_off_pid=$!

run_gate phase5b_base_feedback_off \
  env CUDA_VISIBLE_DEVICES=1 \
  "${PYTHON}" scripts/remote/run_phase5b_whisper_feedback_off.py \
    --model "${ROOT}/models/whisper-base.en" \
    --model-name whisper-base.en \
    --manifest "${MANIFEST}" \
    --output "${OUT_DIR}/whisper-base-en-feedback-off.json" \
    --sessions 100 \
    --batch-size 16 \
  > "${LOG_DIR}/whisper-base-en-feedback-off.log" 2>&1 &
base_off_pid=$!
wait "${tiny_off_pid}"
wait "${base_off_pid}"

printf 'complete\n' > "${STATUS_DIR}/phase5b_repair.complete"

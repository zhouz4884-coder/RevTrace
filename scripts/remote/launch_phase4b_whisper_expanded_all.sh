#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase4/whisper_feedback_expanded"
mkdir -p "${RESULT_ROOT}"

nohup bash "${PROJECT_ROOT}/scripts/remote/run_phase4b_whisper_expanded.sh" \
  0 "${DATA_ROOT}/models/whisper-tiny.en" whisper-tiny.en whisper-tiny-en \
  >"${RESULT_ROOT}/whisper-tiny-en.log" 2>&1 &
echo $! >"${RESULT_ROOT}/whisper-tiny-en.pid"

nohup bash "${PROJECT_ROOT}/scripts/remote/run_phase4b_whisper_expanded.sh" \
  1 "${DATA_ROOT}/models/whisper-base.en" whisper-base.en whisper-base-en \
  >"${RESULT_ROOT}/whisper-base-en.log" 2>&1 &
echo $! >"${RESULT_ROOT}/whisper-base-en.pid"

wait

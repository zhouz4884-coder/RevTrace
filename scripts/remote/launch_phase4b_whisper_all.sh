#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase4/whisper_feedback"

mkdir -p "${RESULT_ROOT}"
cd "${PROJECT_ROOT}"

bash "${PROJECT_ROOT}/scripts/remote/run_phase4b_whisper.sh" \
  0 whisper-tiny.en whisper-tiny-en \
  >"${RESULT_ROOT}/whisper-tiny-en.log" 2>&1 &
PID_TINY=$!

bash "${PROJECT_ROOT}/scripts/remote/run_phase4b_whisper.sh" \
  1 whisper-base.en whisper-base-en \
  >"${RESULT_ROOT}/whisper-base-en.log" 2>&1 &
PID_BASE=$!

echo "${PID_TINY}" >"${RESULT_ROOT}/whisper-tiny-en.pid"
echo "${PID_BASE}" >"${RESULT_ROOT}/whisper-base-en.pid"
wait "${PID_TINY}"
wait "${PID_BASE}"

#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase4/active_mining"
mkdir -p "${RESULT_ROOT}"

nohup bash "${PROJECT_ROOT}/scripts/remote/run_phase4d_active_mining.sh" \
  0 0.6B qwen3-asr-0.6b \
  >"${RESULT_ROOT}/qwen3-asr-0.6b.log" 2>&1 &
echo $! >"${RESULT_ROOT}/qwen3-asr-0.6b.pid"

nohup bash "${PROJECT_ROOT}/scripts/remote/run_phase4d_active_mining.sh" \
  1 1.7B qwen3-asr-1.7b \
  >"${RESULT_ROOT}/qwen3-asr-1.7b.log" 2>&1 &
echo $! >"${RESULT_ROOT}/qwen3-asr-1.7b.pid"

wait

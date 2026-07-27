#!/usr/bin/env bash
set -uo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase3/adaptive"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/phase3"

export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export HF_HOME="${DATA_ROOT}/cache/huggingface"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export REVTRACE_CODE_COMMIT="${REVTRACE_CODE_COMMIT:-UNRECORDED}"

if [[ -n "${WAIT_FOR_PID:-}" ]]; then
  while kill -0 "${WAIT_FOR_PID}" 2>/dev/null; do
    sleep 10
  done
fi

mkdir -p "${RESULT_ROOT}" "${LOG_ROOT}"
"${DATA_ROOT}/envs/revbatch-cu128/bin/python" \
  "${PROJECT_ROOT}/scripts/remote/run_shadow_risk_audit.py" \
  --model "${DATA_ROOT}/models/Qwen3-ASR-0.6B" \
  --model-name "Qwen3-ASR-0.6B" \
  --data-manifest "${DATA_ROOT}/datasets/revbatch/manifest.json" \
  --output "${RESULT_ROOT}/c64-shadow-p0.05-seed20260731.json" \
  --target-risk-entries 30000 \
  --duration-seconds 30 \
  --concurrency 64 \
  --margin-threshold 0.05 \
  --audit-probability 0.05 \
  --alpha 0.05 \
  --delta 0.005 \
  --seed 20260731 \
  --proposer-gpu 0 \
  --verifier-gpu 1 \
  >"${LOG_ROOT}/c64-shadow-p0.05-seed20260731.log" 2>&1

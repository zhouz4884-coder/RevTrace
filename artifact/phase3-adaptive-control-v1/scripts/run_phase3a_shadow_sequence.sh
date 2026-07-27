#!/usr/bin/env bash
set -uo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase3/adaptive"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/phase3"
PYTHON="${DATA_ROOT}/envs/revbatch-cu128/bin/python"
MANIFEST="${DATA_ROOT}/datasets/revbatch/manifest.json"

export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export HF_HOME="${DATA_ROOT}/cache/huggingface"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export REVTRACE_CODE_COMMIT="${REVTRACE_CODE_COMMIT:-WORKTREE_PHASE3A}"

mkdir -p "${RESULT_ROOT}" "${LOG_ROOT}"

if [[ -n "${WAIT_FOR_PID:-}" ]]; then
  while kill -0 "${WAIT_FOR_PID}" 2>/dev/null; do
    sleep 10
  done
fi

run_shadow() {
  local model_name="$1"
  local concurrency="$2"
  local seed="$3"
  local label="$4"
  "${PYTHON}" "${PROJECT_ROOT}/scripts/remote/run_shadow_risk_audit.py" \
    --model "${DATA_ROOT}/models/${model_name}" \
    --model-name "${model_name}" \
    --data-manifest "${MANIFEST}" \
    --output "${RESULT_ROOT}/${label}.json" \
    --target-risk-entries 30000 \
    --duration-seconds 30 \
    --concurrency "${concurrency}" \
    --margin-threshold 0.05 \
    --audit-probability 0.05 \
    --alpha 0.05 \
    --delta 0.005 \
    --seed "${seed}" \
    --proposer-gpu 0 \
    --verifier-gpu 1 \
    >"${LOG_ROOT}/${label}.log" 2>&1
  local status=$?
  printf '{"label":"%s","status":%s}\n' "${label}" "${status}"
  return 0
}

run_shadow "Qwen3-ASR-0.6B" 16 20260732 \
  "c16-initial-shadow-p0.05-seed20260732"
run_shadow "Qwen3-ASR-1.7B" 16 20260733 \
  "1p7b-c16-shadow-p0.05-seed20260733"
run_shadow "Qwen3-ASR-0.6B" 16 20260734 \
  "c16-return-shadow-p0.05-seed20260734"

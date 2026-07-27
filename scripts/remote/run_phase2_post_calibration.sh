#!/usr/bin/env bash
set -uo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase2/risk_v1"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/phase2/risk_v1"

export PATH="${DATA_ROOT}/envs/revbatch-cu128/bin:${PATH}"
export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export HF_HOME="${DATA_ROOT}/cache/huggingface"
export VLLM_WORKER_MULTIPROC_METHOD=spawn

for model_name in Qwen3-ASR-0.6B Qwen3-ASR-1.7B; do
  if [[ -f "${RESULT_ROOT}/natural-shadow-${model_name}.json" ]]; then
    mv \
      "${RESULT_ROOT}/natural-shadow-${model_name}.json" \
      "${RESULT_ROOT}/calibration-c64-${model_name}.json"
  fi
done
for suffix in 0.6b 1.7b; do
  if [[ -f "${LOG_ROOT}/natural-shadow-${suffix}.log" ]]; then
    mv \
      "${LOG_ROOT}/natural-shadow-${suffix}.log" \
      "${LOG_ROOT}/calibration-c64-${suffix}.log"
  fi
done

for model_name in Qwen3-ASR-0.6B Qwen3-ASR-1.7B; do
  safe_suffix="0.6b"
  validation_seed=20260728
  if [[ "${model_name}" == "Qwen3-ASR-1.7B" ]]; then
    safe_suffix="1.7b"
    validation_seed=20260729
  fi
  python "${PROJECT_ROOT}/scripts/remote/run_shadow_risk_audit.py" \
    --model "${DATA_ROOT}/models/${model_name}" \
    --model-name "${model_name}" \
    --data-manifest "${DATA_ROOT}/datasets/revbatch/manifest.json" \
    --output "${RESULT_ROOT}/natural-shadow-${model_name}.json" \
    --target-risk-entries 30000 \
    --concurrency 16 \
    --seed "${validation_seed}" \
    >"${LOG_ROOT}/natural-shadow-${safe_suffix}.log" 2>&1
  status=$?
  printf '{"stage":"c16_audit","model":"%s","status":%s}\n' \
    "${model_name}" "${status}"
  # A statistical gate failure is evidence, not a reason to skip the second
  # model or the independent performance repetitions.
done

"${PROJECT_ROOT}/scripts/remote/run_terminal_replicates.sh"

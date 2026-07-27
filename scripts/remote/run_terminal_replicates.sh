#!/usr/bin/env bash
set -uo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase2/terminal_canonical/replicates"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/phase2/terminal_canonical/replicates"

export PATH="${DATA_ROOT}/envs/revbatch-cu128/bin:${PATH}"
export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export HF_HOME="${DATA_ROOT}/cache/huggingface"
export VLLM_WORKER_MULTIPROC_METHOD=spawn

mkdir -p "${RESULT_ROOT}" "${LOG_ROOT}"

for model_name in Qwen3-ASR-0.6B Qwen3-ASR-1.7B; do
  model_dir="${DATA_ROOT}/models/${model_name}"
  safe_name="${model_name//[^A-Za-z0-9._-]/_}"
  for repeat in 1 2 3 4; do
    output="${RESULT_ROOT}/terminal-canonical-${safe_name}-r${repeat}.json"
    log="${LOG_ROOT}/terminal-canonical-${safe_name}-r${repeat}.log"
    python "${PROJECT_ROOT}/scripts/remote/run_revtrace_dual_gpu.py" \
      --model "${model_dir}" \
      --model-name "${model_name}" \
      --data-manifest "${DATA_ROOT}/datasets/revbatch/manifest.json" \
      --output "${output}" \
      --duration-seconds 30 \
      --concurrency 16 \
      --margin-threshold 0.05 \
      --dtype float16 \
      --proposer-gpu 0 \
      --verifier-gpu 1 \
      --verifier-lanes 1 \
      --verifier-gpu-memory-utilization 0.82 \
      --verifier-max-model-len 4096 \
      --terminal-canonical-dtype float16 \
      --terminal-canonical-batch-size 16 \
      --terminal-canonical-batch-invariant \
      >"${log}" 2>&1
    status=$?
    printf '{"model":"%s","repeat":%s,"status":%s}\n' \
      "${model_name}" "${repeat}" "${status}"
    if [[ ${status} -ne 0 ]]; then
      exit "${status}"
    fi
  done
done

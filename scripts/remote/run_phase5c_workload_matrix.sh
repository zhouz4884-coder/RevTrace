#!/usr/bin/env bash
set -uo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase5/workload_matrix"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/phase5/workload_matrix"
PYTHON="${DATA_ROOT}/envs/revbatch-cu128/bin/python"

export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export HF_HOME="${DATA_ROOT}/caches/huggingface"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export REVTRACE_CODE_COMMIT="${REVTRACE_CODE_COMMIT:-WORKTREE_PHASE5}"

mkdir -p "${RESULT_ROOT}" "${LOG_ROOT}"

run_cell() {
  local gpu0="$1"
  local gpu1="$2"
  local model="$3"
  local concurrency="$4"
  local duration="$5"
  local arrival="$6"
  local language="$7"
  local threshold="$8"
  local label="$9"
  CUDA_VISIBLE_DEVICES="${gpu0},${gpu1}" "${PYTHON}" \
    "${PROJECT_ROOT}/scripts/remote/run_revtrace_dual_gpu.py" \
    --model "${DATA_ROOT}/models/${model}" \
    --model-name "${model}" \
    --data-manifest "${DATA_ROOT}/datasets/revbatch/manifest.json" \
    --output "${RESULT_ROOT}/${label}.json" \
    --duration-seconds "${duration}" \
    --concurrency "${concurrency}" \
    --margin-threshold "${threshold}" \
    --dtype float16 \
    --proposer-gpu 0 \
    --verifier-gpu 1 \
    --verifier-lanes 1 \
    --verifier-gpu-memory-utilization 0.82 \
    --verifier-max-model-len 4096 \
    --terminal-canonical-dtype float16 \
    --terminal-canonical-batch-size 16 \
    --terminal-canonical-batch-invariant \
    --arrival-mode "${arrival}" \
    --arrival-seed 20260728 \
    --arrival-scale-seconds 0.02 \
    --language-mode "${language}" \
    >"${LOG_ROOT}/${label}.log" 2>&1
  local status=$?
  printf '{"label":"%s","status":%s}\n' "${label}" "${status}"
  return 0
}

# Cells are run serially because every deployed cell uses both GPUs.
run_cell 0 1 Qwen3-ASR-0.6B 8 30 sync English 0.05 \
  "0p6b-c8-d30-sync-en"
run_cell 0 1 Qwen3-ASR-0.6B 16 60 poisson mixed 0.05 \
  "0p6b-c16-d60-poisson-mixed"
run_cell 0 1 Qwen3-ASR-0.6B 32 120 burst Chinese 0.05 \
  "0p6b-c32-d120-burst-zh"
run_cell 0 1 Qwen3-ASR-0.6B 16 120 sync mixed 0.05 \
  "0p6b-c16-d120-sync-mixed"

run_cell 0 1 Qwen3-ASR-1.7B 8 60 poisson English 0.10 \
  "1p7b-c8-d60-poisson-en"
run_cell 0 1 Qwen3-ASR-1.7B 16 30 sync mixed 0.10 \
  "1p7b-c16-d30-sync-mixed"
run_cell 0 1 Qwen3-ASR-1.7B 32 60 burst Chinese 0.10 \
  "1p7b-c32-d60-burst-zh"
run_cell 0 1 Qwen3-ASR-1.7B 16 120 poisson mixed 0.10 \
  "1p7b-c16-d120-poisson-mixed"

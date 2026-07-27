#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 MODEL_NAME MODEL_DIR DURATION_SECONDS CONCURRENCY" >&2
  exit 64
fi

MODEL_NAME="$1"
MODEL_DIR="$2"
DURATION_SECONDS="$3"
CONCURRENCY="$4"

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase1/deployed"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/phase1/deployed"
SAFE_MODEL_NAME="${MODEL_NAME//[^A-Za-z0-9._-]/_}"
RUN_TAG="dual-gpu-${SAFE_MODEL_NAME}-fp16-d${DURATION_SECONDS}-c${CONCURRENCY}"

export PATH="${DATA_ROOT}/envs/revbatch-cu128/bin:${PATH}"
export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export HF_HOME="${DATA_ROOT}/caches/huggingface"
export VLLM_CACHE_ROOT="${DATA_ROOT}/caches/vllm"

mkdir -p "${RESULT_ROOT}" "${LOG_ROOT}"

exec python "${PROJECT_ROOT}/scripts/remote/run_revtrace_dual_gpu.py" \
  --model "${MODEL_DIR}" \
  --model-name "${MODEL_NAME}" \
  --data-manifest "${DATA_ROOT}/datasets/revbatch/manifest.json" \
  --output "${RESULT_ROOT}/${RUN_TAG}.json" \
  --duration-seconds "${DURATION_SECONDS}" \
  --concurrency "${CONCURRENCY}" \
  --margin-threshold 0.05 \
  --dtype float16 \
  --proposer-gpu 0 \
  --verifier-gpu 1

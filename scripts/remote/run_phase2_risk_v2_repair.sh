#!/usr/bin/env bash
set -uo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RISK_ROOT="${DATA_ROOT}/results/revtrace/phase2/risk_v2"
RISK_LOG_ROOT="${DATA_ROOT}/logs/revtrace/phase2/risk_v2"
SYSTEM_ROOT="${DATA_ROOT}/results/revtrace/phase2/terminal_canonical_v2"
SYSTEM_LOG_ROOT="${DATA_ROOT}/logs/revtrace/phase2/terminal_canonical_v2"
MODEL_NAME="Qwen3-ASR-1.7B"
MODEL_DIR="${DATA_ROOT}/models/${MODEL_NAME}"

export PATH="${DATA_ROOT}/envs/revbatch-cu128/bin:${PATH}"
export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export HF_HOME="${DATA_ROOT}/cache/huggingface"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export REVTRACE_CODE_COMMIT="eaabdaa017a13786370f3b0e13a1248f94084865"

mkdir -p \
  "${RISK_ROOT}" \
  "${RISK_LOG_ROOT}" \
  "${SYSTEM_ROOT}" \
  "${SYSTEM_LOG_ROOT}"

python "${PROJECT_ROOT}/scripts/remote/run_shadow_risk_audit.py" \
  --model "${MODEL_DIR}" \
  --model-name "${MODEL_NAME}" \
  --data-manifest "${DATA_ROOT}/datasets/revbatch/manifest.json" \
  --output "${RISK_ROOT}/natural-shadow-${MODEL_NAME}-tau0.10.json" \
  --target-risk-entries 30000 \
  --concurrency 16 \
  --margin-threshold 0.10 \
  --seed 20260730 \
  >"${RISK_LOG_ROOT}/natural-shadow-1.7b-tau0.10.log" 2>&1
risk_status=$?
printf '{"stage":"risk_v2","model":"%s","status":%s}\n' \
  "${MODEL_NAME}" "${risk_status}"

system_status=0
mkdir -p "${SYSTEM_ROOT}/replicates" "${SYSTEM_LOG_ROOT}/replicates"
for repeat in 0 1 2 3 4; do
  output="${SYSTEM_ROOT}/terminal-canonical-${MODEL_NAME}-tau0.10-d30-c16.json"
  log="${SYSTEM_LOG_ROOT}/terminal-canonical-1.7b-tau0.10.log"
  if [[ ${repeat} -gt 0 ]]; then
    output="${SYSTEM_ROOT}/replicates/terminal-canonical-${MODEL_NAME}-tau0.10-r${repeat}.json"
    log="${SYSTEM_LOG_ROOT}/replicates/terminal-canonical-1.7b-tau0.10-r${repeat}.log"
  fi
  python "${PROJECT_ROOT}/scripts/remote/run_revtrace_dual_gpu.py" \
    --model "${MODEL_DIR}" \
    --model-name "${MODEL_NAME}" \
    --data-manifest "${DATA_ROOT}/datasets/revbatch/manifest.json" \
    --output "${output}" \
    --duration-seconds 30 \
    --concurrency 16 \
    --margin-threshold 0.10 \
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
  repeat_status=$?
  printf '{"stage":"system_v2","model":"%s","repeat":%s,"status":%s}\n' \
    "${MODEL_NAME}" "${repeat}" "${repeat_status}"
  if [[ ${repeat_status} -ne 0 ]]; then
    system_status=2
  fi
done

if [[ ${risk_status} -ne 0 || ${system_status} -ne 0 ]]; then
  exit 2
fi

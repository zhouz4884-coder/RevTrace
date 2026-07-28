#!/usr/bin/env bash
# Phase 6 submission repairs. Independent gates continue after an evidenced
# failure so the final report can separate safety, capacity, and adaptation.
set -uo pipefail

ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT="${ROOT}/projects/revtrace"
PYTHON="${ROOT}/envs/revbatch-cu128/bin/python"
RESULT="${ROOT}/results/revtrace/phase6"
LOG="${ROOT}/logs/revtrace/phase6"
STATUS="${RESULT}/run_status"

mkdir -p "${RESULT}/contract_scoping" "${RESULT}/live_adaptation" \
  "${LOG}" "${STATUS}"
cd "${PROJECT}" || exit 1
export PYTHONPATH="${PROJECT}/src:${PROJECT}/scripts/remote"
export HF_HOME="${ROOT}/caches/huggingface"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export REVTRACE_CODE_COMMIT="${REVTRACE_CODE_COMMIT:-WORKTREE_PHASE6}"

run_gate() {
  local label="$1"
  shift
  "$@"
  local status=$?
  printf '%s\n' "${status}" > "${STATUS}/${label}.status"
  return 0
}

# P6.2: exact Phase 5 failure cell. The first 64 entries are quarantined,
# and the known 0.109375 counterexample creates a persistent threshold floor.
run_gate p6_2_c32_zh_burst \
  env CUDA_VISIBLE_DEVICES=0,1 \
  "${PYTHON}" scripts/remote/run_revtrace_dual_gpu.py \
    --model "${ROOT}/models/Qwen3-ASR-0.6B" \
    --model-name Qwen3-ASR-0.6B \
    --data-manifest "${ROOT}/datasets/revbatch/manifest.json" \
    --output "${RESULT}/contract_scoping/0p6b-c32-d120-burst-zh.json" \
    --duration-seconds 120 \
    --concurrency 32 \
    --margin-threshold 0.109376 \
    --quarantine-events 64 \
    --contract-digest "qwen0p6-fp16-c32-zh-burst-d120-v1" \
    --contract-epoch 2 \
    --policy-epoch 2 \
    --certificate-source-contract none \
    --dtype float16 \
    --proposer-gpu 0 \
    --verifier-gpu 1 \
    --verifier-lanes 1 \
    --verifier-gpu-memory-utilization 0.82 \
    --verifier-max-model-len 4096 \
    --terminal-canonical-dtype float16 \
    --terminal-canonical-batch-size 16 \
    --terminal-canonical-batch-invariant \
    --arrival-mode burst \
    --arrival-seed 20260728 \
    --arrival-scale-seconds 0.02 \
    --language-mode Chinese \
  >"${LOG}/p6_2_c32_zh_burst.log" 2>&1

# P6.4: both contracts use c16 and stay inside the measured service region.
# The population changes, so the first two stages learn independently. The
# exact return restores only the first contract and first renews 64 canaries.
run_gate p6_4_feasible_live_adaptation \
  env CUDA_VISIBLE_DEVICES=0,1 \
  "${PYTHON}" scripts/remote/run_phase5a_live_adaptive.py \
    --model "${ROOT}/models/Qwen3-ASR-0.6B" \
    --model-name Qwen3-ASR-0.6B \
    --data-manifest "${ROOT}/datasets/revbatch/manifest.json" \
    --output "${RESULT}/live_adaptation/c16-en-c16-zh-c16-en.json" \
    --minimum-audits 1350 \
    --episode-seconds 10 \
    --stage c16_en_initial:16:18:English \
    --stage c16_zh_drift:16:18:Chinese \
    --stage c16_en_return:16:4:English \
    --canonical-dtype float32 \
    --proposer-gpu 0 \
    --verifier-gpu 1 \
    --episode-seed-base 20260820 \
    --suppress-certified-terminal-proposer \
    --phase6-asymmetric-memory \
    --renewal-canaries 64 \
    --statistical-risk-gate \
  >"${LOG}/p6_4_feasible_live_adaptation.log" 2>&1

printf 'complete\n' > "${STATUS}/phase6.complete"

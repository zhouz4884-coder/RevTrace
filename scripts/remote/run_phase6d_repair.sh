#!/usr/bin/env bash
# Rerun only Phase 6D after separating quarantine-learning failures from
# counterexamples that invalidate an already active positive certificate.
set -euo pipefail

ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT="${ROOT}/projects/revtrace"
PYTHON="${ROOT}/envs/revbatch-cu128/bin/python"
RESULT="${ROOT}/results/revtrace/phase6/live_adaptation"
LOG="${ROOT}/logs/revtrace/phase6"
STATUS="${ROOT}/results/revtrace/phase6/run_status"

mkdir -p "${RESULT}" "${LOG}" "${STATUS}"
rm -f \
  "${STATUS}/p6_4_feasible_live_adaptation.status" \
  "${STATUS}/phase6d-repair.complete"
cd "${PROJECT}"
export PYTHONPATH="${PROJECT}/src:${PROJECT}/scripts/remote"
export HF_HOME="${ROOT}/caches/huggingface"
export VLLM_WORKER_MULTIPROC_METHOD=spawn
export REVTRACE_CODE_COMMIT="${REVTRACE_CODE_COMMIT:-WORKTREE_PHASE6_REPAIR}"

if [[ -f "${RESULT}/c16-en-c16-zh-c16-en.json" ]]; then
  if [[ -f "${RESULT}/c16-en-c16-zh-c16-en-first-fail.json" ]]; then
    saved_result="${RESULT}/c16-en-c16-zh-c16-en-second-fail.json"
  else
    saved_result="${RESULT}/c16-en-c16-zh-c16-en-first-fail.json"
  fi
  cp -f "${RESULT}/c16-en-c16-zh-c16-en.json" "${saved_result}"
fi
if [[ -f "${LOG}/p6_4_feasible_live_adaptation.log" ]]; then
  if [[ -f "${LOG}/p6_4_feasible_live_adaptation-first-fail.log" ]]; then
    saved_log="${LOG}/p6_4_feasible_live_adaptation-second-fail.log"
  else
    saved_log="${LOG}/p6_4_feasible_live_adaptation-first-fail.log"
  fi
  cp -f "${LOG}/p6_4_feasible_live_adaptation.log" "${saved_log}"
fi

set +e
env CUDA_VISIBLE_DEVICES=0,1 \
  "${PYTHON}" scripts/remote/run_phase5a_live_adaptive.py \
    --model "${ROOT}/models/Qwen3-ASR-0.6B" \
    --model-name Qwen3-ASR-0.6B \
    --data-manifest "${ROOT}/datasets/revbatch/manifest.json" \
    --output "${RESULT}/c16-en-c16-zh-c16-en.json" \
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
status=$?
set -e

printf '%s\n' "${status}" > "${STATUS}/p6_4_feasible_live_adaptation.status"
printf 'complete\n' > "${STATUS}/phase6d-repair.complete"
exit "${status}"

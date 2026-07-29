#!/usr/bin/env bash
set -euo pipefail

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
cd "$root/projects/revtrace"
mkdir -p results/final_closure/steady_state logs/final_closure

# All three labels intentionally map to the same fingerprint.  The process,
# models, controller and certificate remain alive.  Stage one measures cold
# certification. Stage two is a declared adaptation split: authoritative
# post-stage replay contributes only root counterexamples to the persistent
# dynamic failure floor. Stage three is an independently seeded steady-state
# validation split and is the only post-adaptation result used for F2 claims.
REVTRACE_CODE_COMMIT=${REVTRACE_CODE_COMMIT:-FINAL_CLOSURE_WORKTREE} \
PYTHONPATH=src "$root/envs/revbatch-cu128/bin/python" \
  scripts/remote/run_phase5a_live_adaptive.py \
  --model "$root/models/Qwen3-ASR-0.6B" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$root/datasets/revbatch/manifest.json" \
  --output results/final_closure/steady_state/raw.json \
  --minimum-audits 1350 \
  --episode-seconds 30 \
  --canonical-dtype float16 \
  --canonical-batch-size 14 \
  --phase6-asymmetric-memory \
  --statistical-risk-gate \
  --suppress-certified-terminal-proposer \
  --continue-same-contract-stages \
  --promote-post-stage-audit-failures \
  --audit-adaptation-stage c14_audit_adaptation \
  --stage c14_cold_certification:14:7:English \
  --stage c14_audit_adaptation:14:6:English \
  --stage c14_steady_validation:14:6:English \
  > logs/final_closure/steady-state.log 2>&1

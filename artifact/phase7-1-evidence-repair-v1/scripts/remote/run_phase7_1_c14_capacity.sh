#!/usr/bin/env bash
set -euo pipefail

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
cd "$root/projects/revtrace"
mkdir -p results/phase7_1/c14_capacity logs/phase7_1

REVTRACE_CODE_COMMIT=PHASE7_1_WORKTREE \
PYTHONPATH=src "$root/envs/revbatch-cu128/bin/python" \
  scripts/remote/run_phase5a_live_adaptive.py \
  --model "$root/models/Qwen3-ASR-0.6B" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$root/datasets/revbatch/manifest.json" \
  --output results/phase7_1/c14_capacity/raw.json \
  --minimum-audits 1350 \
  --episode-seconds 30 \
  --canonical-dtype float16 \
  --canonical-batch-size 14 \
  --phase6-asymmetric-memory \
  --statistical-risk-gate \
  --suppress-certified-terminal-proposer \
  --stage c14_capacity:14:7:English \
  > logs/phase7_1/c14_capacity.log 2>&1

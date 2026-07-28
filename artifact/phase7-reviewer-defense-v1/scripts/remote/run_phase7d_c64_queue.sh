#!/usr/bin/env bash
set -euo pipefail

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
cd "$root/projects/revtrace"
mkdir -p results/phase7/c64_queue logs/phase7

PYTHONPATH=src "$root/envs/revbatch-cu128/bin/python" \
  scripts/remote/run_phase5a_live_adaptive.py \
  --model "$root/models/Qwen3-ASR-0.6B" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$root/datasets/revbatch/manifest.json" \
  --output results/phase7/c64_queue/raw-active16-waves-en.json \
  --episode-seconds 30 \
  --canonical-dtype float16 \
  --canonical-batch-size 16 \
  --phase6-asymmetric-memory \
  --statistical-risk-gate \
  --frozen-threshold c64_offered_c16_active_en:0.031251 \
  --suppress-certified-terminal-proposer \
  --stage c64_offered_c16_active_en:16:4:English \
  > logs/phase7/c64_queue_en.log 2>&1

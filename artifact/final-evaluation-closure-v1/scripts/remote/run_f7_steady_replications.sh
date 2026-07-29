#!/usr/bin/env bash
set -euo pipefail

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
project=$root/projects/revtrace
python=$root/envs/revbatch-cu128/bin/python
commit=${REVTRACE_CODE_COMMIT:-F5_F8_WORKTREE}

cd "$project"
mkdir -p results/final_closure/steady_replications logs/final_closure

# This run restores the previously certified c14 threshold and executes three
# independently seeded reporting stages.  It deliberately does not repeat the
# 1,350-event cold-certification phase.  Replay remains an excluded audit draw.
REVTRACE_CODE_COMMIT="$commit" PYTHONPATH=src:scripts/remote "$python" \
  scripts/remote/run_phase5a_live_adaptive.py \
  --model "$root/models/Qwen3-ASR-0.6B" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$root/datasets/revbatch/manifest.json" \
  --output results/final_closure/steady_replications/raw.json \
  --minimum-audits 1350 \
  --episode-seconds 30 \
  --canonical-dtype float16 \
  --canonical-batch-size 14 \
  --episode-seed-base 2026073100 \
  --statistical-risk-gate \
  --suppress-certified-terminal-proposer \
  --continue-same-contract-stages \
  --frozen-threshold steady_seed_1:0.062501 \
  --frozen-threshold steady_seed_2:0.062501 \
  --frozen-threshold steady_seed_3:0.062501 \
  --stage steady_seed_1:14:6:English \
  --stage steady_seed_2:14:6:English \
  --stage steady_seed_3:14:6:English \
  > logs/final_closure/f7-steady-replications.log 2>&1

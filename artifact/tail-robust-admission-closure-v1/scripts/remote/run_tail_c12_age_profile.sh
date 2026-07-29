#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "usage: $0 <frozen-threshold>" >&2
  exit 2
fi

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
project=$root/projects/revtrace
python=$root/envs/revbatch-cu128/bin/python
model=$root/models/Qwen3-ASR-0.6B
manifest=$root/datasets/revbatch/manifest.json
threshold=$1
output=results/tail_robust/c12_age_profile/raw.json
log=logs/tail_robust/c12-age-profile.log

cd "$project"
mkdir -p "$(dirname "$output")" "$(dirname "$log")"
if [[ -s "$output" ]]; then
  echo "age profile resume: keeping $output"
  exit 0
fi

set +e
REVTRACE_CODE_COMMIT="${REVTRACE_CODE_COMMIT:-TAIL_ROBUST_WORKTREE}" \
PYTHONPATH=src:scripts/remote \
  "$python" scripts/remote/run_phase5a_live_adaptive.py \
  --model "$model" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$manifest" \
  --output "$output" \
  --minimum-audits 1350 \
  --episode-seconds 120 \
  --canonical-dtype float16 \
  --canonical-batch-size 12 \
  --episode-seed-base 2026083000 \
  --statistical-risk-gate \
  --suppress-certified-terminal-proposer \
  --frozen-threshold "age_profile:${threshold}" \
  --stage age_profile:12:1:English \
  > "$log" 2>&1
exit_code=$?
set -e

if [[ ! -s "$output" ]]; then
  echo "age profile failed before output (exit=$exit_code)" >&2
  exit "$exit_code"
fi
if [[ "$exit_code" -ne 0 && "$exit_code" -ne 2 ]]; then
  echo "age profile produced output but failed unexpectedly (exit=$exit_code)" >&2
  exit "$exit_code"
fi
echo "c12 120-second age profile complete"

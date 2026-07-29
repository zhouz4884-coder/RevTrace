#!/usr/bin/env bash
set -euo pipefail

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
project=$root/projects/revtrace
python=$root/envs/revbatch-cu128/bin/python
commit=${REVTRACE_CODE_COMMIT:-F5_F8_WORKTREE}

cd "$project"
mkdir -p results/final_closure/quality/raw logs/final_closure

run_cell() {
  local model_name=$1
  local model_path=$2
  local threshold=$3
  local manifest=$4
  local slug=$5
  REVTRACE_CODE_COMMIT="$commit" PYTHONPATH=src \
    "$python" scripts/remote/run_f5_deployed_quality.py \
    --model "$model_path" \
    --model-name "$model_name" \
    --manifest "$manifest" \
    --output "results/final_closure/quality/raw/${slug}-deployed_revtrace_fixed_shape_authority.json" \
    --batch-size 16 \
    --margin-threshold "$threshold" \
    --proposer-gpu 0 \
    --verifier-gpu 1
}

english=$root/datasets/revtrace/final_quality/manifest.json
chinese=$root/datasets/revtrace/final_quality/aishell/manifest.json

filter=${F5_MODEL_FILTER:-all}
if [[ "$filter" == "all" || "$filter" == "0.6b" ]]; then
  run_cell Qwen3-ASR-0.6B "$root/models/Qwen3-ASR-0.6B" 0.05 "$english" 0.6b
  run_cell Qwen3-ASR-0.6B "$root/models/Qwen3-ASR-0.6B" 0.05 "$chinese" 0.6b-zh
fi
if [[ "$filter" == "all" || "$filter" == "1.7b" ]]; then
  run_cell Qwen3-ASR-1.7B "$root/models/Qwen3-ASR-1.7B" 0.10 "$english" 1.7b
  run_cell Qwen3-ASR-1.7B "$root/models/Qwen3-ASR-1.7B" 0.10 "$chinese" 1.7b-zh
fi

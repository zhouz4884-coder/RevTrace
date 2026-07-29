#!/usr/bin/env bash
set -euo pipefail

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
project=$root/projects/revtrace
python=$root/envs/revbatch-cu128/bin/python
manifest=${QUALITY_MANIFEST:-$root/datasets/revtrace/final_quality/manifest.json}
suffix=${QUALITY_SUFFIX:-}
commit=${REVTRACE_CODE_COMMIT:-FINAL_CLOSURE_WORKTREE}

cd "$project"
mkdir -p results/final_closure/quality/raw logs/final_closure

run_model() {
  local gpu=$1
  local model_name=$2
  local model_path=$3
  local threshold=$4
  local slug=$5
  local log=logs/final_closure/quality-${slug}.log
  : > "$log"
  for mode in \
    singleton_authoritative \
    unprotected_batch \
    revtrace_risk_limited \
    fp32_reproducible
  do
    echo "[$(date -Is)] ${model_name} ${mode}" >> "$log"
    REVTRACE_CODE_COMMIT="$commit" PYTHONPATH=src \
      "$python" scripts/remote/run_final_quality_mode.py \
      --model "$model_path" \
      --model-name "$model_name" \
      --manifest "$manifest" \
      --output "results/final_closure/quality/raw/${slug}${suffix}-${mode}.json" \
      --mode "$mode" \
      --batch-size 16 \
      --margin-threshold "$threshold" \
      --gpu "$gpu" >> "$log" 2>&1
  done
}

run_model 0 Qwen3-ASR-0.6B "$root/models/Qwen3-ASR-0.6B" 0.05 0.6b &
pid0=$!
run_model 1 Qwen3-ASR-1.7B "$root/models/Qwen3-ASR-1.7B" 0.10 1.7b &
pid1=$!

status=0
wait "$pid0" || status=1
wait "$pid1" || status=1
exit "$status"

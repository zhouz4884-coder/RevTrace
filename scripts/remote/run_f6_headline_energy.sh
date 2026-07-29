#!/usr/bin/env bash
set -euo pipefail

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
project=$root/projects/revtrace
python=$root/envs/revbatch-cu128/bin/python
commit=${REVTRACE_CODE_COMMIT:-F5_F8_WORKTREE}

cd "$project"
mkdir -p results/final_closure/energy/raw logs/final_closure

run_model() {
  local model_name=$1
  local model_path=$2
  local slug=$3
  local threshold=$4
  local rep
  for rep in 1 2 3; do
    local output="results/final_closure/energy/raw/${slug}-rep${rep}.json"
    local exit_code=0
    if [[ -s "$output" ]]; then
      echo "F6 resume: keeping completed $output"
      continue
    fi
    # A completed measurement may legitimately return 2 when the older
    # mechanism gate (for example, >=4x wall speedup) does not pass.  F6 must
    # retain that negative result and continue all preregistered repetitions.
    set +e
    REVTRACE_CODE_COMMIT="$commit" PYTHONPATH=src:scripts/remote \
      "$python" scripts/remote/run_revtrace_dual_gpu.py \
      --model "$model_path" \
      --model-name "$model_name" \
      --data-manifest "$root/datasets/revbatch/manifest.json" \
      --output "$output" \
      --duration-seconds 30 \
      --concurrency 16 \
      --margin-threshold "$threshold" \
      --dtype float16 \
      --proposer-gpu 0 \
      --verifier-gpu 1 \
      --verifier-lanes 1 \
      --verifier-gpu-memory-utilization 0.82 \
      --verifier-max-model-len 4096 \
      --terminal-canonical-dtype float16 \
      --terminal-canonical-batch-size 16 \
      --terminal-canonical-batch-invariant \
      --arrival-mode sync \
      --arrival-seed "$((2026072900 + rep))" \
      > "logs/final_closure/f6-${slug}-rep${rep}.log" 2>&1
    exit_code=$?
    set -e
    if [[ ! -s "$output" ]]; then
      echo "F6 run failed before producing $output (exit=$exit_code)" >&2
      exit "$exit_code"
    fi
    if [[ "$exit_code" -ne 0 && "$exit_code" -ne 2 ]]; then
      echo "F6 run produced output but failed unexpectedly (exit=$exit_code)" >&2
      exit "$exit_code"
    fi
  done
}

run_model Qwen3-ASR-0.6B "$root/models/Qwen3-ASR-0.6B" 0.6b 0.05
run_model Qwen3-ASR-1.7B "$root/models/Qwen3-ASR-1.7B" 1.7b 0.10

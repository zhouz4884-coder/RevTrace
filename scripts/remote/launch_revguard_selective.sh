#!/usr/bin/env bash
set -euo pipefail

DISK_ROOT=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
PROJECT_ROOT="$DISK_ROOT/projects/revtrace"
ENV_PREFIX="$DISK_ROOT/envs/revbatch-cu128"
MODEL_ROOT="$DISK_ROOT/models"
DATA_ROOT="$DISK_ROOT/datasets/revbatch"
RESULT_ROOT="$DISK_ROOT/results/revtrace/phase0/revguard"
LOG_ROOT="$DISK_ROOT/logs/revtrace/phase0/revguard"
RUNNER="$PROJECT_ROOT/scripts/remote/run_revguard_selective.py"

export TMPDIR="$DISK_ROOT/tmp/revbatch"
export HF_HOME="$DISK_ROOT/cache/revbatch/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TRANSFORMERS_CACHE="$HF_HOME/transformers"
export TORCH_HOME="$DISK_ROOT/cache/revbatch/torch"
export TRITON_CACHE_DIR="$DISK_ROOT/cache/revbatch/triton"
export XDG_CACHE_HOME="$DISK_ROOT/cache/revbatch/xdg"

duration="${1:-30}"
concurrency="${2:-16}"
threshold="${3:-1.0}"
study_tag="${4:-n1}"
dtype="${5:-bfloat16}"
tag="selective-${study_tag}-${dtype}-d${duration}-c${concurrency}-m${threshold}"
mkdir -p "$RESULT_ROOT" "$LOG_ROOT"

CUDA_VISIBLE_DEVICES=0 nohup "$ENV_PREFIX/bin/python" "$RUNNER" \
  --model "$MODEL_ROOT/Qwen3-ASR-0.6B" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$DATA_ROOT/manifest.json" \
  --duration-seconds "$duration" \
  --concurrency "$concurrency" \
  --margin-threshold "$threshold" \
  --dtype "$dtype" \
  --output "$RESULT_ROOT/${tag}-qwen3-asr-0.6b.json" \
  >"$LOG_ROOT/${tag}-gpu0.log" 2>&1 </dev/null &
pid0=$!

CUDA_VISIBLE_DEVICES=1 nohup "$ENV_PREFIX/bin/python" "$RUNNER" \
  --model "$MODEL_ROOT/Qwen3-ASR-1.7B" \
  --model-name Qwen3-ASR-1.7B \
  --data-manifest "$DATA_ROOT/manifest.json" \
  --duration-seconds "$duration" \
  --concurrency "$concurrency" \
  --margin-threshold "$threshold" \
  --dtype "$dtype" \
  --output "$RESULT_ROOT/${tag}-qwen3-asr-1.7b.json" \
  >"$LOG_ROOT/${tag}-gpu1.log" 2>&1 </dev/null &
pid1=$!

echo "$pid0" >"$LOG_ROOT/${tag}-gpu0.pid"
echo "$pid1" >"$LOG_ROOT/${tag}-gpu1.pid"
echo "gpu0_pid=$pid0"
echo "gpu1_pid=$pid1"
echo "tag=$tag"

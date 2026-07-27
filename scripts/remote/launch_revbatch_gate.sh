#!/usr/bin/env bash
set -euo pipefail

DISK_ROOT=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
PROJECT_ROOT="$DISK_ROOT/projects/revtrace"
ENV_PREFIX="$DISK_ROOT/envs/revbatch-cu128"
MODEL_ROOT="$DISK_ROOT/models"
DATA_ROOT="$DISK_ROOT/datasets/revbatch"
RESULT_ROOT="$DISK_ROOT/results/revtrace/phase0/revbatch"
LOG_ROOT="$DISK_ROOT/logs/revtrace/phase0/revbatch"
RUNNER="$PROJECT_ROOT/scripts/remote/run_revbatch_gate.py"

export TMPDIR="$DISK_ROOT/tmp/revbatch"
export HF_HOME="$DISK_ROOT/cache/revbatch/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TRANSFORMERS_CACHE="$HF_HOME/transformers"
export TORCH_HOME="$DISK_ROOT/cache/revbatch/torch"
export TRITON_CACHE_DIR="$DISK_ROOT/cache/revbatch/triton"
export XDG_CACHE_HOME="$DISK_ROOT/cache/revbatch/xdg"

mkdir -p "$RESULT_ROOT" "$LOG_ROOT"
"$ENV_PREFIX/bin/python" "$PROJECT_ROOT/scripts/remote/prepare_revbatch_data.py" \
  --root "$DATA_ROOT"

mode="${1:-formal}"
extra=()
suffix=formal
if [[ "$mode" == "smoke" ]]; then
  extra=(--smoke)
  suffix=smoke
elif [[ "$mode" != "formal" ]]; then
  echo "usage: $0 [smoke|formal]" >&2
  exit 2
fi

for gpu in 0 1; do
  if [[ -f "$LOG_ROOT/${suffix}-gpu${gpu}.pid" ]]; then
    old_pid=$(cat "$LOG_ROOT/${suffix}-gpu${gpu}.pid")
    if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
      echo "runner already active on gpu $gpu: $old_pid" >&2
      exit 2
    fi
  fi
done

CUDA_VISIBLE_DEVICES=0 nohup "$ENV_PREFIX/bin/python" "$RUNNER" \
  --model "$MODEL_ROOT/Qwen3-ASR-0.6B" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$DATA_ROOT/manifest.json" \
  --output "$RESULT_ROOT/${suffix}-qwen3-asr-0.6b.json" \
  "${extra[@]}" \
  >"$LOG_ROOT/${suffix}-gpu0.log" 2>&1 </dev/null &
pid0=$!
echo "$pid0" >"$LOG_ROOT/${suffix}-gpu0.pid"

CUDA_VISIBLE_DEVICES=1 nohup "$ENV_PREFIX/bin/python" "$RUNNER" \
  --model "$MODEL_ROOT/Qwen3-ASR-1.7B" \
  --model-name Qwen3-ASR-1.7B \
  --data-manifest "$DATA_ROOT/manifest.json" \
  --output "$RESULT_ROOT/${suffix}-qwen3-asr-1.7b.json" \
  "${extra[@]}" \
  >"$LOG_ROOT/${suffix}-gpu1.log" 2>&1 </dev/null &
pid1=$!
echo "$pid1" >"$LOG_ROOT/${suffix}-gpu1.pid"

echo "gpu0_pid=$pid0"
echo "gpu1_pid=$pid1"
echo "log_root=$LOG_ROOT"

#!/usr/bin/env bash
set -euo pipefail

DISK_ROOT=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
ENV_PREFIX="$DISK_ROOT/envs/revbatch-cu128"
SOURCE_ROOT="$DISK_ROOT/sources/Qwen3-ASR"
MODEL_ROOT="$DISK_ROOT/models"
DATA_ROOT="$DISK_ROOT/datasets/revbatch"
CACHE_ROOT="$DISK_ROOT/cache/revbatch"
TMP_ROOT="$DISK_ROOT/tmp/revbatch"
LOG_ROOT="$DISK_ROOT/logs/streamtxn/revbatch"
RESULT_ROOT="$DISK_ROOT/results/streamtxn/revbatch"
QWEN_COMMIT=7c6daf77a2421100f5fb066495372c00129d39ff

export TMPDIR="$TMP_ROOT"
export HF_HOME="$CACHE_ROOT/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TRANSFORMERS_CACHE="$HF_HOME/transformers"
export TORCH_HOME="$CACHE_ROOT/torch"
export TRITON_CACHE_DIR="$CACHE_ROOT/triton"
export XDG_CACHE_HOME="$CACHE_ROOT/xdg"
export CONDA_PKGS_DIRS="$DISK_ROOT/conda-pkgs/revbatch"
export MODELSCOPE_CACHE="$CACHE_ROOT/modelscope"
export PIP_CACHE_DIR="$CACHE_ROOT/pip"

mkdir -p \
  "$TMP_ROOT" "$HF_HOME" "$HF_DATASETS_CACHE" "$TORCH_HOME" \
  "$TRITON_CACHE_DIR" "$XDG_CACHE_HOME" "$CONDA_PKGS_DIRS" \
  "$MODELSCOPE_CACHE" "$PIP_CACHE_DIR" "$MODEL_ROOT" "$DATA_ROOT" \
  "$LOG_ROOT" "$RESULT_ROOT" "$(dirname "$SOURCE_ROOT")"

source "$HOME/miniconda3/etc/profile.d/conda.sh"
if [[ ! -x "$ENV_PREFIX/bin/python" ]]; then
  conda create -p "$ENV_PREFIX" python=3.12 -y
fi

if [[ ! -d "$SOURCE_ROOT/.git" ]]; then
  git clone https://github.com/QwenLM/Qwen3-ASR.git "$SOURCE_ROOT"
fi
git -C "$SOURCE_ROOT" fetch --depth 1 origin "$QWEN_COMMIT"
git -C "$SOURCE_ROOT" checkout --detach "$QWEN_COMMIT"

"$ENV_PREFIX/bin/python" -m pip install --upgrade pip setuptools wheel
"$ENV_PREFIX/bin/python" -m pip install -e "$SOURCE_ROOT[vllm]"
"$ENV_PREFIX/bin/python" -m pip install modelscope datasets pytest

for model in Qwen3-ASR-0.6B Qwen3-ASR-1.7B; do
  model_dir="$MODEL_ROOT/$model"
  complete=false
  if [[ -f "$model_dir/model.safetensors" ]]; then
    complete=true
  elif [[ -f "$model_dir/model.safetensors.index.json" ]]; then
    if compgen -G "$model_dir/model-*-of-*.safetensors" >/dev/null; then
      complete=true
    fi
  fi
  has_partial=false
  if compgen -G "$model_dir/*.incomplete" >/dev/null; then
    has_partial=true
  fi
  if [[ "$complete" != true || "$has_partial" == true ]]; then
    "$ENV_PREFIX/bin/modelscope" download \
      --model "Qwen/$model" \
      --local_dir "$model_dir"
  fi
done

"$ENV_PREFIX/bin/python" - <<'PY'
import json
from pathlib import Path

import torch
import transformers
import vllm
from qwen_asr import Qwen3ASRModel

root = Path("/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9")
payload = {
    "torch": torch.__version__,
    "torch_cuda": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
    "vllm": vllm.__version__,
    "transformers": transformers.__version__,
    "qwen_asr_import": Qwen3ASRModel.__name__,
}
(root / "results/streamtxn/revbatch/environment.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(payload, sort_keys=True))
PY

git -C "$SOURCE_ROOT" rev-parse HEAD >"$RESULT_ROOT/qwen3_asr_commit.txt"
"$ENV_PREFIX/bin/python" -m pip freeze >"$RESULT_ROOT/requirements-lock.txt"
echo "REV_BATCH_SETUP_COMPLETE"

#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
ENV_ROOT="${DATA_ROOT}/envs/revbatch-cu128"
MODEL_ROOT="${DATA_ROOT}/models/Voxtral-Mini-4B-Realtime-2602"

export HF_ENDPOINT="https://hf-mirror.com"
export HF_HOME="${DATA_ROOT}/cache/huggingface"

mkdir -p "${MODEL_ROOT}"
"${ENV_ROOT}/bin/huggingface-cli" download \
  mistralai/Voxtral-Mini-4B-Realtime-2602 \
  model.safetensors \
  config.json \
  generation_config.json \
  processor_config.json \
  tekken.json \
  params.json \
  README.md \
  --local-dir "${MODEL_ROOT}"

test -s "${MODEL_ROOT}/model.safetensors"
sha256sum "${MODEL_ROOT}/model.safetensors" \
  >"${MODEL_ROOT}/model.safetensors.sha256"

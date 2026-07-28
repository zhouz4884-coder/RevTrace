#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <gpu-index> <smoke|full>" >&2
  exit 2
fi

GPU_INDEX="$1"
MODE="$2"
DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
PYTHON="${DATA_ROOT}/envs/revtrace-voxtral-clean/bin/python"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase3/second_architecture"

mkdir -p "${RESULT_ROOT}"
export CUDA_VISIBLE_DEVICES="${GPU_INDEX}"
export HF_HOME="${DATA_ROOT}/cache/huggingface"
export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PROJECT_ROOT}"

if [[ "${MODE}" == "smoke" ]]; then
  DURATION=4
  BATCH_SIZES=(2)
  REPEATS=1
  OUTPUT="${RESULT_ROOT}/voxtral-smoke.json"
elif [[ "${MODE}" == "full" ]]; then
  DURATION=20
  BATCH_SIZES=(2 4)
  REPEATS=2
  OUTPUT="${RESULT_ROOT}/voxtral.json"
else
  echo "unsupported mode: ${MODE}" >&2
  exit 2
fi

exec "${PYTHON}" \
  "${PROJECT_ROOT}/scripts/remote/run_voxtral_boundary.py" \
  --model "${DATA_ROOT}/models/Voxtral-Mini-4B-Realtime-2602" \
  --audio "${DATA_ROOT}/datasets/revbatch/qwen_public/asr_en.wav" \
  --output "${OUTPUT}" \
  --chunk-seconds 2 \
  --duration-seconds "${DURATION}" \
  --tile-to-duration \
  --batch-sizes "${BATCH_SIZES[@]}" \
  --repeats "${REPEATS}" \
  --max-new-tokens 64

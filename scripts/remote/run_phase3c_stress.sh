#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <gpu-index> <model-size> <output-stem>" >&2
  exit 2
fi

GPU_INDEX="$1"
MODEL_SIZE="$2"
OUTPUT_STEM="$3"
DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase3/rir_population"
LOG_ROOT="${RESULT_ROOT}/phase3c"
PYTHON="${DATA_ROOT}/envs/revbatch-cu128/bin/python"

mkdir -p "${RESULT_ROOT}" "${LOG_ROOT}"
export CUDA_VISIBLE_DEVICES="${GPU_INDEX}"
export HF_HOME="${DATA_ROOT}/cache/huggingface"
export TRANSFORMERS_CACHE="${DATA_ROOT}/cache/huggingface"
export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PROJECT_ROOT}"

exec "${PYTHON}" \
  "${PROJECT_ROOT}/scripts/remote/run_revision_impulse_population.py" \
  --model "${DATA_ROOT}/models/Qwen3-ASR-${MODEL_SIZE}" \
  --model-name "Qwen3-ASR-${MODEL_SIZE}-stress" \
  --data-manifest "${DATA_ROOT}/datasets/revbatch/manifest.json" \
  --output "${RESULT_ROOT}/${OUTPUT_STEM}.json" \
  --duration-seconds 30 \
  --concurrency 64 \
  --batch-size 16 \
  --repeats 8 \
  --target-pairs 50 \
  --search-margin 0.5 \
  --dtype float16 \
  --natural-flip-rate 0.004166666666666667 \
  --audio-stress \
  --stress-seed 20260730

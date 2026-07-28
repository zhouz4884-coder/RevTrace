#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 <gpu-index> <model-dir> <model-name> <output-stem>" >&2
  exit 2
fi

GPU_INDEX="$1"
MODEL_DIR="$2"
MODEL_NAME="$3"
OUTPUT_STEM="$4"
DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase4/whisper_feedback_expanded"
PYTHON="${DATA_ROOT}/envs/revbatch-cu128/bin/python"

mkdir -p "${RESULT_ROOT}"
export CUDA_VISIBLE_DEVICES="${GPU_INDEX}"
export HF_HOME="${DATA_ROOT}/cache/huggingface"
export PYTHONPATH="${PROJECT_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PROJECT_ROOT}"

exec "${PYTHON}" \
  "${PROJECT_ROOT}/scripts/remote/run_whisper_feedback_gate.py" \
  --model "${MODEL_DIR}" \
  --model-name "${MODEL_NAME}" \
  --manifest \
  "${DATA_ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json" \
  --output "${RESULT_ROOT}/${OUTPUT_STEM}.json" \
  --batch-sizes 8 16 \
  --max-candidates 100 \
  --target-pairs 20 \
  --future-windows 2 \
  --max-new-tokens 96

#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT_ROOT="${REVTRACE_PROJECT_ROOT:-${DATA_ROOT}/projects/revtrace_r7_0849660}"
PYTHON_BIN="${REVTRACE_PYTHON:-${DATA_ROOT}/envs/streamtxn-cu128/bin/python}"
OUTPUT_ROOT="${DATA_ROOT}/results/revtrace/r7_efsc/whisper_base_quality"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/r7_efsc/whisper_base_quality"

mkdir -p "${OUTPUT_ROOT}" "${LOG_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export REVTRACE_CODE_COMMIT="$(tr -d '\r\n' < "${PROJECT_ROOT}/CODE_COMMIT")"

"${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/remote/run_r7_whisper_quality.py" \
  --model "${DATA_ROOT}/models/whisper-base.en" \
  --model-name whisper-base.en \
  --manifest "${DATA_ROOT}/datasets/revtrace/librispeech/whisper-w-quality.json" \
  --policy "${DATA_ROOT}/results/revtrace/r7_efsc/whisper_base_preflight/frozen_policy.json" \
  --output "${OUTPUT_ROOT}/paired-128.json" \
  --sessions-per-split 64 --duration-seconds 90 --window-seconds 10 \
  --concurrency 16 --max-new-tokens 96 \
  --seed 2026080701 --bootstrap-seed 2026080702 \
  --bootstrap-replicates 10000 --device cuda:0 \
  >"${LOG_ROOT}/paired-128.log" 2>&1

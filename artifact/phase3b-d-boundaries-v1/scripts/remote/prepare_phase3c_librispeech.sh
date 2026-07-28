#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
DATASET_ROOT="${DATA_ROOT}/datasets/revtrace/librispeech"
ARCHIVE="${DATASET_ROOT}/test-clean.tar.gz"
EXTRACTED="${DATASET_ROOT}/LibriSpeech/test-clean"
MANIFEST="${DATASET_ROOT}/phase3c-test-clean-64.json"
URL="https://hf-mirror.com/datasets/k2-fsa/LibriSpeech/resolve/main/test-clean.tar.gz"

mkdir -p "${DATASET_ROOT}"
if [[ ! -f "${ARCHIVE}" ]]; then
  wget -O "${ARCHIVE}.partial" "${URL}"
  mv "${ARCHIVE}.partial" "${ARCHIVE}"
fi
if [[ ! -d "${EXTRACTED}" ]]; then
  tar -xzf "${ARCHIVE}" -C "${DATASET_ROOT}"
fi

"${DATA_ROOT}/envs/revbatch-cu128/bin/python" \
  "${PROJECT_ROOT}/scripts/remote/build_phase3c_audio_manifest.py" \
  --audio-root "${EXTRACTED}" \
  --output "${MANIFEST}" \
  --limit 64

#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
BASE_ENV="${DATA_ROOT}/envs/revbatch-cu128"
TARGET_ENV="${DATA_ROOT}/envs/sglang-phase7"
SOURCE_WITH_SPACE="${DATA_ROOT}/sources/revtrace-phase7/sglang-main (1)/sglang-main"
SOURCE_LINK="${DATA_ROOT}/sources/revtrace-phase7/sglang-current"
OUTPUT="${DATA_ROOT}/projects/revtrace/results/phase7/source_probes"

ln -sfn "${SOURCE_WITH_SPACE}" "${SOURCE_LINK}"
if [[ ! -x "${TARGET_ENV}/bin/python" ]]; then
  "${BASE_ENV}/bin/python" -m venv --system-site-packages "${TARGET_ENV}"
fi
"${TARGET_ENV}/bin/pip" install -q IPython "sglang-kernel==0.4.5"
SGLANG_BUILD_RUST_EXTS=none "${TARGET_ENV}/bin/pip" install -q \
  --no-deps -e "${SOURCE_LINK}/python"
"${TARGET_ENV}/bin/python" \
  "${DATA_ROOT}/projects/revtrace/scripts/remote/run_phase7_import_probe.py" \
  --source "${SOURCE_LINK}/python" \
  --target sglang-asr \
  --output "${OUTPUT}/sglang-source-qwen-asr-import-retry.json"

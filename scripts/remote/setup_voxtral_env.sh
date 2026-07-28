#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
BASE_ENV="${DATA_ROOT}/envs/revbatch-cu128"
ENV_ROOT="${DATA_ROOT}/envs/revtrace-voxtral-clean"
export PIP_CACHE_DIR="${DATA_ROOT}/cache/pip"

if [[ ! -x "${ENV_ROOT}/bin/python" ]]; then
  "${BASE_ENV}/bin/python" -m venv "${ENV_ROOT}"
fi

"${ENV_ROOT}/bin/python" -m pip install --upgrade pip
"${ENV_ROOT}/bin/python" -m pip install \
  "torch==2.9.1" \
  --index-url "https://download.pytorch.org/whl/cu128"
"${ENV_ROOT}/bin/python" -m pip install --upgrade \
  "transformers>=5.2.0" \
  "accelerate>=1.10.0" \
  "mistral-common[audio]>=1.9.0" \
  soxr \
  librosa \
  soundfile

"${ENV_ROOT}/bin/python" -c \
  'import torch, transformers, mistral_common, soundfile; print(torch.__version__, transformers.__version__, mistral_common.__version__)'

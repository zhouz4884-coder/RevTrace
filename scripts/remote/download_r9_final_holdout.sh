#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
DATA="$ROOT/datasets/revtrace/librispeech_r9_final"
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
mkdir -p "$DATA"
cd "$DATA"
wget -c https://www.openslr.org/resources/12/dev-clean.tar.gz \
  -O dev-clean.tar.gz & clean_pid=$!
wget -c https://www.openslr.org/resources/12/dev-other.tar.gz \
  -O dev-other.tar.gz & other_pid=$!
wait "$clean_pid"
wait "$other_pid"
tar -xzf dev-clean.tar.gz
tar -xzf dev-other.tar.gz
"$PY" "$PROJ/scripts/remote/build_librispeech_tree_manifest.py" \
  --clean-root "$DATA/LibriSpeech/dev-clean" \
  --other-root "$DATA/LibriSpeech/dev-other" \
  --output "$DATA/r9-final-dev-clean-other.json"

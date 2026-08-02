#!/usr/bin/env bash
set -euo pipefail
ROOT=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/datasets/revtrace/librispeech_dev
mkdir -p "$ROOT"
cd "$ROOT"
wget -c -q https://www.openslr.org/resources/12/dev-clean.tar.gz
wget -c -q https://www.openslr.org/resources/12/dev-other.tar.gz
tar -xzf dev-clean.tar.gz
tar -xzf dev-other.tar.gz
touch READY

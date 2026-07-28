#!/usr/bin/env bash
set -u

DATA_ROOT="/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
RESULT_ROOT="${DATA_ROOT}/results/revtrace/phase3"

ps -eo pid,etimes,pcpu,pmem,args |
  grep -E 'run_revision_impulse_population|setup_voxtral_env|pip install' |
  grep -v grep || true

echo "=== QWEN-0.6B ==="
tail -n 12 "${RESULT_ROOT}/rir_population/phase3c/qwen3-asr-0.6b-c64.log" 2>/dev/null || true

echo "=== QWEN-1.7B ==="
tail -n 12 "${RESULT_ROOT}/rir_population/phase3c/qwen3-asr-1.7b-c64.log" 2>/dev/null || true

echo "=== VOXTRAL-SETUP ==="
tail -n 16 "${RESULT_ROOT}/second_architecture/setup-clean.log" 2>/dev/null || true

echo "=== OUTPUTS ==="
find "${RESULT_ROOT}" -maxdepth 3 -type f \
  \( -name 'qwen3-asr-*-c64.json' -o -name 'voxtral*.json' \) \
  -printf '%p %s bytes\n' 2>/dev/null || true

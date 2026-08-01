#!/usr/bin/env bash
# Run independent same-input/feedback-causality probes for both Whisper scales.
set -u

if [[ "$#" -ne 5 ]]; then
  echo "usage: $0 ROOT BASE_MODEL SMALL_MODEL MANIFEST OUT" >&2
  exit 2
fi

ROOT="$1"
BASE_MODEL="$2"
SMALL_MODEL="$3"
MANIFEST="$4"
OUT="$5"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_mechanism.py"

while [[ ! -f "$OUT/.risk-audits-complete" ]]; do
  sleep 20
done
cd "$PROJ"
export PYTHONPATH="$PROJ/src"

base_pid=""
small_pid=""
base_rc=0
small_rc=0

if [[ -s "$OUT/w3-mechanism-base.json" ]]; then
  echo "W3 base already complete; preserving frozen result"
else
  "$PY" "$RUNNER" \
    --model "$BASE_MODEL" \
    --model-name whisper-base.en \
    --manifest "$MANIFEST" \
    --output "$OUT/w3-mechanism-base.json" \
    --sessions 100 \
    --duration-seconds 90 \
    --window-seconds 10 \
    --concurrency 16 \
    --future-windows 2 \
    --max-new-tokens 96 \
    --seed 20260951 \
    --device cuda:0 >"$OUT/w3-mechanism-base.log" 2>&1 &
  base_pid="$!"
fi

if [[ -s "$OUT/w3-mechanism-small.json" ]]; then
  echo "W3 small already complete; preserving frozen result"
else
  "$PY" "$RUNNER" \
    --model "$SMALL_MODEL" \
    --model-name whisper-small.en \
    --manifest "$MANIFEST" \
    --output "$OUT/w3-mechanism-small.json" \
    --sessions 100 \
    --duration-seconds 90 \
    --window-seconds 10 \
    --concurrency 16 \
    --future-windows 2 \
    --max-new-tokens 80 \
    --seed 20260952 \
    --device cuda:1 >"$OUT/w3-mechanism-small.log" 2>&1 &
  small_pid="$!"
fi

if [[ -n "$base_pid" ]]; then
  wait "$base_pid"
  base_rc="$?"
fi
if [[ -n "$small_pid" ]]; then
  wait "$small_pid"
  small_rc="$?"
fi
echo "W3 rc base=$base_rc small=$small_rc"
if [[ "$base_rc" -ne 0 || "$small_rc" -ne 0 ]]; then
  touch "$OUT/.w3-mechanism-failed"
  exit 2
fi
touch "$OUT/.w3-mechanism-complete"

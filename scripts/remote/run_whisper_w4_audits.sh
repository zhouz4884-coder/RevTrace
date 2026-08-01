#!/usr/bin/env bash
# Independent, fail-fast adaptation followed by full W4 risk certification.
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
CONTRACT="$PROJ/scripts/remote/run_whisper_w4_contract.sh"

export PYTHONPATH="$PROJ/src"
while [[ ! -f "$OUT/.small-policies-complete" ]]; do
  sleep 15
done
cd "$PROJ"

(
  bash "$CONTRACT" "$ROOT" whisper-base.en "$BASE_MODEL" base \
    "$MANIFEST" "$OUT" 16 0 20260733 1 \
    && bash "$CONTRACT" "$ROOT" whisper-small.en "$SMALL_MODEL" small \
      "$MANIFEST" "$OUT" 16 0 20260933 1
) >"$OUT/.risk-lane-c16.log" 2>&1 &
c16_pid="$!"

(
  bash "$CONTRACT" "$ROOT" whisper-base.en "$BASE_MODEL" base \
    "$MANIFEST" "$OUT" 8 1 20260734 1 \
    && bash "$CONTRACT" "$ROOT" whisper-small.en "$SMALL_MODEL" small \
      "$MANIFEST" "$OUT" 8 1 20260934 1
) >"$OUT/.risk-lane-c8.log" 2>&1 &
c8_pid="$!"

wait "$c16_pid"
c16_rc="$?"
wait "$c8_pid"
c8_rc="$?"
echo "risk lanes rc c16=$c16_rc c8=$c8_rc"
if [[ "$c16_rc" -eq 0 && "$c8_rc" -eq 0 ]]; then
  touch "$OUT/.risk-audits-complete"
  exit 0
fi
touch "$OUT/.risk-audits-failed"
exit 2

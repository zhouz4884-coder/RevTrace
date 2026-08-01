#!/usr/bin/env bash
# One-time recovery after excluding pre-holdback W4 evidence.
#
# GPU 1 starts c8 immediately. GPU 0 waits for the already-running W3 small
# mechanism probe, then starts c16. Both lanes use the ordinary reproducible
# W4 contract script; this wrapper only avoids contending with retained work.
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

rm -f "$OUT/.risk-audits-complete" "$OUT/.risk-audits-failed"

(
  bash "$CONTRACT" "$ROOT" whisper-base.en "$BASE_MODEL" base \
    "$MANIFEST" "$OUT" 8 1 20260734 1 \
    && bash "$CONTRACT" "$ROOT" whisper-small.en "$SMALL_MODEL" small \
      "$MANIFEST" "$OUT" 8 1 20260934 1
) >"$OUT/.risk-holdback-lane-c8.log" 2>&1 &
c8_pid="$!"

(
  while pgrep -f \
    "run_whisper_w_mechanism.py.*w3-mechanism-small.json" >/dev/null; do
    sleep 20
  done
  bash "$CONTRACT" "$ROOT" whisper-base.en "$BASE_MODEL" base \
    "$MANIFEST" "$OUT" 16 0 20260733 1 \
    && bash "$CONTRACT" "$ROOT" whisper-small.en "$SMALL_MODEL" small \
      "$MANIFEST" "$OUT" 16 0 20260933 1
) >"$OUT/.risk-holdback-lane-c16.log" 2>&1 &
c16_pid="$!"

wait "$c8_pid"
c8_rc="$?"
wait "$c16_pid"
c16_rc="$?"
echo "holdback W4 lanes rc c8=$c8_rc c16=$c16_rc"
if [[ "$c8_rc" -eq 0 && "$c16_rc" -eq 0 ]]; then
  touch "$OUT/.risk-audits-complete"
  exit 0
fi
touch "$OUT/.risk-audits-failed"
exit 2

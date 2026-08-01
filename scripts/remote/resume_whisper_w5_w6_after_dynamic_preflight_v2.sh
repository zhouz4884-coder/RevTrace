#!/usr/bin/env bash
# Run the disjoint formal W5/W6 epoch after the renewed dynamic-work preflight.
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

while [[ ! -f "$OUT/.w5-state-contract-release" \
  && ! -f "$OUT/.w5-dynamic-preflight-failed" ]]; do
  sleep 20
done
if [[ ! -f "$OUT/.w5-state-contract-release" ]]; then
  echo "BLOCKED: renewed dynamic-work preflight failed" >&2
  touch "$OUT/.w5-state-contract-final-blocked"
  exit 2
fi

W5_SEED_EPOCH=202728 \
W5_BASE_C16_MAX_NEW_TOKENS=96 \
W5_BASE_C8_MAX_NEW_TOKENS=80 \
W5_SMALL_C16_MAX_NEW_TOKENS=80 \
W5_SMALL_C8_MAX_NEW_TOKENS=80 \
W5_VERIFIER_LANES=1 \
bash "$PROJ/scripts/remote/run_whisper_w5_parallel.sh" \
  "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w5-state-contract-final-master.log" 2>&1
w5_rc="$?"
if [[ "$w5_rc" -ne 0 ]]; then
  echo "W5 state-contract matrix failed rc=$w5_rc" >&2
  touch "$OUT/.w5-state-contract-final-failed"
  exit "$w5_rc"
fi

W6_BASE_MAX_NEW_TOKENS=96 W6_SMALL_MAX_NEW_TOKENS=80 \
bash "$PROJ/scripts/remote/run_whisper_w6_parallel.sh" \
  "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w6-state-contract-final-master.log" 2>&1
w6_rc="$?"
echo "W6 state-contract quality rc=$w6_rc"
exit "$w6_rc"

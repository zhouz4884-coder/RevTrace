#!/usr/bin/env bash
# Recover/complete all four W4 contracts, then release downstream gates.
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

wait_pid_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    local pid
    pid="$(cat "$path")"
    while kill -0 "$pid" 2>/dev/null; do sleep 20; done
  fi
}

wait_pid_file "$OUT/.w4-base-c8-recovery.pid"

# GPU 1 completes the c8 contracts.
bash "$CONTRACT" "$ROOT" whisper-base.en "$BASE_MODEL" base \
  "$MANIFEST" "$OUT" 8 1 20260734 4 || exit 2
bash "$CONTRACT" "$ROOT" whisper-small.en "$SMALL_MODEL" small \
  "$MANIFEST" "$OUT" 8 1 20260934 1 || exit 2

# Preserve useful work from the original c16 lane, then recover only if needed.
while pgrep -f "run_whisper_w4_audits.sh.*$OUT" >/dev/null; do sleep 20; done
bash "$CONTRACT" "$ROOT" whisper-base.en "$BASE_MODEL" base \
  "$MANIFEST" "$OUT" 16 0 20260733 1 || exit 2
bash "$CONTRACT" "$ROOT" whisper-small.en "$SMALL_MODEL" small \
  "$MANIFEST" "$OUT" 16 0 20260933 1 || exit 2

for slug in base small; do
  for concurrency in 8 16; do
    test -s "$OUT/w4-final-threshold-${slug}-c${concurrency}.txt" || exit 2
    test -s "$OUT/w4-final-late-window-${slug}-c${concurrency}.txt" || exit 2
    test -s "$OUT/w4-final-late-threshold-${slug}-c${concurrency}.txt" || exit 2
  done
done
rm -f "$OUT/.risk-audits-failed"
touch "$OUT/.risk-audits-complete"
echo "ALL_W4_CONTRACTS_PASS"

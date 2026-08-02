#!/usr/bin/env bash
# Serial paper-critical recovery: c16 headline first, optional c8 boundary next.
set -uo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; OUT="$ROOT/results/revtrace/whisper_p0_p3"
mkdir -p "$OUT/logs"; cd "$PROJ" || exit 2
while pgrep -f '[r]un_whisper_c16_risk.sh' >/dev/null || \
      pgrep -f '[r]un_whisper_w_system.py audit.*c16-seed202744' >/dev/null; do
  sleep 30
done
status=0
bash scripts/remote/run_whisper_c16_recovery.sh \
 >"$OUT/logs/final-c16-recovery.log" 2>&1 || {
  touch "$OUT/p3/.c16-renewal-failed"; status=2;
}

if bash scripts/remote/run_whisper_c8_recovery.sh \
 >"$OUT/logs/final-c8-recovery.log" 2>&1; then
  if ! bash scripts/remote/run_whisper_p2_staggered.sh \
    "$ROOT" "$OUT/p0/c8-policy.json" \
    >"$OUT/logs/final-c8-staggered.log" 2>&1; then
    touch "$OUT/p3/.c8-staggered-validation-failed"
  fi
else
  mkdir -p "$OUT/p2_staggered"
  printf '%s\n' '{"schema_version":1,"candidates":[],"selected":null,"reason":"risk-policy-renewal-failed-closed"}' \
    >"$OUT/p2_staggered/selection.json"
  touch "$OUT/p3/.c8-policy-renewal-failed"
fi
touch "$OUT/.p0-p3-complete"
exit "$status"

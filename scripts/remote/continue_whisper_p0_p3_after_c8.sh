#!/usr/bin/env bash
# Continue the paper-critical work even when the optional c8 boundary
# certificate correctly fails closed.
set -uo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
mkdir -p "$OUT/logs"

while pgrep -f '[r]un_whisper_p0_p3.sh' >/dev/null; do sleep 30; done
# The failed member of a parallel audit pair can make the parent shell exit
# before its sibling.  Do not overlap the paper-critical c16 matrix with that
# orphaned GPU process.
while pgrep -f '[r]un_whisper_w_system.py audit' >/dev/null; do sleep 30; done
cd "$PROJ" || exit 2
status=0

bash scripts/remote/run_whisper_p3_c16_w2.sh \
  >"$OUT/logs/final-c16-performance.log" 2>&1 || {
    touch "$OUT/p3/.c16-performance-failed"; status=2;
  }
bash scripts/remote/run_whisper_c16_risk.sh \
  >"$OUT/logs/final-c16-risk.log" 2>&1 || {
    touch "$OUT/p3/.c16-risk-failed"; status=2;
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

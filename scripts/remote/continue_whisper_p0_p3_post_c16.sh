#!/usr/bin/env bash
# Finish the renewed c16 quality contract, then evaluate the optional c8
# long-session capacity boundary.  c8 failure never erases a valid c16 result.
set -uo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
mkdir -p "$OUT/logs"; cd "$PROJ" || exit 2

while pgrep -f '[r]un_whisper_c16_recovery.sh' >/dev/null; do sleep 30; done
status=0
if [[ ! -f "$OUT/.c16-renewal-complete" ]]; then
  echo "Renewed c16 risk certificate failed closed" >&2
  touch "$OUT/.c16-renewal-failed"
  status=2
else
  while pgrep -f '[r]un_whisper_c16_quality.sh' >/dev/null; do sleep 30; done
  if [[ ! -f "$OUT/.c16-quality-complete" ]]; then
    bash scripts/remote/run_whisper_c16_quality.sh \
      >"$OUT/logs/final-c16-quality.log" 2>&1 || {
        touch "$OUT/.c16-quality-failed"; status=2;
      }
  fi
fi

if bash scripts/remote/run_whisper_c8_recovery.sh \
  >"$OUT/logs/final-c8-recovery.log" 2>&1; then
  if ! bash scripts/remote/run_whisper_p2_staggered.sh \
    "$ROOT" "$OUT/p0/c8-policy.json" \
    >"$OUT/logs/final-c8-staggered.log" 2>&1; then
    touch "$OUT/.c8-staggered-validation-failed"
  fi
else
  mkdir -p "$OUT/p2_staggered"
  printf '%s\n' '{"schema_version":1,"candidates":[],"selected":null,"reason":"risk-policy-renewal-failed-closed"}' \
    >"$OUT/p2_staggered/selection.json"
  touch "$OUT/.c8-policy-renewal-failed"
fi
touch "$OUT/.p0-p3-complete"
exit "$status"

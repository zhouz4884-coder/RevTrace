#!/usr/bin/env bash
# Validate a renewed small-c16 W4 certificate, rerun a disjoint W5 preflight,
# then continue the formal W5/W6 epoch.  Every stage fails closed.
set -u

if [[ "$#" -ne 7 ]]; then
  echo "usage: $0 ROOT BASE_MODEL SMALL_MODEL W5_MANIFEST OUT RECERT_PID PREFLIGHT_SEED" >&2
  exit 2
fi

ROOT="$1"; BASE_MODEL="$2"; SMALL_MODEL="$3"; MANIFEST="$4"
OUT="$5"; RECERT_PID="$6"; PREFLIGHT_SEED="$7"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
export PYTHONPATH="$PROJ/src"

while kill -0 "$RECERT_PID" 2>/dev/null; do sleep 30; done

selection="$($PY - "$OUT" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
valid = []
for path in out.glob(
    "w4-risk-small-c16-m80-workv1-attempt*-seed202726*.json"
):
    try:
        row = json.load(path.open())
    except Exception:
        continue
    if row.get("decision") != "W4_RISK_CERTIFICATE_PASS":
        continue
    policy = pathlib.Path(row.get("config", {}).get("policy_source", ""))
    if policy.is_file():
        valid.append((path.stat().st_mtime_ns, path, policy))
if not valid:
    raise SystemExit(2)
_, result, policy = max(valid)
print(result)
print(policy)
PY
)"
if [[ "$?" -ne 0 ]]; then
  echo "BLOCKED: no renewed small-c16 risk certificate" >&2
  touch "$OUT/.dynamic-work-risk-recert-failed"
  exit 2
fi
result="$(printf '%s\n' "$selection" | sed -n '1p')"
policy="$(printf '%s\n' "$selection" | sed -n '2p')"

"$PY" "$PROJ/scripts/validate_whisper_w4_recert.py" \
  --result "$result" --policy "$policy" --model small \
  --concurrency 16 --max-new-tokens 80 \
  >"$OUT/small-c16-preflight-recert-v2-validation.log" 2>&1
if [[ "$?" -ne 0 ]]; then
  touch "$OUT/.dynamic-work-risk-recert-failed"
  exit 2
fi
touch "$OUT/.dynamic-work-risk-recert-complete"

WHISPER_PREFLIGHT_SEED="$PREFLIGHT_SEED" \
bash "$PROJ/scripts/remote/release_whisper_w5_after_dynamic_preflight.sh" \
  "$ROOT" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w5-dynamic-preflight-seed${PREFLIGHT_SEED}-release.log" 2>&1
if [[ "$?" -ne 0 ]]; then
  echo "BLOCKED: renewed live preflight failed" >&2
  exit 2
fi

bash "$PROJ/scripts/remote/resume_whisper_w5_w6_after_dynamic_preflight_v2.sh" \
  "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w5-w6-after-dynamic-preflight-v2.log" 2>&1
exit "$?"

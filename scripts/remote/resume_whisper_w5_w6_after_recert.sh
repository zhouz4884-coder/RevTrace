#!/usr/bin/env bash
# Resume the disjoint W5/W6 epoch only after risk-first base-c16 renewal passes.
set -u

if [[ "$#" -ne 6 ]]; then
  echo "usage: $0 ROOT BASE_MODEL SMALL_MODEL MANIFEST OUT RECERT_PID_FILE" >&2
  exit 2
fi

ROOT="$1"
BASE_MODEL="$2"
SMALL_MODEL="$3"
MANIFEST="$4"
OUT="$5"
RECERT_PID_FILE="$6"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
W5="$PROJ/scripts/remote/run_whisper_w5_parallel.sh"
W6="$PROJ/scripts/remote/run_whisper_w6_parallel.sh"

while [[ ! -s "$RECERT_PID_FILE" ]]; do sleep 10; done
recert_pid="$(cat "$RECERT_PID_FILE")"
while kill -0 "$recert_pid" 2>/dev/null; do sleep 30; done

if ! grep -q "CONTRACT_PASS base c16" \
  "$OUT/w4-base-c16-risk-first-recert.nohup"; then
  echo "BLOCKED: renewed base-c16 contract did not pass" >&2
  touch "$OUT/.w5-blocked-post-w5-recert"
  exit 2
fi

"$PY" - "$OUT" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
policy = json.load(open(out / "w4-state-age-policy-base-c16-recovery.json"))
selected = policy["selected_policy"]
assert int(selected["fast_path_state_errors"]) == 0
assert float(selected["verification_fraction"]) <= 0.20
assert int(selected["caught_roots_covered"]) >= 2

passes = []
for path in out.glob("w4-risk-base-c16-attempt*-seed*.json"):
    row = json.load(open(path))
    if (
        row.get("decision") == "W4_RISK_CERTIFICATE_PASS"
        and row.get("config", {}).get("policy_source")
        == str(out / "w4-state-age-policy-base-c16-recovery.json")
        and int(row["counts"]["risk_eligible_entries"]) >= 30000
        and int(row["counts"]["caught_state_errors"]) == 0
    ):
        passes.append(path)
assert passes, "no independent risk-first base-c16 certificate"
print({"risk_first_contract": "PASS", "certificate": str(max(passes))})
PY
if [[ "$?" -ne 0 ]]; then
  touch "$OUT/.w5-blocked-post-w5-recert"
  exit 2
fi

W5_SEED_EPOCH=202728 \
W5_BASE_C16_MAX_NEW_TOKENS=96 \
W5_BASE_C8_MAX_NEW_TOKENS=80 \
W5_SMALL_C16_MAX_NEW_TOKENS=80 \
W5_SMALL_C8_MAX_NEW_TOKENS=80 \
bash "$W5" \
  "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w5-risk-first-v3-master.log" 2>&1
w5_rc="$?"
if [[ "$w5_rc" -ne 0 ]]; then
  echo "W5 risk-first matrix failed rc=$w5_rc" >&2
  exit "$w5_rc"
fi

W6_BASE_MAX_NEW_TOKENS=96 \
W6_SMALL_MAX_NEW_TOKENS=80 \
bash "$W6" \
  "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w6-risk-first-v3-master.log" 2>&1
w6_rc="$?"
echo "W6 risk-first quality rc=$w6_rc"
exit "$w6_rc"

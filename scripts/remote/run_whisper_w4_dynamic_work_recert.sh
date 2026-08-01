#!/usr/bin/env bash
# Re-certify every max-80 deployed fingerprint after dynamic work authority.
set -u

ROOT="$1"
BASE_MODEL="$2"
SMALL_MODEL="$3"
MANIFEST="$4"
OUT="$5"
BASE_RECERT_PID="$6"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
CONTRACT="$PROJ/scripts/remote/run_whisper_w4_contract.sh"

while kill -0 "$BASE_RECERT_PID" 2>/dev/null; do sleep 30; done
while [[ ! -f "$OUT/.w6-budget-authority-small-complete" ]]; do sleep 20; done

# This 64-session development run cannot pass the final n>=128 gate by
# construction.  It must nevertheless remove every catastrophic outlier and
# satisfy all numerical quality/UX bounds before the expensive certificates
# are authorized.
"$PY" - "$OUT/development/w6-budget-authority-small/result.json" <<'PY'
import json
import sys
row = json.load(open(sys.argv[1]))
metrics = row["metrics"]
assert row["config"]["work_authority_protocol"] == (
    "decoder-step-saturation-extended-canonical-v1"
)
assert row["config"]["target_capacity_protocol"] == (
    "target-canonical-declared-work-v1"
)
assert int(row["counts"]["catastrophic_outliers"]) == 0
assert float(metrics["mean_wer_delta_pp"]) <= 1.0
assert float(metrics["paired_bootstrap_95_upper_pp"]) <= 2.0
for split in metrics["per_split"].values():
    assert float(split["mean_wer_delta_pp"]) <= 1.0
    assert float(split["paired_bootstrap_95_upper_pp"]) <= 2.0
assert float(metrics["provisional_lifetime_p95"]) <= 4.0
assert float(metrics["provisional_lifetime_max"]) <= 10.0
assert float(metrics["provisional_overwrite_p95"]) <= 20.0
assert int(row["counts"]["work_budget_authorities"]) > 0
print({
    "dynamic_work_development_gate": "PASS",
    "catastrophic_outliers": row["counts"]["catastrophic_outliers"],
    "work_budget_authorities": row["counts"]["work_budget_authorities"],
    "mean_wer_delta_pp": metrics["mean_wer_delta_pp"],
})
PY
if [[ "$?" -ne 0 ]]; then
  echo "BLOCKED: dynamic work authority development gate failed" >&2
  touch "$OUT/.dynamic-work-risk-recert-blocked"
  exit 2
fi

WHISPER_MAX_NEW_TOKENS=80 bash "$CONTRACT" \
  "$ROOT" whisper-base.en "$BASE_MODEL" base "$MANIFEST" "$OUT" \
  8 0 20272570 1 >"$OUT/w4-base-c8-workv1.nohup" 2>&1 &
p0="$!"
WHISPER_MAX_NEW_TOKENS=80 bash "$CONTRACT" \
  "$ROOT" whisper-small.en "$SMALL_MODEL" small "$MANIFEST" "$OUT" \
  16 1 20272580 1 >"$OUT/w4-small-c16-workv1.nohup" 2>&1 &
p1="$!"
wait "$p0"; r0="$?"
wait "$p1"; r1="$?"
if [[ "$r0" -ne 0 || "$r1" -ne 0 ]]; then
  echo "dynamic work risk recert wave1 failed base-c8=$r0 small-c16=$r1" >&2
  touch "$OUT/.dynamic-work-risk-recert-failed"
  exit 2
fi

WHISPER_MAX_NEW_TOKENS=80 bash "$CONTRACT" \
  "$ROOT" whisper-small.en "$SMALL_MODEL" small "$MANIFEST" "$OUT" \
  8 1 20272590 1 >"$OUT/w4-small-c8-workv1.nohup" 2>&1
r2="$?"
if [[ "$r2" -ne 0 ]]; then
  echo "dynamic work risk recert wave2 failed small-c8=$r2" >&2
  touch "$OUT/.dynamic-work-risk-recert-failed"
  exit 2
fi
touch "$OUT/.dynamic-work-risk-recert-complete"
echo "DYNAMIC_WORK_RISK_RECERT_PASS"

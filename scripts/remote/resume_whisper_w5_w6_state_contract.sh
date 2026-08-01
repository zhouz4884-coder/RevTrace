#!/usr/bin/env bash
# Resume final disjoint W5/W6 only after the state-contract policy recertifies.
set -u
ROOT="$1"; BASE_MODEL="$2"; SMALL_MODEL="$3"; MANIFEST="$4"
OUT="$5"; RECERT_PID_FILE="$6"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"

while [[ ! -s "$RECERT_PID_FILE" ]]; do sleep 10; done
pid="$(cat "$RECERT_PID_FILE")"
while kill -0 "$pid" 2>/dev/null; do sleep 30; done
if ! grep -q "CONTRACT_PASS base c16" \
  "$OUT/w4-base-c16-state-contract-recert.nohup"; then
  echo "BLOCKED: state-contract risk renewal failed" >&2
  touch "$OUT/.w5-blocked-state-contract-recert"
  exit 2
fi

while [[ ! -f "$OUT/.dynamic-work-risk-recert-complete" \
  && ! -f "$OUT/.dynamic-work-risk-recert-failed" \
  && ! -f "$OUT/.dynamic-work-risk-recert-blocked" ]]; do
  sleep 30
done
if [[ ! -f "$OUT/.dynamic-work-risk-recert-complete" ]]; then
  echo "BLOCKED: dynamic work risk recertification failed" >&2
  touch "$OUT/.w5-blocked-dynamic-work-recert"
  exit 2
fi

"$PY" - "$OUT" <<'PY'
import json,pathlib,sys
out=pathlib.Path(sys.argv[1])
p=json.load(open(out/"w4-state-age-policy-base-c16-recovery.json"))
s=p["selected_policy"]
assert int(s["fast_path_state_errors"]) == 0
assert float(s["verification_fraction"]) <= 0.20
assert int(s["caught_roots_covered"]) >= 3
matches=[]
for path in out.glob("w4-risk-base-c16-attempt*-seed*.json"):
    row=json.load(open(path))
    if (
        row.get("decision") == "W4_RISK_CERTIFICATE_PASS"
        and row.get("config",{}).get("policy_source")
        == str(out/"w4-state-age-policy-base-c16-recovery.json")
        and int(row["counts"]["risk_eligible_entries"]) >= 30000
        and int(row["counts"]["caught_state_errors"]) == 0
    ):
        matches.append(path)
assert matches, "no renewed independent state-contract certificate"
print({"state_contract_recert":"PASS","certificate":str(max(matches))})

# Every deployed (model, concurrency, work-budget) fingerprint must have an
# independent post-policy certificate.  Older max-80 audits predate dynamic
# work authority and are intentionally rejected here.
contracts = (
    ("base", 16, 96),
    ("base", 8, 80),
    ("small", 16, 80),
    ("small", 8, 80),
)
for model_slug, concurrency, max_new in contracts:
    accepted = []
    for path in out.glob(
        f"w4-risk-{model_slug}-c{concurrency}-*.json"
    ):
        row = json.load(open(path))
        cfg = row.get("config", {})
        if (
            row.get("decision") == "W4_RISK_CERTIFICATE_PASS"
            and int(cfg.get("max_new_tokens", -1)) == max_new
            and int(cfg.get("authority_max_new_tokens", -1)) == 96
            and int(row.get("counts", {}).get(
                "risk_eligible_entries", 0
            )) >= 30000
            and int(row.get("counts", {}).get(
                "pre_outcome_randomized_audits", 0
            )) >= 500
            and int(row.get("counts", {}).get(
                "caught_state_errors", -1
            )) == 0
            and (
                max_new == 96
                or cfg.get("work_authority_protocol")
                == "decoder-step-saturation-extended-canonical-v1"
            )
            and (
                max_new == 96
                or cfg.get("target_capacity_protocol")
                == "target-canonical-declared-work-v1"
            )
        ):
            accepted.append(path)
    assert accepted, (
        "no independent certificate for "
        f"{model_slug} c{concurrency} max_new={max_new}"
    )
    print({
        "risk_contract": "PASS",
        "model": model_slug,
        "concurrency": concurrency,
        "max_new_tokens": max_new,
        "certificate": str(max(accepted)),
    })
PY
if [[ "$?" -ne 0 ]]; then
  touch "$OUT/.w5-blocked-state-contract-recert"
  exit 2
fi

# A final state-only quality attribution and post-timing state-root audit run
# independently on the other GPU.  W5 may start only after those diagnostics
# have been inspected and an explicit release marker is created.  This avoids
# racing a newly discovered adaptation root with the final disjoint seed.
while [[ ! -f "$OUT/.w5-state-contract-release" ]]; do sleep 20; done

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

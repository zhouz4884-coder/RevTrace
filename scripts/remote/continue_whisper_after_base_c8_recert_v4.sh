#!/usr/bin/env bash
# Continue W0-W7 after two independent base/c8 long-state certificates.
set -u

if [[ "$#" -ne 5 ]]; then
  echo "usage: $0 ROOT BASE_MODEL SMALL_MODEL MANIFEST OUT" >&2
  exit 2
fi

ROOT="$1"; BASE_MODEL="$2"; SMALL_MODEL="$3"; MANIFEST="$4"; OUT="$5"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
# Attempts 1-3 supplied adaptation-only roots. Only the two independent
# attempt-4 streams below are eligible for release.
RESULT1="$OUT/w4-risk-base-c8-m80-workv1-attempt4-seed20273300.json"
RESULT2="$OUT/w4-risk-base-c8-m80-workv1-attempt4-seed20273350.json"
PREFLIGHT="$OUT/development/w5-base-c8-long-recovery-preflight-seed20272919.json"
PREFLIGHT_LOG="${PREFLIGHT%.json}.log"
PREFLIGHT_ORACLE="$OUT/development/oracle-w5-base-c8-long-recovery-preflight-seed20272919.json"

export PYTHONPATH="$PROJ/src"
cd "$PROJ"
mkdir -p "$OUT/development"

for result in "$RESULT1" "$RESULT2"; do
  while [[ ! -s "$result" ]]; do sleep 30; done
  policy="$($PY - "$result" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1]))["config"]["policy_source"])
PY
)"
  "$PY" scripts/validate_whisper_w4_recert.py \
    --result "$result" --policy "$policy" \
    --model whisper-base.en --concurrency 8 --max-new-tokens 80 \
    || {
      touch "$OUT/.w4-base-c8-double-recert-failed"
      exit 2
    }
done
touch "$OUT/.w4-base-c8-double-recert-pass"

tau="$(cat "$OUT/w4-final-threshold-base-c8.txt")"
lw="$(cat "$OUT/w4-final-late-window-base-c8.txt")"
lt="$(cat "$OUT/w4-final-late-threshold-base-c8.txt")"
hp="$(cat "$OUT/w4-final-high-load-prompt-base-c8.txt")"
ht="$(cat "$OUT/w4-final-high-load-threshold-base-c8.txt")"
context=()
if [[ "$lw" != none ]]; then
  context+=(--late-window-index "$lw" --late-margin-threshold "$lt")
fi
if [[ "$hp" != none ]]; then
  context+=(
    --high-load-prompt-tokens "$hp"
    --high-load-margin-threshold "$ht"
  )
fi

if [[ ! -s "$PREFLIGHT" ]]; then
  "$PY" "$RUNNER" workload \
    --model "$BASE_MODEL" --model-name whisper-base.en \
    --manifest "$MANIFEST" --output "$PREFLIGHT" \
    --oracle-cache "$PREFLIGHT_ORACLE" --system revtrace \
    --sessions 8 --duration-seconds 180 --window-seconds 10 \
    --concurrency 8 --arrival sync --seed 20272919 \
    --margin-threshold "$tau" "${context[@]}" \
    --max-new-tokens 80 --authority-max-new-tokens 96 \
    --audit-probability 0.021 --slo-seconds 2.0 \
    --power-sample-seconds 0.2 \
    --proposer-device cuda:0 --verifier-device cuda:1 \
    --verifier-lanes 1 --terminal-contract state-only \
    >"$PREFLIGHT_LOG" 2>&1
  rc="$?"
  if [[ "$rc" -ne 0 ]]; then
    touch "$OUT/.w5-base-c8-recovery-preflight-failed"
    exit "$rc"
  fi
fi

"$PY" - "$PREFLIGHT" <<'PY'
import json
import math
import sys

row = json.load(open(sys.argv[1]))
cfg, counts, metrics = row["config"], row["counts"], row["metrics"]
assert cfg["state_control_protocol"] == (
    "prompt-state-deferred-authority-checkpoint10-capacity-rebase-v2"
)
assert cfg["work_authority_protocol"] == (
    "decoder-step-saturation-extended-canonical-v1"
)
assert cfg["target_capacity_protocol"] == (
    "target-canonical-declared-work-v1"
)
assert int(cfg["max_new_tokens"]) == 80
assert int(cfg["authority_max_new_tokens"]) == 96
assert cfg["terminal_contract"] == "state-only"
for key in (
    "state_violations",
    "stale_commits",
    "post_timing_stable_output_mismatches",
    "post_timing_stable_state_mismatches",
):
    assert int(counts[key]) == 0, (key, counts[key])
assert float(metrics["verification_fraction"]) <= 0.20
assert float(metrics["wall_speedup"]) >= 2.0
assert float(metrics["display_slo_goodput_speedup"]) >= 2.0
assert math.isfinite(float(metrics["latency_p99"]))
assert math.isfinite(float(metrics["display_latency_p99"]))
print({
    "base_c8_long_recovery_preflight": "PASS",
    "wall_speedup": metrics["wall_speedup"],
    "display_slo_goodput_speedup": metrics["display_slo_goodput_speedup"],
    "state_p99": metrics["latency_p99"],
    "display_p99": metrics["display_latency_p99"],
    "verification_fraction": metrics["verification_fraction"],
})
PY
if [[ "$?" -ne 0 ]]; then
  touch "$OUT/.w5-base-c8-recovery-preflight-failed"
  exit 2
fi
touch "$OUT/.w5-base-c8-recovery-preflight-pass"
touch "$OUT/.w5-state-contract-release-202730"

W5_SEED_EPOCH=202730 \
W5_BASE_C16_MAX_NEW_TOKENS=96 \
W5_BASE_C8_MAX_NEW_TOKENS=80 \
W5_SMALL_C16_MAX_NEW_TOKENS=80 \
W5_SMALL_C8_MAX_NEW_TOKENS=80 \
W5_VERIFIER_LANES=1 \
bash "$PROJ/scripts/remote/run_whisper_w5_parallel.sh" \
  "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w5-state-contract-202730-master.log" 2>&1
w5_rc="$?"
if [[ "$w5_rc" -ne 0 ]]; then
  touch "$OUT/.w5-state-contract-202730-failed"
  exit "$w5_rc"
fi
touch "$OUT/.w5-state-contract-202730-complete"

W6_BASE_MAX_NEW_TOKENS=96 W6_SMALL_MAX_NEW_TOKENS=80 \
bash "$PROJ/scripts/remote/run_whisper_w6_parallel.sh" \
  "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w6-state-contract-202730-master.log" 2>&1
w6_rc="$?"
echo "W6 state-contract quality rc=$w6_rc"
exit "$w6_rc"

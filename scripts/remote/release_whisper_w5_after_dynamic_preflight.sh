#!/usr/bin/env bash
# Release final W5 only after max-80 risk recerts and a live two-GPU preflight.
set -u
ROOT="$1"; SMALL_MODEL="$2"; MANIFEST="$3"; OUT="$4"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
export PYTHONPATH="$PROJ/src"
PREFLIGHT_SEED="${WHISPER_PREFLIGHT_SEED:-20272619}"

while [[ ! -f "$OUT/.dynamic-work-risk-recert-complete" \
  && ! -f "$OUT/.dynamic-work-risk-recert-failed" ]]; do sleep 30; done
if [[ ! -f "$OUT/.dynamic-work-risk-recert-complete" ]]; then
  touch "$OUT/.w5-dynamic-preflight-blocked"
  exit 2
fi

tau="$(cat "$OUT/w4-final-threshold-small-c16.txt")"
lw="$(cat "$OUT/w4-final-late-window-small-c16.txt")"
lt="$(cat "$OUT/w4-final-late-threshold-small-c16.txt")"
hp="$(cat "$OUT/w4-final-high-load-prompt-small-c16.txt")"
ht="$(cat "$OUT/w4-final-high-load-threshold-small-c16.txt")"
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

result="$OUT/development/w5-dynamic-work-preflight-small-c16-seed${PREFLIGHT_SEED}.json"
log="$OUT/development/w5-dynamic-work-preflight-small-c16-seed${PREFLIGHT_SEED}.log"
oracle="$OUT/development/oracle-dynamic-work-preflight-small-c16-seed${PREFLIGHT_SEED}.json"
if [[ ! -s "$result" ]]; then
  "$PY" "$RUNNER" workload \
    --model "$SMALL_MODEL" --model-name whisper-small.en \
    --manifest "$MANIFEST" --output "$result" \
    --oracle-cache "$oracle" --system revtrace \
    --sessions 16 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --arrival sync --seed "$PREFLIGHT_SEED" \
    --margin-threshold "$tau" "${context[@]}" \
    --max-new-tokens 80 --authority-max-new-tokens 96 \
    --audit-probability 0.021 --slo-seconds 2.0 \
    --power-sample-seconds 0.2 \
    --proposer-device cuda:0 --verifier-device cuda:1 \
    --verifier-lanes 1 --terminal-contract state-only >"$log" 2>&1
  rc="$?"
  if [[ "$rc" -ne 0 ]]; then
    touch "$OUT/.w5-dynamic-preflight-failed"
    exit "$rc"
  fi
else
  echo "REUSE_EXISTING_PREFLIGHT $result"
fi

"$PY" - "$result" <<'PY'
import json
import math
import sys
row = json.load(open(sys.argv[1]))
cfg, counts, metrics = row["config"], row["counts"], row["metrics"]
assert cfg["work_authority_protocol"] == (
    "decoder-step-saturation-extended-canonical-v1"
)
assert cfg["target_capacity_protocol"] == (
    "target-canonical-declared-work-v1"
)
assert int(cfg["max_new_tokens"]) == 80
assert int(cfg["authority_max_new_tokens"]) == 96
assert cfg["terminal_contract"] == "state-only"
assert int(counts["state_violations"]) == 0
assert int(counts["stale_commits"]) == 0
assert int(counts["post_timing_stable_output_mismatches"]) == 0
assert int(counts["post_timing_stable_state_mismatches"]) == 0
assert float(metrics["verification_fraction"]) <= 0.20
assert float(metrics["wall_speedup"]) >= 2.0
assert float(metrics["display_slo_goodput_speedup"]) >= 2.0
assert math.isfinite(float(metrics["latency_p99"]))
assert math.isfinite(float(metrics["display_latency_p99"]))
print({
    "dynamic_work_preflight": "PASS",
    "wall_speedup": metrics["wall_speedup"],
    "display_slo_goodput_speedup": (
        metrics["display_slo_goodput_speedup"]
    ),
    "state_p99": metrics["latency_p99"],
    "display_p99": metrics["display_latency_p99"],
    "verification_fraction": metrics["verification_fraction"],
    "work_budget_authorities": counts["work_budget_authorities"],
})
PY
if [[ "$?" -ne 0 ]]; then
  touch "$OUT/.w5-dynamic-preflight-failed"
  exit 2
fi
touch "$OUT/.w5-dynamic-preflight-pass"
touch "$OUT/.w5-state-contract-release"
echo "W5_DYNAMIC_PREFLIGHT_RELEASE_PASS"

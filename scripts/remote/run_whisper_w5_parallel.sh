#!/usr/bin/env bash
# Run the two-model W5 matrix sequentially; each RevTrace cell uses both GPUs.
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
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
MATRIX="$PROJ/scripts/remote/run_whisper_w_matrix.sh"
BASE_C16_MAX_NEW_TOKENS="${W5_BASE_C16_MAX_NEW_TOKENS:-96}"
BASE_C8_MAX_NEW_TOKENS="${W5_BASE_C8_MAX_NEW_TOKENS:-80}"
SMALL_C16_MAX_NEW_TOKENS="${W5_SMALL_C16_MAX_NEW_TOKENS:-80}"
SMALL_C8_MAX_NEW_TOKENS="${W5_SMALL_C8_MAX_NEW_TOKENS:-80}"
VERIFIER_LANES="${W5_VERIFIER_LANES:-1}"

export PYTHONPATH="$PROJ/src"
# Keep capacity-rebase-v2 oracle trajectories in a protocol-versioned cache.
# Reusing the pre-repair cache would compare deployed systems against a
# different amount of canonical work and is therefore invalid evidence.
ORACLE_DIR="$OUT/oracle-dynamic-work-target-capacity-v4"
mkdir -p "$ORACLE_DIR" "$OUT/logs"

while [[ ! -f "$OUT/.w3-mechanism-complete" \
  && ! -f "$OUT/.w3-mechanism-failed" ]]; do
  sleep 20
done
if [[ ! -f "$OUT/.w3-mechanism-complete" ]]; then
  echo "W5 blocked: W3 mechanism gate did not pass" >&2
  touch "$OUT/.w5-blocked-w3"
  exit 2
fi
while [[ ! -f "$OUT/.risk-audits-complete" \
  && ! -f "$OUT/.risk-audits-failed" ]]; do
  sleep 20
done
if [[ ! -f "$OUT/.risk-audits-complete" ]]; then
  echo "W5 blocked: risk audit did not pass" >&2
  touch "$OUT/.w5-blocked-risk"
  exit 2
fi

tau_b16="$(cat "$OUT/w4-final-threshold-base-c16.txt")"
tau_b8="$(cat "$OUT/w4-final-threshold-base-c8.txt")"
tau_s16="$(cat "$OUT/w4-final-threshold-small-c16.txt")"
tau_s8="$(cat "$OUT/w4-final-threshold-small-c8.txt")"
late_w_b16="$(cat "$OUT/w4-final-late-window-base-c16.txt")"
late_tau_b16="$(cat "$OUT/w4-final-late-threshold-base-c16.txt")"
late_w_b8="$(cat "$OUT/w4-final-late-window-base-c8.txt")"
late_tau_b8="$(cat "$OUT/w4-final-late-threshold-base-c8.txt")"
late_w_s16="$(cat "$OUT/w4-final-late-window-small-c16.txt")"
late_tau_s16="$(cat "$OUT/w4-final-late-threshold-small-c16.txt")"
late_w_s8="$(cat "$OUT/w4-final-late-window-small-c8.txt")"
late_tau_s8="$(cat "$OUT/w4-final-late-threshold-small-c8.txt")"
load_p_b16="$(cat "$OUT/w4-final-high-load-prompt-base-c16.txt")"
load_tau_b16="$(cat "$OUT/w4-final-high-load-threshold-base-c16.txt")"
load_p_b8="$(cat "$OUT/w4-final-high-load-prompt-base-c8.txt")"
load_tau_b8="$(cat "$OUT/w4-final-high-load-threshold-base-c8.txt")"
load_p_s16="$(cat "$OUT/w4-final-high-load-prompt-small-c16.txt")"
load_tau_s16="$(cat "$OUT/w4-final-high-load-threshold-small-c16.txt")"
load_p_s8="$(cat "$OUT/w4-final-high-load-prompt-small-c8.txt")"
load_tau_s8="$(cat "$OUT/w4-final-high-load-threshold-small-c8.txt")"
base_preflight_late_args=()
if [[ "$late_w_b8" != "none" && "$late_tau_b8" != "none" ]]; then
  base_preflight_late_args+=(
    --late-window-index "$late_w_b8"
    --late-margin-threshold "$late_tau_b8"
  )
fi
if [[ "$load_p_b8" != "none" && "$load_tau_b8" != "none" ]]; then
  base_preflight_late_args+=(
    --high-load-prompt-tokens "$load_p_b8"
    --high-load-margin-threshold "$load_tau_b8"
  )
fi

"$PY" "$RUNNER" workload \
  --model "$BASE_MODEL" \
  --model-name whisper-base.en \
  --manifest "$MANIFEST" \
  --output "$OUT/w5-preflight-base.json" \
  --oracle-cache "$ORACLE_DIR/w5-preflight-base.json" \
  --system revtrace \
  --sessions 8 \
  --duration-seconds 30 \
  --window-seconds 10 \
  --concurrency 8 \
  --arrival sync \
  --seed 20260991 \
  --max-new-tokens "$BASE_C8_MAX_NEW_TOKENS" \
  --authority-max-new-tokens 96 \
  --margin-threshold "$tau_b8" \
  "${base_preflight_late_args[@]}" \
  --proposer-device cuda:0 \
  --verifier-device cuda:1 \
  --verifier-lanes "$VERIFIER_LANES" \
  --terminal-contract state-only \
  >"$OUT/w5-preflight-base.log" 2>&1
pre_rc="$?"
if [[ "$pre_rc" -ne 0 ]]; then
  echo "W5 preflight runner rc=$pre_rc" >&2
  touch "$OUT/.w5-preflight-failed"
  exit "$pre_rc"
fi

"$PY" - "$OUT/w5-preflight-base.json" <<'PY'
import json
import math
import sys

row = json.load(open(sys.argv[1]))
assert row["config"]["prompt_state_semantics"] == (
    "raw-segment-token-history-v5-deferred-authority"
)
assert row["config"]["precision"] == "float16"
assert row["config"]["baseline_capacity_protocol"] == (
    "declared-work-capacity-rebase-v2"
)
assert row["config"]["state_control_protocol"] == (
    "prompt-state-deferred-authority-checkpoint10-capacity-rebase-v2"
)
assert row["config"]["post_timing_validation"] == (
    "exhaustive-same-state-replay-with-repeat-control-v2"
)
assert int(row["config"]["verifier_lanes"]) == 1
assert int(row["config"]["authority_max_new_tokens"]) == 96
assert row["config"]["work_authority_protocol"] == (
    "decoder-step-saturation-extended-canonical-v1"
)
assert row["config"]["target_capacity_protocol"] == (
    "target-canonical-declared-work-v1"
)
assert row["config"]["warmup"]["verifier_lane_exact"] is True
assert row["config"]["terminal_contract"] == "state-only"
assert row["config"]["terminal_spillover_on_proposer"] is False
assert int(row["counts"]["terminal_authorities"]) == 0
assert int(row["counts"]["terminal_display_only"]) > 0
assert row["counts"]["state_violations"] == 0
assert row["counts"]["stale_commits"] == 0
assert (
    row["counts"]["post_timing_fast_path_audits"]
    == row["counts"]["safe_commits"]
)
assert row["counts"]["post_timing_stable_state_mismatches"] == 0
assert math.isfinite(row["metrics"]["latency_p99"])
assert math.isfinite(row["metrics"]["display_latency_p99"])
assert math.isfinite(row["metrics"]["baseline_latency_p99"])
print({
    "preflight": "PASS",
    "p99": row["metrics"]["latency_p99"],
    "display_p99": row["metrics"]["display_latency_p99"],
    "baseline_p99": row["metrics"]["baseline_latency_p99"],
})
PY
if [[ "$?" -ne 0 ]]; then
  touch "$OUT/.w5-preflight-failed"
  exit 2
fi
touch "$OUT/.w5-preflight-pass"

W5_MAX_NEW_TOKENS_C16="$BASE_C16_MAX_NEW_TOKENS" \
W5_MAX_NEW_TOKENS_C8="$BASE_C8_MAX_NEW_TOKENS" \
W5_AUTHORITY_MAX_NEW_TOKENS_C16=96 \
W5_AUTHORITY_MAX_NEW_TOKENS_C8=96 \
W5_VERIFIER_LANES="$VERIFIER_LANES" \
bash "$MATRIX" \
  "$ROOT" "$BASE_MODEL" whisper-base.en "$MANIFEST" "$OUT" cuda:0 \
  "$tau_b16" "$tau_b8" \
  "$late_w_b16" "$late_tau_b16" "$late_w_b8" "$late_tau_b8" \
  "$load_p_b16" "$load_tau_b16" "$load_p_b8" "$load_tau_b8" \
  >"$OUT/w5-matrix-base.log" 2>&1
base_rc="$?"

small_rc=2
if [[ "$base_rc" -eq 0 ]]; then
  W5_MAX_NEW_TOKENS_C16="$SMALL_C16_MAX_NEW_TOKENS" \
  W5_MAX_NEW_TOKENS_C8="$SMALL_C8_MAX_NEW_TOKENS" \
  W5_AUTHORITY_MAX_NEW_TOKENS_C16=96 \
  W5_AUTHORITY_MAX_NEW_TOKENS_C8=96 \
  W5_VERIFIER_LANES="$VERIFIER_LANES" \
  bash "$MATRIX" \
    "$ROOT" "$SMALL_MODEL" whisper-small.en "$MANIFEST" "$OUT" cuda:0 \
    "$tau_s16" "$tau_s8" \
    "$late_w_s16" "$late_tau_s16" "$late_w_s8" "$late_tau_s8" \
    "$load_p_s16" "$load_tau_s16" "$load_p_s8" "$load_tau_s8" \
    >"$OUT/w5-matrix-small.log" 2>&1
  small_rc="$?"
fi

echo "W5 matrix rc base=$base_rc small=$small_rc"
if [[ "$base_rc" -ne 0 || "$small_rc" -ne 0 ]]; then
  touch "$OUT/.w5-matrix-failed"
  exit 2
fi
touch "$OUT/.w5-matrix-complete"

#!/usr/bin/env bash
# Run paired W6 quality/UX evaluation for both Whisper scales in parallel.
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
RUNNER="$PROJ/scripts/remote/run_whisper_w_quality.py"
BASE_MAX_NEW_TOKENS="${W6_BASE_MAX_NEW_TOKENS:-96}"
SMALL_MAX_NEW_TOKENS="${W6_SMALL_MAX_NEW_TOKENS:-80}"
QUALITY_MANIFEST="${W6_QUALITY_MANIFEST:-$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json}"

export PYTHONPATH="$PROJ/src"
"$PY" - "$QUALITY_MANIFEST" <<'PY'
import json
import sys

row = json.load(open(sys.argv[1]))
records = row.get("records", [])
splits = {item.get("split") for item in records}
assert {"test-clean", "test-other"} <= splits
assert all(
    item.get("text") and item.get("path") and item.get("utterance_id")
    for item in records
)
PY
if [[ "$?" -ne 0 ]]; then
  echo "W6 quality manifest schema validation failed" >&2
  touch "$OUT/.w6-quality-failed"
  exit 2
fi
while [[ ! -f "$OUT/.w5-matrix-complete" \
  && ! -f "$OUT/.w5-matrix-failed" \
  && ! -f "$OUT/.w5-blocked-risk" \
  && ! -f "$OUT/.w5-blocked-w3" ]]; do
  sleep 20
done
if [[ ! -f "$OUT/.w5-matrix-complete" ]]; then
  echo "W6 blocked: W5 did not complete" >&2
  touch "$OUT/.w6-blocked"
  exit 2
fi

tau_b16="$(cat "$OUT/w4-final-threshold-base-c16.txt")"
tau_s16="$(cat "$OUT/w4-final-threshold-small-c16.txt")"
late_w_b16="$(cat "$OUT/w4-final-late-window-base-c16.txt")"
late_tau_b16="$(cat "$OUT/w4-final-late-threshold-base-c16.txt")"
late_w_s16="$(cat "$OUT/w4-final-late-window-small-c16.txt")"
late_tau_s16="$(cat "$OUT/w4-final-late-threshold-small-c16.txt")"
load_p_b16="$(cat "$OUT/w4-final-high-load-prompt-base-c16.txt")"
load_tau_b16="$(cat "$OUT/w4-final-high-load-threshold-base-c16.txt")"
load_p_s16="$(cat "$OUT/w4-final-high-load-prompt-small-c16.txt")"
load_tau_s16="$(cat "$OUT/w4-final-high-load-threshold-small-c16.txt")"
base_late_args=()
small_late_args=()
if [[ "$late_w_b16" != "none" && "$late_tau_b16" != "none" ]]; then
  base_late_args+=(
    --late-window-index "$late_w_b16"
    --late-margin-threshold "$late_tau_b16"
  )
fi
if [[ "$load_p_b16" != "none" && "$load_tau_b16" != "none" ]]; then
  base_late_args+=(
    --high-load-prompt-tokens "$load_p_b16"
    --high-load-margin-threshold "$load_tau_b16"
  )
fi
if [[ "$late_w_s16" != "none" && "$late_tau_s16" != "none" ]]; then
  small_late_args+=(
    --late-window-index "$late_w_s16"
    --late-margin-threshold "$late_tau_s16"
  )
fi
if [[ "$load_p_s16" != "none" && "$load_tau_s16" != "none" ]]; then
  small_late_args+=(
    --high-load-prompt-tokens "$load_p_s16"
    --high-load-margin-threshold "$load_tau_s16"
  )
fi

base_output="$OUT/w6-quality-base.json"
base_prerun="$OUT/w6-quality-base-prerun.json"
base_pid=""
base_prerun_valid=false
if [[ -s "$base_prerun" ]] && "$PY" - \
  "$base_prerun" "$tau_b16" "$late_w_b16" "$late_tau_b16" \
  "$load_p_b16" "$load_tau_b16" "$BASE_MAX_NEW_TOKENS" <<'PY'
import json
import math
import sys

row = json.load(open(sys.argv[1]))
config = row.get("config", {})

def optional_number(raw):
    return None if raw == "none" else float(raw)

def optional_integer(raw):
    return None if raw == "none" else int(raw)

def same_number(left, right):
    if left is None or right is None:
        return left is right
    return math.isclose(
        float(left), float(right), rel_tol=0.0, abs_tol=1e-12
    )

assert row.get("decision") == "W6_QUALITY_UX_PASS"
assert config.get("deferred_risk_authority") is True
assert config.get("deferred_terminal_authority") is False
assert config.get("prompt_state_semantics") == (
    "raw-segment-token-history-v5-deferred-authority"
)
assert config.get("state_control_protocol") == (
    "prompt-state-deferred-authority-checkpoint10-capacity-rebase-v2"
)
assert config.get("work_authority_protocol") == (
    "decoder-step-saturation-extended-canonical-v1"
)
assert config.get("target_capacity_protocol") == (
    "target-canonical-declared-work-v1"
)
assert config.get("local_agreement_capacity_protocol") == (
    "declared-work-capacity-rebase-v2"
)
assert config.get("precision") == "float16"
assert int(config.get("concurrency", -1)) == 16
assert int(config.get("max_new_tokens", -1)) == int(sys.argv[7])
assert int(config.get("reference_max_new_tokens", -1)) == 96
assert int(config.get("authority_max_new_tokens", -1)) == 96
assert same_number(config.get("margin_threshold"), float(sys.argv[2]))
assert config.get("late_window_index") == optional_integer(sys.argv[3])
assert same_number(
    config.get("late_margin_threshold"),
    optional_number(sys.argv[4]),
)
assert config.get("high_load_prompt_tokens") == optional_integer(
    sys.argv[5]
)
assert same_number(
    config.get("high_load_margin_threshold"),
    optional_number(sys.argv[6]),
)
PY
then
  base_prerun_valid=true
fi
if [[ "$base_prerun_valid" == true ]]; then
  cp "$base_prerun" "$base_output"
  echo "W6 reuse independent base quality prerun"
else
"$PY" "$RUNNER" \
  --model "$BASE_MODEL" \
  --model-name whisper-base.en \
  --manifest "$QUALITY_MANIFEST" \
  --output "$base_output" \
  --sessions-per-split 64 \
  --duration-seconds 90 \
  --window-seconds 10 \
  --concurrency 16 \
  --margin-threshold "$tau_b16" \
  "${base_late_args[@]}" \
  --seed 20260811 \
  --bootstrap-seed 20260812 \
  --bootstrap-replicates 10000 \
  --max-new-tokens "$BASE_MAX_NEW_TOKENS" \
  --authority-max-new-tokens 96 \
  --reference-max-new-tokens 96 \
  --no-deferred-terminal-authority \
  --device cuda:0 >"$OUT/w6-quality-base.log" 2>&1 &
base_pid="$!"
fi

"$PY" "$RUNNER" \
  --model "$SMALL_MODEL" \
  --model-name whisper-small.en \
  --manifest "$QUALITY_MANIFEST" \
  --output "$OUT/w6-quality-small.json" \
  --sessions-per-split 64 \
  --duration-seconds 90 \
  --window-seconds 10 \
  --concurrency 16 \
  --margin-threshold "$tau_s16" \
  "${small_late_args[@]}" \
  --seed 20260813 \
  --bootstrap-seed 20260814 \
  --bootstrap-replicates 10000 \
  --max-new-tokens "$SMALL_MAX_NEW_TOKENS" \
  --authority-max-new-tokens 96 \
  --reference-max-new-tokens 96 \
  --no-deferred-terminal-authority \
  --device cuda:1 >"$OUT/w6-quality-small.log" 2>&1 &
small_pid="$!"

base_rc=0
if [[ -n "$base_pid" ]]; then
  wait "$base_pid"
  base_rc="$?"
fi
wait "$small_pid"
small_rc="$?"

echo "W6 quality rc base=$base_rc small=$small_rc"
if [[ "$base_rc" -ne 0 || "$small_rc" -ne 0 ]]; then
  touch "$OUT/.w6-quality-failed"
  exit 2
fi
touch "$OUT/.w6-quality-complete"

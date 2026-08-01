#!/usr/bin/env bash
# Run the frozen W5 operating envelope for one Whisper model/one GPU.
set -u

if [[ "$#" -ne 16 ]]; then
  echo "usage: $0 ROOT MODEL_PATH MODEL_NAME MANIFEST OUT GPU TAU_C16 TAU_C8 LATE_W16 LATE_TAU16 LATE_W8 LATE_TAU8 LOAD_P16 LOAD_TAU16 LOAD_P8 LOAD_TAU8" >&2
  exit 2
fi

ROOT="$1"
MODEL_PATH="$2"
MODEL_ID="$3"
MODEL_SLUG="${MODEL_ID#whisper-}"
MODEL_SLUG="${MODEL_SLUG%.en}"
MANIFEST="$4"
OUT="$5"
GPU="$6"
TAU_C16="$7"
TAU_C8="$8"
LATE_W16="$9"
LATE_TAU16="${10}"
LATE_W8="${11}"
LATE_TAU8="${12}"
LOAD_P16="${13}"
LOAD_TAU16="${14}"
LOAD_P8="${15}"
LOAD_TAU8="${16}"
W5_SEED_EPOCH="${W5_SEED_EPOCH:-202638}"
MAX_NEW_TOKENS_C16="${W5_MAX_NEW_TOKENS_C16:-96}"
MAX_NEW_TOKENS_C8="${W5_MAX_NEW_TOKENS_C8:-96}"
AUTHORITY_MAX_NEW_TOKENS_C16="${W5_AUTHORITY_MAX_NEW_TOKENS_C16:-$MAX_NEW_TOKENS_C16}"
AUTHORITY_MAX_NEW_TOKENS_C8="${W5_AUTHORITY_MAX_NEW_TOKENS_C8:-$MAX_NEW_TOKENS_C8}"
VERIFIER_LANES="${W5_VERIFIER_LANES:-1}"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
mkdir -p "$OUT/oracle" "$OUT/logs"
export PYTHONPATH="$PROJ/src"

systems=(
  unprotected-batch
  feedback-off-batch
  fixed-margin-sync
  local-agreement-2
  revtrace
)
failures=0

run_cell() {
  local cell="$1"
  local seconds="$2"
  local concurrency="$3"
  local arrival="$4"
  local threshold="$5"
  local late_window="$6"
  local late_threshold="$7"
  local high_load_prompt="$8"
  local high_load_threshold="$9"
  local seed="${10}"
  local sessions="$concurrency"
  local max_new_tokens="$MAX_NEW_TOKENS_C16"
  local authority_max_new_tokens="$AUTHORITY_MAX_NEW_TOKENS_C16"
  if [[ "$concurrency" -eq 8 ]]; then
    max_new_tokens="$MAX_NEW_TOKENS_C8"
    authority_max_new_tokens="$AUTHORITY_MAX_NEW_TOKENS_C8"
  fi
  if [[ "$cell" == "B1" ]]; then
    sessions=32
  fi
  # The directory name is part of the evidence boundary: these canonical
  # trajectories include the declared-work capacity rebase used by every
  # compared system.  Never fall back to an older unversioned oracle cache.
  local oracle="$OUT/oracle-dynamic-work-target-capacity-v4/${MODEL_SLUG}-${cell}-seed${seed}.json"
  local rotation=$(((seed - 1) % ${#systems[@]}))
  local ordered_systems=(
    "${systems[@]:rotation}"
    "${systems[@]:0:rotation}"
  )
  local order_index=0
  local system
  for system in "${ordered_systems[@]}"; do
    local stem="${MODEL_SLUG}-${cell}-seed${seed}-${system}"
    local result="$OUT/${stem}.json"
    local log="$OUT/logs/${stem}.log"
    if [[ -s "$result" ]]; then
      echo "SKIP $stem"
      order_index=$((order_index + 1))
      continue
    fi
    echo "START $stem"
    extra_args=()
    if [[ "$cell" == "B1" ]]; then
      extra_args+=(--offered-concurrency 32)
    fi
    if [[ "$system" == "revtrace" \
      && "$late_window" != "none" \
      && "$late_threshold" != "none" ]]; then
      extra_args+=(
        --late-window-index "$late_window"
        --late-margin-threshold "$late_threshold"
      )
    fi
    if [[ "$system" == "revtrace" \
      && "$high_load_prompt" != "none" \
      && "$high_load_threshold" != "none" ]]; then
      extra_args+=(
        --high-load-prompt-tokens "$high_load_prompt"
        --high-load-margin-threshold "$high_load_threshold"
      )
    fi
    if [[ "$system" == "revtrace" ]]; then
      extra_args+=(
        --verifier-device cuda:1
        --verifier-lanes "$VERIFIER_LANES"
        --terminal-contract state-only
      )
    fi
    "$PY" "$RUNNER" workload \
      --model "$MODEL_PATH" \
      --model-name "$MODEL_ID" \
      --manifest "$MANIFEST" \
      --output "$result" \
      --oracle-cache "$oracle" \
      --system "$system" \
      --sessions "$sessions" \
      --duration-seconds "$seconds" \
      --window-seconds 10 \
      --concurrency "$concurrency" \
      "${extra_args[@]}" \
      --arrival "$arrival" \
      --arrival-scale-seconds 0.02 \
      --seed "$seed" \
      --system-order-index "$order_index" \
      --system-order-policy cyclic-latin-square-v1 \
      --margin-threshold "$threshold" \
      --max-new-tokens "$max_new_tokens" \
      --authority-max-new-tokens "$authority_max_new_tokens" \
      --audit-probability 0.021 \
      --slo-seconds 2.0 \
      --power-sample-seconds 0.2 \
      --proposer-device "$GPU" \
      >"$log" 2>&1
    rc="$?"
    if [[ "$rc" -eq 0 && "$system" == "revtrace" ]]; then
      "$PY" - "$result" <<'PY'
import json
import sys

row = json.load(open(sys.argv[1]))
counts = row["counts"]
assert counts["post_timing_stable_output_mismatches"] == 0
assert counts["post_timing_stable_state_mismatches"] == 0
assert counts["state_violations"] == 0
assert counts["stale_commits"] == 0
PY
      rc="$?"
    fi
    if [[ "$rc" -ne 0 ]]; then
      echo "$stem rc=$rc" | tee -a "$OUT/matrix-failures.txt"
      failures=$((failures + 1))
      if [[ "$system" == "revtrace" ]]; then
        echo "FAIL_CLOSED_STABLE_STATE_MISMATCH $stem" >&2
        exit 2
      fi
    else
      echo "DONE $stem"
    fi
    order_index=$((order_index + 1))
  done
}

for suffix in 01 02 03 04 05; do
  seed="${W5_SEED_EPOCH}${suffix}"
  run_cell W1 90 16 sync "$TAU_C16" "$LATE_W16" "$LATE_TAU16" "$LOAD_P16" "$LOAD_TAU16" "$seed"
done
for suffix in 21 22 23; do
  seed="${W5_SEED_EPOCH}${suffix}"
  run_cell W2 90 16 poisson "$TAU_C16" "$LATE_W16" "$LATE_TAU16" "$LOAD_P16" "$LOAD_TAU16" "$seed"
done
for suffix in 41 42 43 44 45; do
  seed="${W5_SEED_EPOCH}${suffix}"
  run_cell W3 180 8 sync "$TAU_C8" "$LATE_W8" "$LATE_TAU8" "$LOAD_P8" "$LOAD_TAU8" "$seed"
done
for suffix in 61 62 63; do
  seed="${W5_SEED_EPOCH}${suffix}"
  run_cell W4 180 8 poisson "$TAU_C8" "$LATE_W8" "$LATE_TAU8" "$LOAD_P8" "$LOAD_TAU8" "$seed"
done
run_cell B1 90 16 burst "$TAU_C16" "$LATE_W16" "$LATE_TAU16" "$LOAD_P16" "$LOAD_TAU16" "${W5_SEED_EPOCH}81"
run_cell B2 180 16 sync "$TAU_C16" "$LATE_W16" "$LATE_TAU16" "$LOAD_P16" "$LOAD_TAU16" "${W5_SEED_EPOCH}91"

if [[ "$failures" -ne 0 ]]; then
  echo "MATRIX_FAILED model=$MODEL_ID failures=$failures" >&2
  exit 2
fi
echo "MATRIX_COMPLETE model=$MODEL_ID"

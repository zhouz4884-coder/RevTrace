#!/usr/bin/env bash
# Complete one independent W4 contract, renewing only from adaptation failures.
set -u

if [[ "$#" -ne 10 ]]; then
  echo "usage: $0 ROOT MODEL_NAME MODEL_PATH SLUG MANIFEST OUT CONCURRENCY GPU SEED0 START_ATTEMPT" >&2
  exit 2
fi

ROOT="$1"
MODEL_NAME="$2"
MODEL_PATH="$3"
SLUG="$4"
MANIFEST="$5"
OUT="$6"
CONCURRENCY="$7"
GPU="$8"
SEED0="$9"
START_ATTEMPT="${10}"
MAX_NEW_TOKENS="${WHISPER_MAX_NEW_TOKENS:-96}"
CONTRACT_TAG=""
RESULT_TAG=""
if [[ "$MAX_NEW_TOKENS" -ne 96 ]]; then
  CONTRACT_TAG="-m${MAX_NEW_TOKENS}"
  RESULT_TAG="${CONTRACT_TAG}-workv1"
fi
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
INITIAL_POLICY="$OUT/w4-policy-long-${SLUG}-c${CONCURRENCY}${CONTRACT_TAG}.json"
CALIBRATION1="$OUT/w4-calibration-long-${SLUG}-c${CONCURRENCY}${CONTRACT_TAG}-seed20260730.json"
CALIBRATION2="$OUT/w4-calibration-long-${SLUG}-c${CONCURRENCY}${CONTRACT_TAG}-seed20260731.json"

export PYTHONPATH="$PROJ/src"
cd "$PROJ"

ensure_long_policy() {
  local calibration seed log
  for seed in 20260730 20260731; do
    calibration="$OUT/w4-calibration-long-${SLUG}-c${CONCURRENCY}${CONTRACT_TAG}-seed${seed}.json"
    log="${calibration%.json}.log"
    if [[ ! -s "$calibration" ]]; then
      CUDA_VISIBLE_DEVICES="$GPU" "$PY" "$RUNNER" calibrate \
        --model "$MODEL_PATH" \
        --model-name "$MODEL_NAME" \
        --manifest "$MANIFEST" \
        --output "$calibration" \
        --sessions 40 \
        --duration-seconds 180 \
        --window-seconds 10 \
        --concurrency "$CONCURRENCY" \
        --max-new-tokens "$MAX_NEW_TOKENS" \
        --seed "$seed" \
        --proposer-device cuda:0 >"$log" 2>&1 || return 2
    fi
  done
  if [[ ! -s "$INITIAL_POLICY" ]]; then
    "$PY" scripts/select_whisper_w_policy.py \
      --calibration "$CALIBRATION1" \
      --calibration "$CALIBRATION2" \
      --output "$INITIAL_POLICY" \
      >"${INITIAL_POLICY%.json}.log" 2>&1 || return 2
  fi
}

ensure_long_policy || exit 2

result_status() {
  "$PY" - "$1" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.is_file() or not path.stat().st_size:
    print("missing")
    raise SystemExit(0)
row = json.load(path.open())
if (
    row.get("decision") == "W4_RISK_CERTIFICATE_PASS"
    and row.get("config", {}).get("state_control_protocol")
    == "prompt-state-deferred-authority-checkpoint10-capacity-rebase-v2"
    and row.get("config", {}).get("audit_interference")
    == "shadow-canonical-no-state-mutation"
    and int(row.get("config", {}).get("duration_seconds", 0)) == 180
    and int(row["counts"]["risk_eligible_entries"]) >= 30000
    and int(row["counts"]["pre_outcome_randomized_audits"]) >= 500
    and int(row["counts"]["caught_state_errors"]) == 0
    and int(row.get("config", {}).get(
        "authority_max_new_tokens",
        row.get("config", {}).get("max_new_tokens", -1),
    )) == 96
    and (
        int(row.get("config", {}).get("max_new_tokens", -1)) == 96
        or row.get("config", {}).get("work_authority_protocol")
        == "decoder-step-saturation-extended-canonical-v1"
    )
    and (
        int(row.get("config", {}).get("max_new_tokens", -1)) == 96
        or row.get("config", {}).get("target_capacity_protocol")
        == "target-canonical-declared-work-v1"
    )
):
    print("pass")
elif int(row.get("counts", {}).get("caught_state_errors", 0)) > 0:
    print("caught")
else:
    print("invalid")
PY
}

adaptation_files=()
for prior in "$OUT"/w4-risk-"$SLUG"-c"$CONCURRENCY""$CONTRACT_TAG"-attempt*-seed*.json; do
  [[ -f "$prior" ]] || continue
  if [[ "$(result_status "$prior")" == "caught" ]]; then
    adaptation_files+=("$prior")
  fi
done
for external in "$OUT"/w4-external-root-"$SLUG"-c"$CONCURRENCY""$CONTRACT_TAG"-*.json; do
  [[ -f "$external" ]] || continue
  adaptation_files+=("$external")
done

policy="$INITIAL_POLICY"
if [[ "${#adaptation_files[@]}" -gt 0 ]]; then
  # Never overwrite a policy artifact referenced by an older certificate.
  # The root count versions each recovery epoch while every source digest is
  # still recorded inside the policy payload.
  policy="$OUT/w4-state-age-policy-${SLUG}-c${CONCURRENCY}${CONTRACT_TAG}-recovery-r${#adaptation_files[@]}.json"
  builder_args=(
    --policy "$INITIAL_POLICY"
    --calibration "$CALIBRATION1"
    --calibration "$CALIBRATION2"
    --output "$policy"
  )
  for adaptation in "${adaptation_files[@]}"; do
    builder_args+=(--adaptation-audit "$adaptation")
  done
  "$PY" scripts/build_whisper_w_state_age_policy.py \
    "${builder_args[@]}" >"${policy%.json}.log" 2>&1 || exit 2
fi

attempt="$START_ATTEMPT"
while [[ "$attempt" -le 6 ]]; do
  seed=$((SEED0 + attempt - 1))
  stem="w4-risk-${SLUG}-c${CONCURRENCY}${RESULT_TAG}-attempt${attempt}-seed${seed}"
  result="$OUT/${stem}.json"
  log="$OUT/${stem}.log"
  status="$(result_status "$result")"

  policy_fields="$("$PY" - "$policy" <<'PY'
import json
import sys
p = json.load(open(sys.argv[1]))["selected_policy"]
print(p["threshold"])
for key in (
    "late_window_index",
    "late_margin_threshold",
    "high_load_prompt_tokens",
    "high_load_margin_threshold",
):
    value = p.get(key)
    print(value if value is not None else "none")
PY
)"
  threshold="$(printf '%s\n' "$policy_fields" | sed -n '1p')"
  late_window="$(printf '%s\n' "$policy_fields" | sed -n '2p')"
  late_threshold="$(printf '%s\n' "$policy_fields" | sed -n '3p')"
  high_load_prompt="$(printf '%s\n' "$policy_fields" | sed -n '4p')"
  high_load_threshold="$(printf '%s\n' "$policy_fields" | sed -n '5p')"

  if [[ "$status" == "pass" ]]; then
    "$PY" - "$result" "$OUT" "$SLUG" "$CONCURRENCY" <<'PY'
import json
import pathlib
import sys
row = json.load(open(sys.argv[1]))
out = pathlib.Path(sys.argv[2])
slug, concurrency = sys.argv[3:5]
config = row["config"]
(out / f"w4-final-threshold-{slug}-c{concurrency}.txt").write_text(
    f"{config['margin_threshold']}\n"
)
(out / f"w4-final-late-window-{slug}-c{concurrency}.txt").write_text(
    f"{config.get('late_window_index') if config.get('late_window_index') is not None else 'none'}\n"
)
(out / f"w4-final-late-threshold-{slug}-c{concurrency}.txt").write_text(
    f"{config.get('late_margin_threshold') if config.get('late_margin_threshold') is not None else 'none'}\n"
)
(out / f"w4-final-high-load-prompt-{slug}-c{concurrency}.txt").write_text(
    f"{config.get('high_load_prompt_tokens') if config.get('high_load_prompt_tokens') is not None else 'none'}\n"
)
(out / f"w4-final-high-load-threshold-{slug}-c{concurrency}.txt").write_text(
    f"{config.get('high_load_margin_threshold') if config.get('high_load_margin_threshold') is not None else 'none'}\n"
)
PY
    echo "CONTRACT_PASS $SLUG c$CONCURRENCY existing=$result"
    exit 0
  fi
  if [[ "$status" == "invalid" ]]; then
    echo "CONTRACT_INVALID $SLUG c$CONCURRENCY result=$result" >&2
    exit 2
  fi

  late_args=()
  if [[ "$late_window" != "none" && "$late_threshold" != "none" ]]; then
    late_args+=(
      --late-window-index "$late_window"
      --late-margin-threshold "$late_threshold"
    )
  fi
  if [[ "$high_load_prompt" != "none" \
    && "$high_load_threshold" != "none" ]]; then
    late_args+=(
      --high-load-prompt-tokens "$high_load_prompt"
      --high-load-margin-threshold "$high_load_threshold"
    )
  fi
  if [[ "$status" == "missing" ]]; then
    echo "CONTRACT_START $SLUG c$CONCURRENCY attempt=$attempt seed=$seed threshold=$threshold late_window=$late_window late_threshold=$late_threshold high_load_prompt=$high_load_prompt high_load_threshold=$high_load_threshold"
    CUDA_VISIBLE_DEVICES="$GPU" "$PY" "$RUNNER" audit \
      --model "$MODEL_PATH" \
      --model-name "$MODEL_NAME" \
      --manifest "$MANIFEST" \
      --output "$result" \
      --target-risk-entries 30000 \
      --minimum-audits 500 \
      --sessions 32 \
      --duration-seconds 180 \
      --window-seconds 10 \
      --concurrency "$CONCURRENCY" \
      --max-new-tokens "$MAX_NEW_TOKENS" \
      --authority-max-new-tokens 96 \
      --margin-threshold "$threshold" \
      --policy-source "$policy" \
      "${late_args[@]}" \
      --audit-probability 0.021 \
      --seed "$seed" \
      --alpha 0.05 \
      --delta 0.005 \
      --stop-on-caught-error \
      --proposer-device cuda:0 \
      --verifier-device cuda:0 >"$log" 2>&1
    rc="$?"
    status="$(result_status "$result")"
    if [[ "$rc" -eq 0 && "$status" == "pass" ]]; then
      continue
    fi
  fi
  if [[ "$status" != "caught" ]]; then
    echo "CONTRACT_INFRA_OR_STATISTICAL_FAILURE $SLUG c$CONCURRENCY attempt=$attempt status=$status" >&2
    exit 2
  fi

  already_recorded=false
  for adaptation in "${adaptation_files[@]}"; do
    if [[ "$adaptation" == "$result" ]]; then
      already_recorded=true
      break
    fi
  done
  if [[ "$already_recorded" == false ]]; then
    adaptation_files+=("$result")
  fi
  policy="$OUT/w4-state-age-policy-${SLUG}-c${CONCURRENCY}${CONTRACT_TAG}-after-attempt${attempt}.json"
  builder_args=(
    --policy "$INITIAL_POLICY"
    --calibration "$CALIBRATION1"
    --calibration "$CALIBRATION2"
    --output "$policy"
  )
  for adaptation in "${adaptation_files[@]}"; do
    builder_args+=(--adaptation-audit "$adaptation")
  done
  "$PY" scripts/build_whisper_w_state_age_policy.py \
    "${builder_args[@]}" >"${policy%.json}.log" 2>&1 || exit 2
  attempt=$((attempt + 1))
done

echo "CONTRACT_ATTEMPTS_EXHAUSTED $SLUG c$CONCURRENCY" >&2
exit 2

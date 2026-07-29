#!/usr/bin/env bash
set -euo pipefail

root=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
project=$root/projects/revtrace
python=$root/envs/revbatch-cu128/bin/python
model=$root/models/Qwen3-ASR-0.6B
manifest=$root/datasets/revbatch/manifest.json
commit=${REVTRACE_CODE_COMMIT:-TAIL_ROBUST_WORKTREE}
result_root=results/tail_robust
log_root=logs/tail_robust

cd "$project"
mkdir -p "$result_root/c14_diagnostic" "$result_root/c12_calibration" \
  "$result_root/c12_heldout" "$result_root/c12_age_profile" "$log_root"

assert_gpu_free() {
  local minimum_free_mib=20000
  local free
  mapfile -t free < <(
    nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits
  )
  if [[ "${#free[@]}" -lt 2 ]]; then
    echo "tail closure requires two visible GPUs" >&2
    exit 4
  fi
  for value in "${free[@]:0:2}"; do
    value=${value//[[:space:]]/}
    if (( value < minimum_free_mib )); then
      echo "tail closure preflight: GPU has only ${value} MiB free; " \
        "an orphan or unrelated workload must be resolved explicitly" >&2
      nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory,process_name \
        --format=csv,noheader >&2 || true
      exit 4
    fi
  done
}

run_retained() {
  local output=$1
  local log=$2
  shift 2
  if [[ -s "$output" ]]; then
    echo "tail closure resume: keeping $output"
    return
  fi
  assert_gpu_free
  local exit_code=0
  set +e
  REVTRACE_CODE_COMMIT="$commit" PYTHONPATH=src:scripts/remote \
    "$@" > "$log" 2>&1
  exit_code=$?
  set -e
  if [[ ! -s "$output" ]]; then
    echo "tail closure failed before producing $output (exit=$exit_code)" >&2
    exit "$exit_code"
  fi
  if [[ "$exit_code" -ne 0 && "$exit_code" -ne 2 ]]; then
    echo "tail closure produced output but failed unexpectedly (exit=$exit_code)" >&2
    exit "$exit_code"
  fi
}

c14_output=$result_root/c14_diagnostic/raw.json
run_retained "$c14_output" "$log_root/c14-diagnostic.log" \
  "$python" scripts/remote/run_phase5a_live_adaptive.py \
  --model "$model" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$manifest" \
  --output "$c14_output" \
  --minimum-audits 1350 \
  --episode-seconds 30 \
  --canonical-dtype float16 \
  --canonical-batch-size 14 \
  --episode-seed-base 2026073100 \
  --statistical-risk-gate \
  --suppress-certified-terminal-proposer \
  --continue-same-contract-stages \
  --frozen-threshold steady_seed_1:0.062501 \
  --frozen-threshold steady_seed_2:0.062501 \
  --frozen-threshold steady_seed_3:0.062501 \
  --stage steady_seed_1:14:6:English \
  --stage steady_seed_2:14:6:English \
  --stage steady_seed_3:14:6:English

calibration_output=$result_root/c12_calibration/raw.json
run_retained "$calibration_output" "$log_root/c12-calibration.log" \
  "$python" scripts/remote/run_phase5a_live_adaptive.py \
  --model "$model" \
  --model-name Qwen3-ASR-0.6B \
  --data-manifest "$manifest" \
  --output "$calibration_output" \
  --minimum-audits 1350 \
  --episode-seconds 30 \
  --canonical-dtype float16 \
  --canonical-batch-size 12 \
  --episode-seed-base 2026080100 \
  --statistical-risk-gate \
  --suppress-certified-terminal-proposer \
  --stage calibration:12:8:English

threshold=$(
  "$python" -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["stages"][0]["threshold"])' \
    "$calibration_output"
)
if [[ "$threshold" == "None" || -z "$threshold" ]]; then
  echo "c12 calibration did not issue a threshold" >&2
  exit 3
fi
printf '%s\n' "$threshold" > "$result_root/c12_calibration/threshold.txt"

for seed in 1 2 3 4 5; do
  label="heldout_seed_${seed}"
  output="$result_root/c12_heldout/${label}.json"
  run_retained "$output" "$log_root/c12-${label}.log" \
    "$python" scripts/remote/run_phase5a_live_adaptive.py \
    --model "$model" \
    --model-name Qwen3-ASR-0.6B \
    --data-manifest "$manifest" \
    --output "$output" \
    --minimum-audits 1350 \
    --episode-seconds 30 \
    --canonical-dtype float16 \
    --canonical-batch-size 12 \
    --episode-seed-base "$((2026081000 + seed * 100000))" \
    --statistical-risk-gate \
    --suppress-certified-terminal-proposer \
    --frozen-threshold "${label}:${threshold}" \
    --stage "${label}:12:6:English"
done

echo "tail closure c14 diagnostic, c12 calibration, and five held-out runs complete"

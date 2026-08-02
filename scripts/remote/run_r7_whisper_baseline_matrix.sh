#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT_ROOT="${REVTRACE_PROJECT_ROOT:-${DATA_ROOT}/projects/revtrace_r7_0849660}"
PYTHON_BIN="${REVTRACE_PYTHON:-${DATA_ROOT}/envs/streamtxn-cu128/bin/python}"
PREFLIGHT_ROOT="${DATA_ROOT}/results/revtrace/r7_efsc/whisper_base_preflight"
OUTPUT_ROOT="${DATA_ROOT}/results/revtrace/r7_efsc/whisper_base_matrix"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/r7_efsc/whisper_base_matrix"
MODEL="${DATA_ROOT}/models/whisper-base.en"
MANIFEST="${DATA_ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
RUNNER="${PROJECT_ROOT}/scripts/remote/run_whisper_w_system.py"
ENTER_MARGIN=0.10546875
EXIT_MARGIN=0.484375

mkdir -p "${OUTPUT_ROOT}" "${LOG_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}/src"
export REVTRACE_CODE_COMMIT="$(tr -d '\r\n' < "${PROJECT_ROOT}/CODE_COMMIT")"

systems=(
  unprotected-batch
  feedback-off-batch
  fixed-margin-sync
  revtrace
  holdback-only
  efsc
)
seeds_w1=(2026080501 2026080502 2026080503 2026080504 2026080505)
seeds_w2=(2026080601 2026080602 2026080603 2026080604 2026080605)

run_cell() {
  local cell="$1"
  local arrival="$2"
  local seed="$3"
  local seed_index="$4"
  local rotation=$((seed_index % ${#systems[@]}))
  local ordered=("${systems[@]:rotation}" "${systems[@]:0:rotation}")
  local extra_arrival=()
  if [[ "${arrival}" == "poisson" ]]; then
    extra_arrival=(
      --arrival-scale-seconds 0.02
      --batch-coalesce-seconds 0.5
    )
  fi
  local system
  for system in "${ordered[@]}"; do
    local result="${OUTPUT_ROOT}/${cell}-seed${seed}-${system}.json"
    local log="${LOG_ROOT}/${cell}-seed${seed}-${system}.log"
    if [[ -s "${result}" ]]; then
      continue
    fi
    local extra_system=()
    if [[ "${system}" == "efsc" ]]; then
      extra_system=(--efsc-exit-margin "${EXIT_MARGIN}")
    elif [[ "${system}" == "revtrace" ]]; then
      extra_system=(--low-margin-policy verify --verifier-lanes 1)
    fi
    "${PYTHON_BIN}" "${RUNNER}" workload \
      --model "${MODEL}" --model-name whisper-base.en \
      --manifest "${MANIFEST}" --output "${result}" \
      --oracle-cache "${PREFLIGHT_ROOT}/oracle/${cell}-seed${seed}.json" \
      --sessions 16 --duration-seconds 90 --window-seconds 10 \
      --concurrency 16 --arrival "${arrival}" "${extra_arrival[@]}" \
      --seed "${seed}" --max-new-tokens 96 \
      --authority-max-new-tokens 96 --terminal-contract state-only \
      --slo-seconds 1.9 --system "${system}" \
      --proposer-device cuda:0 --verifier-device cuda:1 \
      --margin-threshold "${ENTER_MARGIN}" "${extra_system[@]}" \
      >"${log}" 2>&1
  done
}

for index in "${!seeds_w1[@]}"; do
  run_cell w1 sync "${seeds_w1[$index]}" "${index}"
done
for index in "${!seeds_w2[@]}"; do
  run_cell w2 poisson "${seeds_w2[$index]}" "$((index + 2))"
done

"${PYTHON_BIN}" - "${OUTPUT_ROOT}" <<'PY'
import json
import pathlib
import statistics
import sys

root = pathlib.Path(sys.argv[1])
systems = (
    "unprotected-batch", "feedback-off-batch", "fixed-margin-sync",
    "revtrace", "holdback-only", "efsc",
)
summary = {"schema_version": 1, "study": "R7.3 Whisper c16 baseline matrix", "cells": {}}
for cell in ("w1", "w2"):
    summary["cells"][cell] = {}
    for system in systems:
        rows = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(root.glob(f"{cell}-seed*-{system}.json"))
        ]
        metrics = [row["metrics"] for row in rows]
        counts = [row["counts"] for row in rows]
        summary["cells"][cell][system] = {
            "replicates": len(rows),
            "median_wall_speedup": statistics.median(row["wall_speedup"] for row in metrics),
            "median_display_slo_goodput_speedup": statistics.median(row["display_slo_goodput_speedup"] for row in metrics),
            "maximum_display_p99_seconds": max(row["display_latency_p99"] for row in metrics),
            "maximum_feedback_resolution_p99_seconds": max(row["feedback_resolution_latency_p99"] for row in metrics),
            "minimum_energy_reduction": min(row["energy_reduction"] for row in metrics),
            "state_violations": sum(row["state_violations"] for row in counts),
            "output_violations": sum(row["output_violations"] for row in counts),
        }
summary["decision"] = "COMPLETE_R7_3_BASELINE_MATRIX"
summary["claim_boundary"] = "state/output violations are oracle diagnostics; only EFSC semantic violations are contract violations"
(root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, sort_keys=True))
PY

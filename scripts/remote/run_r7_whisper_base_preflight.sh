#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT_ROOT="${REVTRACE_PROJECT_ROOT:-${DATA_ROOT}/projects/revtrace_r7_0849660}"
PYTHON_BIN="${REVTRACE_PYTHON:-${DATA_ROOT}/envs/streamtxn-cu128/bin/python}"
OUTPUT_ROOT="${REVTRACE_OUTPUT_ROOT:-${DATA_ROOT}/results/revtrace/r7_efsc/whisper_base_preflight}"
LOG_ROOT="${REVTRACE_LOG_ROOT:-${DATA_ROOT}/logs/revtrace/r7_efsc/whisper_base_preflight}"
MODEL="${DATA_ROOT}/models/whisper-base.en"
MANIFEST="${DATA_ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
RUNNER="${PROJECT_ROOT}/scripts/remote/run_whisper_w_system.py"
POLICY="${OUTPUT_ROOT}/frozen_policy.json"

mkdir -p "${OUTPUT_ROOT}/w1" "${OUTPUT_ROOT}/w2" \
  "${OUTPUT_ROOT}/oracle" "${LOG_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}/src"
export REVTRACE_CODE_COMMIT="$(tr -d '\r\n' < "${PROJECT_ROOT}/CODE_COMMIT")"

"${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/finalize_r7_whisper_policy.py" \
  --model-name whisper-base.en \
  --calibration "${DATA_ROOT}/results/revtrace/whisper_w0_w7/w4-calibration-long-base-c16-seed20260730.json" \
  --adaptation "${DATA_ROOT}/results/revtrace/whisper_w0_w7/w1-calibration-final-base-c16-seed20260731.json" \
  --output "${POLICY}" >"${LOG_ROOT}/policy.log" 2>&1

readarray -t THRESHOLDS < <("${PYTHON_BIN}" - "${POLICY}" <<'PY'
import json, sys
p = json.load(open(sys.argv[1], encoding="utf-8"))["selected_policy"]
print(p["enter_margin"])
print(p["exit_margin"])
PY
)
ENTER_MARGIN="${THRESHOLDS[0]}"
EXIT_MARGIN="${THRESHOLDS[1]}"

run_cell() {
  local arrival="$1"
  local seed="$2"
  local cell="$3"
  local extra=()
  if [[ "${arrival}" == "poisson" ]]; then
    extra=(
      --arrival-scale-seconds 0.02
      --batch-coalesce-seconds 0.5
    )
  fi
  "${PYTHON_BIN}" "${RUNNER}" workload \
    --model "${MODEL}" --model-name whisper-base.en \
    --manifest "${MANIFEST}" \
    --output "${OUTPUT_ROOT}/${cell}/seed${seed}.json" \
    --oracle-cache "${OUTPUT_ROOT}/oracle/${cell}-seed${seed}.json" \
    --sessions 16 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --arrival "${arrival}" "${extra[@]}" \
    --seed "${seed}" --max-new-tokens 96 \
    --authority-max-new-tokens 96 --terminal-contract state-only \
    --slo-seconds 1.9 --system efsc --proposer-device cuda:0 \
    --verifier-device cuda:1 --margin-threshold "${ENTER_MARGIN}" \
    --efsc-exit-margin "${EXIT_MARGIN}" \
    >"${LOG_ROOT}/${cell}-seed${seed}.log" 2>&1
}

for seed in 2026080501 2026080502 2026080503 2026080504 2026080505; do
  run_cell sync "${seed}" w1
done
for seed in 2026080601 2026080602 2026080603 2026080604 2026080605; do
  run_cell poisson "${seed}" w2
done

"${PYTHON_BIN}" - "${OUTPUT_ROOT}" <<'PY'
import json
import pathlib
import statistics
import sys

root = pathlib.Path(sys.argv[1])
cells = {}
for name in ("w1", "w2"):
    payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / name).glob("seed*.json"))
    ]
    metrics = [row["metrics"] for row in payloads]
    schedulers = [row["scheduler"] for row in payloads]
    counts = [row["counts"] for row in payloads]
    cells[name] = {
        "replicates": len(payloads),
        "median_wall_speedup": statistics.median(row["wall_speedup"] for row in metrics),
        "median_gpu_normalized_speedup": statistics.median(row["gpu_normalized_speedup"] for row in metrics),
        "maximum_display_p99_seconds": max(row["display_latency_p99"] for row in metrics),
        "maximum_committed_state_p99_seconds": max(row["latency_p99"] for row in metrics),
        "maximum_feedback_resolution_p99_seconds": max(row["feedback_resolution_latency_p99"] for row in metrics),
        "minimum_energy_reduction": min(row["energy_reduction"] for row in metrics),
        "minimum_occupancy_fraction": min(row["mean_occupancy_fraction"] for row in schedulers),
        "pending_critical_path_authorities": max(row["maximum_pending_authorities"] for row in schedulers),
        "semantic_violations": sum(
            sum(row["efsc_semantic_violations"].values()) for row in counts
        ),
        "maximum_prompt_state_age": max(row["efsc_maximum_ancestry_age"] for row in metrics),
        "maximum_feedback_debt": max(row["efsc_maximum_feedback_debt"] for row in metrics),
    }
    gates = {
        "wall_speedup": cells[name]["median_wall_speedup"] >= 2.5,
        "display_p99": cells[name]["maximum_display_p99_seconds"] <= 1.9,
        "committed_state_p99": cells[name]["maximum_committed_state_p99_seconds"] <= 1.9,
        "energy": cells[name]["minimum_energy_reduction"] >= 0.35,
        "occupancy": cells[name]["minimum_occupancy_fraction"] >= 0.90,
        "authority": cells[name]["pending_critical_path_authorities"] == 0,
        "semantics": cells[name]["semantic_violations"] == 0,
    }
    cells[name]["gates"] = gates
    cells[name]["passed"] = all(gates.values())

summary = {
    "schema_version": 1,
    "study": "RevTrace R7.3 Whisper base.en c16 EFSC death gate",
    "decision": (
        "PASS_R7_3_EFSC_PREFLIGHT"
        if all(row["passed"] for row in cells.values())
        else "FAIL_R7_3_EFSC_PREFLIGHT"
    ),
    "cells": cells,
    "claim_boundary": "one-GPU authority-free steady-state serving; embedded singleton baseline is paired per seed",
}
(root / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(summary, sort_keys=True))
PY

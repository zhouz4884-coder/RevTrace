#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT_ROOT="${REVTRACE_PROJECT_ROOT:-${DATA_ROOT}/projects/revtrace_r10_cross}"
PYTHON_BIN="${REVTRACE_PYTHON:-${DATA_ROOT}/envs/revbatch-cu128/bin/python}"
OUTPUT_ROOT="${REVTRACE_OUTPUT_ROOT:-${DATA_ROOT}/results/revtrace/r10_qwen_cross_adapter}"
LOG_ROOT="${REVTRACE_LOG_ROOT:-${DATA_ROOT}/logs/revtrace/r10_qwen_cross_adapter}"
MANIFEST="${DATA_ROOT}/datasets/revbatch/manifest.json"

mkdir -p "${OUTPUT_ROOT}" "${LOG_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export REVTRACE_CODE_COMMIT="$(tr -d '\r\n' < "${PROJECT_ROOT}/CODE_COMMIT")"

run_one() {
  local model="$1"
  local short="$2"
  local mode="$3"
  local output="${OUTPUT_ROOT}/${short}-${mode}.json"
  "${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/remote/run_qwen_dgft_cross_adapter.py" \
    --model "${DATA_ROOT}/models/${model}" \
    --model-name "${model}" \
    --data-manifest "${MANIFEST}" \
    --output "${output}" \
    --mode "${mode}" \
    --duration-seconds 30 \
    --concurrency 16 \
    --fine-window-seconds 2 \
    --windows-per-segment 3 \
    --forward-threshold 0.20 \
    --reverse-ceiling 0.20 \
    --risk-margin 0.05 \
    --proposer-gpu 0 \
    --authority-gpu 1 \
    >"${LOG_ROOT}/${short}-${mode}.log" 2>&1 || true
}

run_one Qwen3-ASR-0.6B qwen06 dgft
run_one Qwen3-ASR-0.6B qwen06 hybrid
run_one Qwen3-ASR-1.7B qwen17 dgft
run_one Qwen3-ASR-1.7B qwen17 hybrid

"${PYTHON_BIN}" - "${OUTPUT_ROOT}" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for path in sorted(root.glob("qwen*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload["summary"]
    rows.append({
        "file": path.name,
        "model": payload["model"],
        "mode": payload["mode"],
        "decision": payload["decision"],
        "wall_speedup": summary["deployed_wall_speedup"],
        "gpu_normalized_speedup": summary["gpu_normalized_speedup"],
        "energy_reduction_fraction": summary["energy_reduction_fraction"],
        "final_unit_edit_rate_median": summary["final_unit_edit_rate_median"],
        "final_unit_edit_rate_p95": summary["final_unit_edit_rate_p95"],
        "fine_replay_fraction": summary["fine_replay_fraction"],
        "transaction_install_violations": summary["transaction_install_violations"],
    })
summary = {
    "schema_version": 1,
    "study": "R10 Qwen cross-adapter matrix",
    "complete": len(rows) == 4,
    "rows": rows,
}
(root / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(summary, sort_keys=True))
PY

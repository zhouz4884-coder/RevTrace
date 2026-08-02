#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT_ROOT="${REVTRACE_PROJECT_ROOT:-${DATA_ROOT}/projects/revtrace_r7_0849660}"
PYTHON_BIN="${REVTRACE_PYTHON:-${DATA_ROOT}/envs/revbatch-cu128/bin/python}"
OUTPUT_ROOT="${REVTRACE_OUTPUT_ROOT:-${DATA_ROOT}/results/revtrace/r7_efsc/qwen_q0_formal}"
LOG_ROOT="${REVTRACE_LOG_ROOT:-${DATA_ROOT}/logs/revtrace/r7_efsc/qwen_q0_formal}"
MANIFEST="${DATA_ROOT}/datasets/revbatch/manifest.json"
ROOTS="${PROJECT_ROOT}/results/phase2/risk_v1/all_caught_errors.csv"

mkdir -p "${OUTPUT_ROOT}" "${LOG_ROOT}"
export REVTRACE_CODE_COMMIT="$(tr -d '\r\n' < "${PROJECT_ROOT}/CODE_COMMIT")"

run_one() {
  local model_id="$1"
  local model_name="$2"
  local enter_margin="$3"
  local exit_margin="$4"
  local seed="$5"
  local tag="$6"
  "${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/remote/run_r7_qwen_efsc.py" \
    --model "${DATA_ROOT}/models/${model_id}" \
    --model-name "${model_name}" \
    --data-manifest "${MANIFEST}" \
    --known-roots "${ROOTS}" \
    --output "${OUTPUT_ROOT}/${tag}-seed${seed}.json" \
    --target-events 1200 \
    --concurrency 16 \
    --duration-seconds 30 \
    --seed "${seed}" \
    --gpu 0 \
    --enter-margin "${enter_margin}" \
    --exit-margin "${exit_margin}" \
    >"${LOG_ROOT}/${tag}-seed${seed}.log" 2>&1
}

run_one Qwen3-ASR-0.6B Qwen3-ASR-0.6B 0.078125 6.03124999301508 2026080221 qwen06
run_one Qwen3-ASR-1.7B Qwen3-ASR-1.7B 0.0625 7.06249977956759 2026080231 qwen17

"${PYTHON_BIN}" - "${OUTPUT_ROOT}" <<'PY'
import json
import pathlib
import statistics
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for path in sorted(root.glob("qwen*-seed*.json")):
    payload = json.loads(path.read_text(encoding="utf-8"))
    performance = payload["performance"]
    rows.append({
        "path": path.name,
        "model": payload["model"],
        "decision": payload["decision"],
        "wall_seconds": performance["episode_median_wall_seconds_first_five"],
        "latency_p99_seconds": performance["episode_median_p99_seconds_first_five"],
        "events_per_second": statistics.median(
            episode["goodput_events_per_second"]
            for episode in performance["first_five_episodes"]
        ),
        "joules_per_audio_second": performance["energy"]["joules_per_audio_second"],
        "semantic_violations": sum(payload["semantic_contract"]["violations"].values()),
    })

models = {}
for model in sorted({row["model"] for row in rows}):
    selected = [row for row in rows if row["model"] == model]
    models[model] = {
        "replicates": sum(
            len(json.loads((root / row["path"]).read_text(encoding="utf-8"))["performance"]["first_five_episodes"])
            for row in selected
        ),
        "all_pass": all(row["decision"] == "PASS_R7_Q0_LIVE_MODEL" for row in selected),
        "median_wall_seconds": statistics.median(row["wall_seconds"] for row in selected),
        "median_latency_p99_seconds": statistics.median(row["latency_p99_seconds"] for row in selected),
        "median_events_per_second": statistics.median(row["events_per_second"] for row in selected),
        "median_joules_per_audio_second": statistics.median(row["joules_per_audio_second"] for row in selected),
        "semantic_violations": sum(row["semantic_violations"] for row in selected),
    }

summary = {
    "schema_version": 1,
    "study": "RevTrace R7.Q0 five-seed isolated-host performance gate",
    "resource_protocol": "one model at a time; GPU0 active; GPU1 and competing model idle",
    "models": models,
    "replicates": rows,
}
(root / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(summary["models"], sort_keys=True))
PY

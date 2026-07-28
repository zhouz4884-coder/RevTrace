#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
ENV_ROOT="${DATA_ROOT}/envs/llm42-phase7"
PROJECT_ROOT="${DATA_ROOT}/projects/revtrace"
MODEL="${DATA_ROOT}/models/Qwen2.5-0.5B-Instruct"
OUTPUT_ROOT="${PROJECT_ROOT}/results/phase7/source_probes"
PORT="${LLM42_PORT:-30017}"

mkdir -p "${OUTPUT_ROOT}"
SERVER_LOG="${OUTPUT_ROOT}/llm42-text-server.log"
CLIENT_JSON="${OUTPUT_ROOT}/llm42-text-source-smoke.json"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

CUDA_VISIBLE_DEVICES=0 "${ENV_ROOT}/bin/python" -m sglang.launch_server \
  --model-path "${MODEL}" \
  --host 127.0.0.1 \
  --port "${PORT}" \
  --tp 1 \
  --enable-llm42 3 \
  --llm42-window-size 8 \
  --llm42-verify-batch-size 4 \
  --attention-backend triton \
  --disable-radix-cache \
  --disable-chunked-prefix-cache \
  --disable-overlap-schedule \
  --chunked-prefill-size -1 \
  --random-seed 42 \
  --mem-fraction-static 0.7 \
  >"${SERVER_LOG}" 2>&1 &
SERVER_PID=$!

ready=0
for _ in $(seq 1 120); do
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    break
  fi
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "${ready}" != "1" ]]; then
  echo "LLM-42 server failed to become ready" >&2
  tail -120 "${SERVER_LOG}" >&2
  exit 2
fi

"${ENV_ROOT}/bin/python" - "${PORT}" "${MODEL}" "${CLIENT_JSON}" <<'PY'
import concurrent.futures
import json
import sys
import time
import urllib.request
from pathlib import Path

port, model, output = int(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
url = f"http://127.0.0.1:{port}/generate"
payload = {
    "text": "Explain in one sentence why deterministic inference matters.",
    "sampling_params": {
        "temperature": 0,
        "max_new_tokens": 24,
        "is_deterministic": True,
    },
}

def request_once(_):
    body = json.dumps(payload).encode()
    started = time.perf_counter()
    with urllib.request.urlopen(
        urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        ),
        timeout=180,
    ) as response:
        value = json.loads(response.read())
    return value, time.perf_counter() - started

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    first = list(pool.map(request_once, range(8)))
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    second = list(pool.map(request_once, range(8)))
texts_first = [item[0].get("text") for item in first]
texts_second = [item[0].get("text") for item in second]
result = {
    "schema_version": 1,
    "study": "Original LLM-42 source text-model smoke",
    "model": model,
    "requests_per_round": 8,
    "rounds": 2,
    "all_outputs_identical": len(set(texts_first + texts_second)) == 1,
    "cross_round_pair_exact": texts_first == texts_second,
    "latency_seconds": [item[1] for item in first + second],
    "outputs": texts_first + texts_second,
    "scope": (
        "original public LLM-42 text path; not a direct Qwen3-ASR run and "
        "not used as an ASR throughput result"
    ),
}
output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, sort_keys=True))
PY

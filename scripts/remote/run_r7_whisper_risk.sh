#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJECT_ROOT="${REVTRACE_PROJECT_ROOT:-${DATA_ROOT}/projects/revtrace_r7_0849660}"
PYTHON_BIN="${REVTRACE_PYTHON:-${DATA_ROOT}/envs/streamtxn-cu128/bin/python}"
OUTPUT_ROOT="${DATA_ROOT}/results/revtrace/r7_efsc/whisper_base_risk"
LOG_ROOT="${DATA_ROOT}/logs/revtrace/r7_efsc/whisper_base_risk"

mkdir -p "${OUTPUT_ROOT}" "${LOG_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}/src:${PROJECT_ROOT}/scripts/remote"
export REVTRACE_CODE_COMMIT="$(tr -d '\r\n' < "${PROJECT_ROOT}/CODE_COMMIT")"

run_shard() {
  local shard="$1"
  local seed="$2"
  local device="$3"
  "${PYTHON_BIN}" "${PROJECT_ROOT}/scripts/remote/run_r7_whisper_risk.py" \
    --model "${DATA_ROOT}/models/whisper-base.en" \
    --model-name whisper-base.en \
    --manifest "${DATA_ROOT}/datasets/revtrace/librispeech/phase4b-test-clean-full.json" \
    --policy "${DATA_ROOT}/results/revtrace/r7_efsc/whisper_base_preflight/frozen_policy.json" \
    --output "${OUTPUT_ROOT}/sentinel-shard${shard}.json" \
    --sessions 32 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --target-eligible 30000 --minimum-audits 600 \
    --sentinel-probability 0.021 --alpha 0.05 --delta 0.005 \
    --seed "${seed}" --max-new-tokens 96 \
    --proposer-device "${device}" --verifier-device "${device}" \
    >"${LOG_ROOT}/sentinel-shard${shard}.log" 2>&1
}

run_shard 0 2026080801 cuda:0 & p0=$!
run_shard 1 2026080802 cuda:1 & p1=$!
wait "${p0}"
wait "${p1}"

"${PYTHON_BIN}" - "${OUTPUT_ROOT}" <<'PY'
import hashlib
import json
import pathlib
import sys

from revtrace.risk import AuditRiskBound

root = pathlib.Path(sys.argv[1])
paths = [root / "sentinel-shard0.json", root / "sentinel-shard1.json"]
rows = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
eligible = sum(row["counts"]["eligible_fast_commits"] for row in rows)
audits = sum(row["counts"]["random_sentinel_audits"] for row in rows)
caught = sum(row["counts"]["caught_state_errors"] for row in rows)
violations = sum(row["counts"]["semantic_violations"] for row in rows)
bound = AuditRiskBound(0.021, 0.05)
upper_count = bound.upper_error_count(eligible, caught)
upper_risk = upper_count / eligible
passed = eligible >= 60000 and audits >= 1200 and upper_risk <= 0.005 and violations == 0
payload = {
    "schema_version": 1,
    "study": "RevTrace R7.4 pooled two-GPU epoch-fenced sentinel audit",
    "decision": "PASS_R7_4_RISK" if passed else "FAIL_R7_4_RISK",
    "model": "whisper-base.en",
    "counts": {
        "risk_eligible_entries": eligible,
        "pre_outcome_random_audits": audits,
        "caught_state_errors": caught,
        "semantic_violations": violations,
    },
    "risk_certificate": {
        "upper_error_count": upper_count,
        "upper_risk": upper_risk,
        "confidence": 0.95,
        "target_delta": 0.005,
        "method": "fixed-probability mixture e-process inversion",
    },
    "shards": [
        {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "decision": row["decision"],
            "counts": row["counts"],
        }
        for path, row in zip(paths, rows)
    ],
    "claim_boundary": (
        "the two independent GPU streams share one frozen model-policy epoch; "
        "the pooled certificate covers correlated eligible events, not utterances"
    ),
}
(root / "sentinel-60k.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(payload, sort_keys=True))
raise SystemExit(0 if passed else 2)
PY

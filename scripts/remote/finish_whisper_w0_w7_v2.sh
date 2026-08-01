#!/usr/bin/env bash
# Re-run W2-W7 under the deferred state/final-output authority v2 contract.
set -u

if [[ "$#" -ne 7 ]]; then
  echo "usage: $0 ROOT BASE_MODEL SMALL_MODEL MANIFEST TINY_PAIRS BASE_PAIRS OUT" >&2
  exit 2
fi

ROOT="$1"
BASE_MODEL="$2"
SMALL_MODEL="$3"
MANIFEST="$4"
TINY_PAIRS="$5"
BASE_PAIRS="$6"
OUT="$7"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
W3="$PROJ/scripts/remote/run_whisper_w3_parallel.sh"
W4="$PROJ/scripts/remote/run_whisper_w4_contract.sh"
W5="$PROJ/scripts/remote/run_whisper_w5_parallel.sh"
W6="$PROJ/scripts/remote/run_whisper_w6_parallel.sh"
W7="$PROJ/scripts/remote/run_whisper_w7_finalize.sh"
ARCHIVE="$OUT/excluded/state-contract-v1"

export PYTHONPATH="$PROJ/src"
mkdir -p "$OUT" "$OUT/logs" "$OUT/oracle" "$ARCHIVE"

archive_glob() {
  local destination="$1"
  shift
  local pattern path
  mkdir -p "$destination"
  for pattern in "$@"; do
    for path in $pattern; do
      [[ -e "$path" ]] || continue
      mv "$path" "$destination/"
    done
  done
}

echo "ARCHIVE state-contract-v1"
archive_glob "$ARCHIVE" \
  "$OUT/w2-known-pairs-v4.json" \
  "$OUT/w3-mechanism-*.json" "$OUT/w3-mechanism-*.log" \
  "$OUT/w4-calibration-long-*" "$OUT/w4-policy-long-*" \
  "$OUT/w4-risk-*" "$OUT/w4-state-age-policy-*" \
  "$OUT/w4-external-root-*" "$OUT/w4-final-*" \
  "$OUT/base-W*.json" "$OUT/base-B*.json" \
  "$OUT/small-W*.json" "$OUT/small-B*.json" \
  "$OUT/w5-preflight-base.json" "$OUT/w5-preflight-base.log" \
  "$OUT/w5-matrix-base.log" "$OUT/w5-matrix-small.log" \
  "$OUT/w6-quality-base.json" "$OUT/w6-quality-small.json" \
  "$OUT/w6-quality-base.log" "$OUT/w6-quality-small.log" \
  "$OUT/w7-summary.json" "$OUT/w7-report.md" \
  "$OUT/paper-evidence-summary.json"
archive_glob "$ARCHIVE/markers" \
  "$OUT/.w3-mechanism-complete" "$OUT/.w3-mechanism-failed" \
  "$OUT/.risk-audits-complete" "$OUT/.risk-audits-failed" \
  "$OUT/.w5-matrix-complete" "$OUT/.w5-matrix-failed" \
  "$OUT/.w5-preflight-pass" "$OUT/.w5-preflight-failed" \
  "$OUT/.w6-quality-complete" "$OUT/.w6-quality-failed" \
  "$OUT/.w6-blocked" "$OUT/.w7-finalized"

echo "START W2 known-pair authority regression"
"$PY" "$PROJ/scripts/validate_whisper_w_known_pairs.py" \
  --tiny-pairs "$TINY_PAIRS" \
  --base-pairs "$BASE_PAIRS" \
  --output "$OUT/w2-known-pairs-v4.json" \
  >"$OUT/w2-known-pairs-v4.log" 2>&1
w2_rc="$?"

echo "START W4 deferred-authority risk contracts"
(
  WHISPER_MAX_NEW_TOKENS=96 bash "$W4" \
    "$ROOT" whisper-base.en "$BASE_MODEL" base "$MANIFEST" "$OUT" \
    16 0 20272033 1
  rc1="$?"
  WHISPER_MAX_NEW_TOKENS=80 bash "$W4" \
    "$ROOT" whisper-base.en "$BASE_MODEL" base "$MANIFEST" "$OUT" \
    8 0 20272034 1
  rc2="$?"
  [[ "$rc1" -eq 0 && "$rc2" -eq 0 ]]
) >"$OUT/w4-v2-base-master.log" 2>&1 &
base_w4_pid="$!"
(
  WHISPER_MAX_NEW_TOKENS=80 bash "$W4" \
    "$ROOT" whisper-small.en "$SMALL_MODEL" small "$MANIFEST" "$OUT" \
    16 1 20272133 1
  rc1="$?"
  WHISPER_MAX_NEW_TOKENS=80 bash "$W4" \
    "$ROOT" whisper-small.en "$SMALL_MODEL" small "$MANIFEST" "$OUT" \
    8 1 20272134 1
  rc2="$?"
  [[ "$rc1" -eq 0 && "$rc2" -eq 0 ]]
) >"$OUT/w4-v2-small-master.log" 2>&1 &
small_w4_pid="$!"
wait "$base_w4_pid"
base_w4_rc="$?"
wait "$small_w4_pid"
small_w4_rc="$?"
if [[ "$base_w4_rc" -eq 0 && "$small_w4_rc" -eq 0 ]]; then
  touch "$OUT/.risk-audits-complete"
  w4_rc=0
else
  touch "$OUT/.risk-audits-failed"
  w4_rc=2
fi

echo "START W3 mechanism"
if [[ "$w4_rc" -eq 0 ]]; then
  bash "$W3" \
    "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
    >"$OUT/w3-v2-master.log" 2>&1
  w3_rc="$?"
else
  w3_rc=2
fi

echo "START W5 deployed system matrix"
if [[ "$w2_rc" -eq 0 && "$w3_rc" -eq 0 && "$w4_rc" -eq 0 ]]; then
  W5_SEED_EPOCH=202722 \
  W5_BASE_C16_MAX_NEW_TOKENS=96 \
  W5_BASE_C8_MAX_NEW_TOKENS=80 \
  W5_SMALL_C16_MAX_NEW_TOKENS=80 \
  W5_SMALL_C8_MAX_NEW_TOKENS=80 \
  bash "$W5" \
    "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
    >"$OUT/w5-v2-master.log" 2>&1
  w5_rc="$?"
else
  w5_rc=2
fi

echo "START W6 paired quality and UX"
if [[ "$w5_rc" -eq 0 ]]; then
  W6_BASE_MAX_NEW_TOKENS=96 \
  W6_SMALL_MAX_NEW_TOKENS=80 \
  bash "$W6" \
    "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
    >"$OUT/w6-v2-master.log" 2>&1
  w6_rc="$?"
else
  w6_rc=2
fi

echo "START W7 finalization"
bash "$W7" "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$OUT" \
  >"$OUT/w7-v2-master.log" 2>&1
w7_rc="$?"

"$PY" - "$OUT" "$w2_rc" "$w3_rc" "$w4_rc" "$w5_rc" "$w6_rc" "$w7_rc" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
keys = ("w2_rc", "w3_rc", "w4_rc", "w5_rc", "w6_rc", "w7_rc")
payload = dict(zip(keys, map(int, sys.argv[2:])))
(out / "state-contract-v2-pipeline-status.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
touch "$OUT/.state-contract-v2-pipeline-finished"

if [[ "$w2_rc" -ne 0 || "$w3_rc" -ne 0 || "$w4_rc" -ne 0 \
  || "$w5_rc" -ne 0 || "$w6_rc" -ne 0 || "$w7_rc" -ne 0 ]]; then
  exit 2
fi
exit 0

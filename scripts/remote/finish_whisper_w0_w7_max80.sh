#!/usr/bin/env bash
# Finish the renewed max80 Whisper W4-W7 protocol without mixing old epochs.
set -u

if [[ "$#" -ne 5 ]]; then
  echo "usage: $0 ROOT BASE_MODEL SMALL_MODEL MANIFEST OUT" >&2
  exit 2
fi

ROOT="$1"
BASE_MODEL="$2"
SMALL_MODEL="$3"
MANIFEST="$4"
OUT="$5"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
W4="$PROJ/scripts/remote/run_whisper_w4_contract.sh"
W5="$PROJ/scripts/remote/run_whisper_w5_parallel.sh"
W6="$PROJ/scripts/remote/run_whisper_w6_parallel.sh"
W7="$PROJ/scripts/remote/run_whisper_w7_finalize.sh"
ARCHIVE="$OUT/excluded/w5-pre-max80-contract-epoch"

export PYTHONPATH="$PROJ/src"
mkdir -p "$OUT" "$ARCHIVE/logs" "$ARCHIVE/oracle" "$ARCHIVE/markers"

has_contract() {
  local slug="$1"
  local concurrency="$2"
  local max_new_tokens="$3"
  "$PY" - "$OUT" "$slug" "$concurrency" "$max_new_tokens" <<'PY'
import glob
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
slug, concurrency, max_new_tokens = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
paths = glob.glob(str(out / f"w4-risk-{slug}-c{concurrency}-m{max_new_tokens}-attempt*-seed*.json"))
valid = []
for raw in paths:
    try:
        row = json.load(open(raw))
    except Exception:
        continue
    config = row.get("config", {})
    counts = row.get("counts", {})
    if (
        row.get("decision") == "W4_RISK_CERTIFICATE_PASS"
        and int(config.get("max_new_tokens", -1)) == max_new_tokens
        and int(config.get("concurrency", -1)) == concurrency
        and int(counts.get("risk_eligible_entries", 0)) >= 30000
        and int(counts.get("pre_outcome_randomized_audits", 0)) >= 500
        and int(counts.get("caught_state_errors", -1)) == 0
    ):
        valid.append(raw)
print(len(valid))
raise SystemExit(0 if valid else 1)
PY
}

echo "WAIT small-c16-m80"
until has_contract small 16 80 >/dev/null 2>&1; do
  sleep 30
done

echo "START small-c8-m80"
WHISPER_MAX_NEW_TOKENS=80 bash "$W4" \
  "$ROOT" whisper-small.en "$SMALL_MODEL" small "$MANIFEST" "$OUT" \
  8 1 20270933 1 >"$OUT/w4-small-c8-m80.log" 2>&1
small_c8_rc="$?"

echo "WAIT base-c8-m80"
base_waits=0
until has_contract base 8 80 >/dev/null 2>&1; do
  base_waits=$((base_waits + 1))
  if [[ "$base_waits" -gt 240 ]]; then
    echo "base-c8-m80 contract timeout" >&2
    break
  fi
  sleep 30
done

if [[ "$small_c8_rc" -ne 0 ]] \
  || ! has_contract small 16 80 >/dev/null 2>&1 \
  || ! has_contract small 8 80 >/dev/null 2>&1 \
  || ! has_contract base 8 80 >/dev/null 2>&1; then
  echo "MAX80_W4_INCOMPLETE" >&2
  touch "$OUT/.max80-w4-incomplete"
  exit 2
fi
touch "$OUT/.max80-w4-complete"

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

archive_glob "$ARCHIVE" \
  "$OUT/base-W*.json" "$OUT/base-B*.json" \
  "$OUT/small-W*.json" "$OUT/small-B*.json" \
  "$OUT/w5-preflight-base.json" \
  "$OUT/w6-quality-base.json" "$OUT/w6-quality-small.json" \
  "$OUT/w7-summary.json" "$OUT/paper-evidence-summary.json"
archive_glob "$ARCHIVE/logs" \
  "$OUT/logs/base-W*.log" "$OUT/logs/base-B*.log" \
  "$OUT/logs/small-W*.log" "$OUT/logs/small-B*.log" \
  "$OUT/w5-preflight-base.log" "$OUT/w5-matrix-base.log" \
  "$OUT/w5-matrix-small.log" "$OUT/w6-quality-base.log" \
  "$OUT/w6-quality-small.log" "$OUT/w7-finalize.log" \
  "$OUT/paper-evidence-finalize.log"
archive_glob "$ARCHIVE/oracle" \
  "$OUT/oracle/base-W*.json" "$OUT/oracle/base-B*.json" \
  "$OUT/oracle/small-W*.json" "$OUT/oracle/small-B*.json" \
  "$OUT/oracle/w5-preflight-base.json"
archive_glob "$ARCHIVE/markers" \
  "$OUT/.w5-matrix-complete" "$OUT/.w5-matrix-failed" \
  "$OUT/.w5-preflight-pass" "$OUT/.w5-preflight-failed" \
  "$OUT/.w6-quality-complete" "$OUT/.w6-quality-failed" \
  "$OUT/.w6-blocked" "$OUT/.w7-finalized"

echo "START fresh W5 epoch"
W5_SEED_EPOCH=202710 \
W5_BASE_C16_MAX_NEW_TOKENS=96 \
W5_BASE_C8_MAX_NEW_TOKENS=80 \
W5_SMALL_C16_MAX_NEW_TOKENS=80 \
W5_SMALL_C8_MAX_NEW_TOKENS=80 \
bash "$W5" "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w5-max80-master.log" 2>&1
w5_rc="$?"

echo "START W6 quality"
W6_BASE_MAX_NEW_TOKENS=96 \
W6_SMALL_MAX_NEW_TOKENS=80 \
bash "$W6" "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$MANIFEST" "$OUT" \
  >"$OUT/w6-max80-master.log" 2>&1
w6_rc="$?"

echo "START W7 finalization"
bash "$W7" "$ROOT" "$BASE_MODEL" "$SMALL_MODEL" "$OUT" \
  >"$OUT/w7-max80-master.log" 2>&1
w7_rc="$?"

"$PY" - "$OUT" "$w5_rc" "$w6_rc" "$w7_rc" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
payload = {
    "w5_rc": int(sys.argv[2]),
    "w6_rc": int(sys.argv[3]),
    "w7_rc": int(sys.argv[4]),
}
(out / "max80-pipeline-status.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n"
)
PY
touch "$OUT/.max80-pipeline-finished"

if [[ "$w5_rc" -ne 0 || "$w6_rc" -ne 0 || "$w7_rc" -ne 0 ]]; then
  exit 2
fi
exit 0

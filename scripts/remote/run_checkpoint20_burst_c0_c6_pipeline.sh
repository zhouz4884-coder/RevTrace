#!/usr/bin/env bash
# Finish every C1/C4/C5/C6 experiment even if an individual gate fails.
set -uo pipefail

ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
REPO="$ROOT/projects/revtrace"
PY="$ROOT/envs/revbatch-cu128/bin/python"
OUTDIR="${REVTRACE_OUTDIR:-$REPO/results/checkpoint20_burst_authority}"
LAUNCH="$REPO/scripts/remote/launch_checkpoint20_burst_authority.sh"
mkdir -p "$OUTDIR"
cd "$REPO"

if [[ ! -f "$OUTDIR/b1_b2_compatibility_720.json" ]]; then
  echo "missing C2 B1/B2 compatibility gate" >&2
  exit 65
fi

declare -a names=()
declare -a statuses=()
run_gate() {
  local name="$1"
  shift
  set +e
  "$@"
  local status=$?
  set -e
  names+=("$name")
  statuses+=("$status")
}

set -e
run_gate calibrate env \
  REVTRACE_CODE_COMMIT=C0_C6_BURST_CLOSURE \
  bash "$LAUNCH" calibrate

threshold="$(
  "$PY" - "$OUTDIR/calibration.json" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
heldout = [row for row in payload["stages"] if row["label"] == "heldout"]
if len(heldout) != 1 or heldout[0]["threshold"] is None:
    raise SystemExit("calibration has no unique heldout threshold")
print(heldout[0]["threshold"])
PY
)"
printf '%s\n' "$threshold" > "$OUTDIR/frozen_threshold.txt"

run_gate audit env \
  REVTRACE_FROZEN_THRESHOLD="$threshold" \
  REVTRACE_CODE_COMMIT=C0_C6_BURST_CLOSURE \
  bash "$LAUNCH" audit

for seed in 20260830 20260831 20260832 20260833 20260834; do
  run_gate "seed_${seed}" env \
    REVTRACE_FROZEN_THRESHOLD="$threshold" \
    REVTRACE_SEED="$seed" \
    REVTRACE_CODE_COMMIT=C0_C6_BURST_CLOSURE \
    bash "$LAUNCH" seed
done

run_gate quality env \
  REVTRACE_CODE_COMMIT=C0_C6_BURST_CLOSURE \
  bash "$LAUNCH" quality

overall=0
{
  printf '{\n  "threshold": %s,\n  "gates": {\n' "$threshold"
  for index in "${!names[@]}"; do
    comma=","
    if [[ "$index" -eq "$((${#names[@]} - 1))" ]]; then
      comma=""
    fi
    printf '    "%s": %s%s\n' \
      "${names[$index]}" "${statuses[$index]}" "$comma"
    if [[ "${statuses[$index]}" -ne 0 ]]; then
      overall=2
    fi
  done
  printf '  }\n}\n'
} > "$OUTDIR/pipeline_status.json"
exit "$overall"

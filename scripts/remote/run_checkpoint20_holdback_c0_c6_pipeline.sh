#!/usr/bin/env bash
# Run every formal-risk, service, and quality gate even after a failure.
set -uo pipefail

ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
REPO="$ROOT/projects/revtrace"
PY="$ROOT/envs/revbatch-cu128/bin/python"
OUTDIR="${REVTRACE_OUTDIR:-$REPO/results/checkpoint20_holdback_authority}"
LAUNCH="$REPO/scripts/remote/launch_checkpoint20_holdback_authority.sh"
mkdir -p "$OUTDIR"
cd "$REPO"

if [[ ! -f "$OUTDIR/calibration.json" ]]; then
  echo "missing holdback-contract calibration" >&2
  exit 65
fi

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
run_gate audit env \
  REVTRACE_FROZEN_THRESHOLD="$threshold" \
  REVTRACE_CODE_COMMIT=HOLDBACK_CLOSURE \
  bash "$LAUNCH" audit

for seed in 20260840 20260841 20260842 20260843 20260844; do
  run_gate "seed_${seed}" env \
    REVTRACE_FROZEN_THRESHOLD="$threshold" \
    REVTRACE_SEED="$seed" \
    REVTRACE_CODE_COMMIT=HOLDBACK_CLOSURE \
    bash "$LAUNCH" seed
done

run_gate quality env \
  REVTRACE_FROZEN_THRESHOLD="$threshold" \
  REVTRACE_CODE_COMMIT=HOLDBACK_CLOSURE \
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

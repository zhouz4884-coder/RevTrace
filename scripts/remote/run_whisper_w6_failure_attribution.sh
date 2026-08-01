#!/usr/bin/env bash
# Attribute W6 state-only quality outliers to state, terminal, or work budget.
set -euo pipefail

ROOT="$1"
OUT="$2"
MODEL_SLUG="${3:-small}"
DEVICE="${4:-cuda:1}"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_quality.py"
DEV="$OUT/development/w6-failure-attribution-${MODEL_SLUG}"
mkdir -p "$DEV"
export PYTHONPATH="$PROJ/src"

tau="$(cat "$OUT/w4-final-threshold-${MODEL_SLUG}-c16.txt")"
lw="$(cat "$OUT/w4-final-late-window-${MODEL_SLUG}-c16.txt")"
lt="$(cat "$OUT/w4-final-late-threshold-${MODEL_SLUG}-c16.txt")"
hp="$(cat "$OUT/w4-final-high-load-prompt-${MODEL_SLUG}-c16.txt")"
ht="$(cat "$OUT/w4-final-high-load-threshold-${MODEL_SLUG}-c16.txt")"
context=()
if [[ "$lw" != none ]]; then
  context+=(--late-window-index "$lw" --late-margin-threshold "$lt")
fi
if [[ "$hp" != none ]]; then
  context+=(
    --high-load-prompt-tokens "$hp"
    --high-load-margin-threshold "$ht"
  )
fi
max_new=96
if [[ "$MODEL_SLUG" == small ]]; then max_new=80; fi

common=(
  --model "$ROOT/models/whisper-${MODEL_SLUG}.en"
  --model-name "whisper-${MODEL_SLUG}.en"
  --manifest "$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json"
  --sessions-per-split 32
  --duration-seconds 90
  --window-seconds 10
  --concurrency 16
  --seed 20272592
  --bootstrap-seed 20272593
  --bootstrap-replicates 5000
  --max-new-tokens "$max_new"
  --reference-max-new-tokens 96
  --device "$DEVICE"
)

run_mode() {
  local name="$1"; shift
  set +e
  "$PY" "$RUNNER" "${common[@]}" \
    --output "$DEV/${name}.json" "$@" \
    >"$DEV/${name}.log" 2>&1
  local rc="$?"
  set -e
  echo "$name rc=$rc" | tee -a "$DEV/summary.log"
}

# Keep the selected state policy but restore canonical terminal output.
run_mode selected-state-terminal-canonical \
  --margin-threshold "$tau" "${context[@]}" \
  --deferred-terminal-authority

# Canonicalize every feedback-writing transition, but leave terminal batched.
run_mode all-state-terminal-batch \
  --margin-threshold 1000000 \
  --no-deferred-terminal-authority

# Canonicalize all state transitions and terminal output.  Any remaining
# difference from the 96-token reference is attributable to the deployed
# 80-token work budget rather than batch state or terminal selection.
run_mode all-state-terminal-canonical \
  --margin-threshold 1000000 \
  --deferred-terminal-authority

"$PY" - "$DEV" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for path in sorted(root.glob("*.json")):
    value = json.loads(path.read_text())
    rows.append({
        "mode": path.stem,
        "decision": value["decision"],
        "catastrophic_outliers": value["counts"][
            "catastrophic_outliers"
        ],
        "mean_wer_delta_pp": value["metrics"]["mean_wer_delta_pp"],
        "paired_bootstrap_95_upper_pp": value["metrics"][
            "paired_bootstrap_95_upper_pp"
        ],
        "deferred_risk_authorities": value["counts"].get(
            "deferred_risk_authorities", 0
        ),
        "deferred_terminal_authorities": value["counts"].get(
            "deferred_terminal_authorities", 0
        ),
    })
(root / "attribution-summary.json").write_text(
    json.dumps({"rows": rows}, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(rows, indent=2, sort_keys=True))
PY

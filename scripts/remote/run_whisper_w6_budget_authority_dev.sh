#!/usr/bin/env bash
# Development gate for saturation-triggered extended work authority.
set -euo pipefail

ROOT="$1"
OUT="$2"
MODEL_SLUG="${3:-small}"
DEVICE="${4:-cuda:1}"
WAIT_PID="${5:-}"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
RUNNER="$PROJ/scripts/remote/run_whisper_w_quality.py"
DEV="$OUT/development/w6-budget-authority-${MODEL_SLUG}"
mkdir -p "$DEV"
export PYTHONPATH="$PROJ/src"
if [[ -n "$WAIT_PID" ]]; then
  while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 20; done
fi

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

set +e
"$PY" "$RUNNER" \
  --model "$ROOT/models/whisper-${MODEL_SLUG}.en" \
  --model-name "whisper-${MODEL_SLUG}.en" \
  --manifest "$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json" \
  --output "$DEV/result.json" \
  --sessions-per-split 32 \
  --duration-seconds 90 \
  --window-seconds 10 \
  --concurrency 16 \
  --margin-threshold "$tau" "${context[@]}" \
  --seed 20272592 \
  --bootstrap-seed 20272593 \
  --bootstrap-replicates 5000 \
  --max-new-tokens "$max_new" \
  --authority-max-new-tokens 96 \
  --reference-max-new-tokens 96 \
  --no-deferred-terminal-authority \
  --device "$DEVICE" >"$DEV/run.log" 2>&1
rc="$?"
set -e
"$PY" - "$DEV/result.json" <<'PY'
import json
import sys
row = json.load(open(sys.argv[1]))
print(json.dumps({
    "decision": row["decision"],
    "counts": row["counts"],
    "mean_wer_delta_pp": row["metrics"]["mean_wer_delta_pp"],
    "paired_bootstrap_95_upper_pp": row["metrics"][
        "paired_bootstrap_95_upper_pp"
    ],
    "per_split": row["metrics"]["per_split"],
    "provisional_lifetime_p95": row["metrics"][
        "provisional_lifetime_p95"
    ],
    "provisional_lifetime_max": row["metrics"][
        "provisional_lifetime_max"
    ],
    "provisional_overwrite_p95": row["metrics"][
        "provisional_overwrite_p95"
    ],
}, indent=2, sort_keys=True))
PY
echo "runner_rc=$rc"
touch "$OUT/.w6-budget-authority-${MODEL_SLUG}-complete"

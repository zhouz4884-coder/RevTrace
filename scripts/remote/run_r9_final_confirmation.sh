#!/usr/bin/env bash
set -euo pipefail
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft/final_holdout"
MANIFEST="$ROOT/datasets/revtrace/librispeech/r9-final-untouched.json"
mkdir -p "$OUT"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

run_model() {
  local gpu=$1 model=$2 boot=$3
  local coarse="$OUT/$model-coarse.json"
  local source="$OUT/$model-source.json"
  local probe="$OUT/$model-coverage-probe.json"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_segment_oracle.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" --output "$coarse" \
    --sessions-per-split 20 --duration-seconds 30 --window-seconds 10 \
    --seed 2026100101 --bootstrap-seed "$boot" --device cuda:0 \
    --concurrency 16 --modes adaptive15_30_batch \
    --adaptive-min-seconds 15 --adaptive-max-seconds 30 \
    --segment-salvage-yield-threshold 1.0 \
    --session-salvage-on-conflict --quality-only \
    >"$OUT/$model-coarse.log" 2>&1
  "$PY" - "$coarse" "$source" <<'PY'
import json, pathlib, sys
source_path, output_path = map(pathlib.Path, sys.argv[1:])
d = json.load(source_path.open())
mode = next(iter(d["modes"].values()))
payload = {
    "schema_version": 1,
    "metrics": {"canonical_seconds": d["baselines"]["canonical_seconds"]},
    "sessions": [
        {
            "utterance_ids": row["utterance_ids"],
            "canonical_wer": row["canonical_wer"],
            "canonical_text": "",
        }
        for row in mode["sessions"]
    ],
    "derived_from": str(source_path),
}
output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_cross_granularity_probe.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" --coarse-result "$coarse" --output "$probe" \
    --sessions-per-split 20 --duration-seconds 30 --window-seconds 10 \
    --seed 2026100101 --device cuda:0 --concurrency 16 \
    >"$OUT/$model-coverage-probe.log" 2>&1
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$PROJ/scripts/remote/run_r9_coverage_fallback.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" --source-quality "$source" \
    --coarse-result "$coarse" --coverage-probe "$probe" \
    --output "$OUT/$model-asym37-display-final-confirmation.json" \
    --coverage-threshold 0.37 --coverage-asymmetry-margin 0.10 \
    --structural-coverage-threshold 0.30 \
    --coverage-scope segment --repair-mode display-segment \
    --post-rebase-forward-threshold 0.20 \
    --post-rebase-reverse-ceiling 0.20 --sessions-per-split 20 \
    --duration-seconds 30 --window-seconds 10 --seed 2026100101 \
    --bootstrap-seed "$((boot + 100))" --device cuda:0 \
    >"$OUT/$model-asym37-display-final-confirmation.log" 2>&1 || true
}

run_model 0 tiny 2026100201 & tiny_pid=$!
run_model 1 base 2026100301 & base_pid=$!
wait "$tiny_pid"
wait "$base_pid"
run_model 0 small 2026100401

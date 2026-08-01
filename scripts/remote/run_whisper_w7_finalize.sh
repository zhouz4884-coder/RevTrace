#!/usr/bin/env bash
# Produce the W7 audit summary after W6 succeeds or reaches a recorded boundary.
set -u

if [[ "$#" -ne 4 ]]; then
  echo "usage: $0 ROOT BASE_MODEL SMALL_MODEL OUT" >&2
  exit 2
fi

ROOT="$1"
BASE_MODEL="$2"
SMALL_MODEL="$3"
OUT="$4"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"

while [[ ! -f "$OUT/.w6-quality-complete" \
  && ! -f "$OUT/.w6-quality-failed" \
  && ! -f "$OUT/.w6-blocked" ]]; do
  sleep 30
done
cd "$PROJ"
export PYTHONPATH="$PROJ/src"

"$PY" - "$BASE_MODEL" "$SMALL_MODEL" "$OUT/model-fingerprints.json" <<'PY'
import hashlib
import json
import pathlib
import sys

rows = []
for model in map(pathlib.Path, sys.argv[1:3]):
    weights = model / "model.safetensors"
    digest = hashlib.sha256()
    with weights.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    rows.append({
        "model_path": str(model),
        "model_safetensors_sha256": digest.hexdigest(),
        "bytes": weights.stat().st_size,
    })
pathlib.Path(sys.argv[3]).write_text(
    json.dumps(
        {"schema_version": 1, "models": rows},
        indent=2,
        sort_keys=True,
    ) + "\n"
)
PY

"$PY" scripts/finalize_whisper_w0_w7.py \
  --input-dir "$OUT" \
  --output-json "$OUT/w7-summary.json" \
  --output-md "$OUT/w7-report.md" >"$OUT/w7-finalize.log" 2>&1
final_rc="$?"
echo "W7 finalizer rc=$final_rc"
paper_rc=2
if [[ -s "$OUT/w7-summary.json" ]]; then
  "$PY" scripts/finalize_revtrace_paper_evidence.py \
    --whisper "$OUT/w7-summary.json" \
    --output-json "$OUT/paper-evidence-summary.json" \
    --output-md "$OUT/paper-evidence-report.md" \
    >"$OUT/paper-evidence-finalize.log" 2>&1
  paper_rc="$?"
fi
echo "Whole-paper evidence finalizer rc=$paper_rc"
touch "$OUT/.w7-finalized"
if [[ "$final_rc" -ne 0 || "$paper_rc" -ne 0 ]]; then
  exit 2
fi
exit 0

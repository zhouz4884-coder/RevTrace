#!/usr/bin/env bash
# Paired quality/UX validation for the renewed c16 production policy.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
POLICY="$OUT/p0/c16-policy.json"
RESULT="$OUT/p3/quality_c16_renewed/c16-holdback.json"
mkdir -p "$(dirname "$RESULT")" "$OUT/logs"
cd "$PROJ"; export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

mapfile -t P < <("$PY" - "$POLICY" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))['selected_policy']
for k in ('threshold','age_window_index','age_margin_threshold','late_window_index','late_margin_threshold','high_load_prompt_tokens','high_load_margin_threshold'):
 v=p.get(k); print('NONE' if v is None else v)
PY
)
ARGS=(--margin-threshold "${P[0]}" --policy-source "$POLICY")
[[ "${P[1]}" == NONE ]] || ARGS+=(--age-window-index "${P[1]}")
[[ "${P[2]}" == NONE ]] || ARGS+=(--age-margin-threshold "${P[2]}")
[[ "${P[3]}" == NONE ]] || ARGS+=(--late-window-index "${P[3]}")
[[ "${P[4]}" == NONE ]] || ARGS+=(--late-margin-threshold "${P[4]}")
[[ "${P[5]}" == NONE ]] || ARGS+=(--high-load-prompt-tokens "${P[5]}")
[[ "${P[6]}" == NONE ]] || ARGS+=(--high-load-margin-threshold "${P[6]}")

CUDA_VISIBLE_DEVICES=0 "$PY" "$PROJ/scripts/remote/run_whisper_w_quality.py" \
 --model "$MODEL" --model-name whisper-base.en --manifest "$MANIFEST" \
 --output "$RESULT" --sessions-per-split 64 --duration-seconds 90 \
 --window-seconds 10 --concurrency 16 --seed 20275501 \
 --bootstrap-seed 20275502 --bootstrap-replicates 10000 \
 --max-new-tokens 96 --authority-max-new-tokens 96 \
 --reference-max-new-tokens 96 --checkpoint-revisions 10 \
 --checkpoint-phase-policy synchronized --no-deferred-risk-authority \
 --no-deferred-terminal-authority --device cuda:0 "${ARGS[@]}" \
 >"$OUT/logs/p3-c16-quality-renewed.log" 2>&1
touch "$OUT/.c16-quality-complete"

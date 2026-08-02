#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OUT="$ROOT/results/revtrace/whisper_p0_p3"; RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
POLICY="$OUT/p0/c16-policy.json"; PILOT="$OUT/pilot/c16_shared_verifier"
ORACLE="$OUT/oracle/base-c16-w2-tail-seed20276006.json"
mkdir -p "$PILOT" "$OUT/logs"; cd "$PROJ"; export PYTHONPATH="$PROJ/src"
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
run_cell() {
 local name="$1" lanes="$2"
 "$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
  --manifest "$MANIFEST" --output "$PILOT/${name}.json" --oracle-cache "$ORACLE" \
  --sessions 16 --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --arrival poisson --arrival-scale-seconds 0.02 --seed 20276006 \
  --max-new-tokens 96 --authority-max-new-tokens 96 --terminal-contract state-only \
  --verifier-lanes "$lanes" --share-verifier-weights --slo-seconds 1.9 \
  --system revtrace --low-margin-policy verify --proposer-device cuda:0 \
  --verifier-device cuda:1 "${ARGS[@]}" \
  >"$OUT/logs/pilot-shared-verifier-${name}.log" 2>&1
}
run_cell lane2-shared 2
run_cell lane3-shared 3
touch "$PILOT/.complete"

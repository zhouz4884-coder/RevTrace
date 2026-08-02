#!/usr/bin/env bash
# Replay the two observed live failure roots under the learned piecewise
# revision-window frontier.  This is an adaptation-root check, not independent
# risk evidence.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OUT="$ROOT/results/revtrace/whisper_p0_p3"; RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
POLICY="$OUT/p0/c16-policy.json"; PILOT="$OUT/pilot/c16_r3_replay"
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
mapfile -t WINDOW_RULES < <("$PY" - "$POLICY" <<'PY'
import json,sys
for row in json.load(open(sys.argv[1]))['selected_policy'].get('window_margin_rules', []):
 print(f"{row['window_index']}:{row['margin_threshold']}")
PY
)
for rule in "${WINDOW_RULES[@]}"; do ARGS+=(--window-margin-rule "$rule"); done
run_cell() {
 local arrival="$1" seed="$2" output="$3" oracle="$4"; local extra=()
 [[ "$arrival" == poisson ]] && extra=(--arrival-scale-seconds 0.02)
 "$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
  --manifest "$MANIFEST" --output "$output" --oracle-cache "$oracle" \
  --sessions 16 --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --arrival "$arrival" "${extra[@]}" --seed "$seed" --max-new-tokens 96 \
  --authority-max-new-tokens 96 --terminal-contract state-only --verifier-lanes 2 \
  --slo-seconds 1.9 --system revtrace --low-margin-policy verify \
  --proposer-device cuda:0 --verifier-device cuda:1 "${ARGS[@]}" \
  >"$OUT/logs/pilot-r3-${arrival}-${seed}.log" 2>&1
}
run_cell poisson 20276006 "$PILOT/w2-root-replay.json" \
 "$OUT/oracle/base-c16-w2-tail-seed20276006.json"
run_cell sync 20276001 "$PILOT/w1-replay.json" \
 "$OUT/oracle/base-c16-topology-seed20276001.json"
run_cell sync 20276101 "$PILOT/w1-r5-root-replay.json" \
 "$OUT/oracle/base-c16-w1-lane2-seed20276101.json"
touch "$OUT/.c16-r3-replay-complete"

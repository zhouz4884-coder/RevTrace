#!/usr/bin/env bash
# Test whether the W2 risk-dense bottleneck is verifier parallelism rather than
# proposer work.  Uses the fixed adaptation seed only; no result is independent
# paper evidence.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OUT="$ROOT/results/revtrace/whisper_p0_p3"; RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
POLICY="$OUT/p0/c16-policy.json"; PILOT="$OUT/pilot/c16_r6_lanes"
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
mapfile -t RULES < <("$PY" - "$POLICY" <<'PY'
import json,sys
for row in json.load(open(sys.argv[1]))['selected_policy'].get('window_margin_rules',[]):
 print(f"{row['window_index']}:{row['margin_threshold']}")
PY
)
for rule in "${RULES[@]}"; do ARGS+=(--window-margin-rule "$rule"); done
for lanes in 3 4; do
 [[ -f "$PILOT/w2-lanes${lanes}.json" ]] && continue
 "$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
  --manifest "$MANIFEST" --output "$PILOT/w2-lanes${lanes}.json" \
  --oracle-cache "$OUT/oracle/base-c16-w2-tail-seed20276006.json" \
  --sessions 16 --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --arrival poisson --arrival-scale-seconds 0.02 --seed 20276006 \
  --max-new-tokens 96 --authority-max-new-tokens 96 \
  --terminal-contract state-only --verifier-lanes "$lanes" --slo-seconds 1.9 \
  --system revtrace --low-margin-policy verify --proposer-device cuda:0 \
  --verifier-device cuda:1 "${ARGS[@]}" \
  >"$OUT/logs/pilot-r6-w2-lanes${lanes}.log" 2>&1
done
if [[ ! -f "$PILOT/w2-lanes2-spill.json" ]]; then
"$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
 --manifest "$MANIFEST" --output "$PILOT/w2-lanes2-spill.json" \
 --oracle-cache "$OUT/oracle/base-c16-w2-tail-seed20276006.json" \
 --sessions 16 --duration-seconds 90 --window-seconds 10 --concurrency 16 \
 --arrival poisson --arrival-scale-seconds 0.02 --seed 20276006 \
 --max-new-tokens 96 --authority-max-new-tokens 96 \
 --terminal-contract state-only --verifier-lanes 2 --slo-seconds 1.9 \
 --system revtrace --low-margin-policy verify --proposer-device cuda:0 \
 --verifier-device cuda:1 --authority-spillover-on-proposer "${ARGS[@]}" \
 >"$OUT/logs/pilot-r6-w2-lanes2-spill.log" 2>&1
fi

#!/usr/bin/env bash
# Independent Poisson-arrival c16 headline cells, complementing the sync W1
# cells in run_whisper_p0_p3.sh.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OLD="$ROOT/results/revtrace/whisper_w0_w7"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
POLICY="$OLD/w4-state-age-policy-base-c16-recovery-r4.json"
mkdir -p "$OUT/p3/c16_w1_final" "$OUT/p3/c16_w2" "$OUT/oracle" "$OUT/logs"
cd "$PROJ"; export PYTHONPATH="$PROJ/src"
"$PY" - "$RUNNER" "$PROJ/src/revtrace/whisper_state.py" \
  >"$OUT/p0/final_runtime_code_identity.json" <<'PY'
import hashlib,json,pathlib,sys
rows=[]
for raw in sys.argv[1:]:
 p=pathlib.Path(raw)
 rows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps({'schema_version':1,'files':rows},indent=2,sort_keys=True))
PY
mapfile -t P < <("$PY" - "$POLICY" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))['selected_policy']
for k in ('threshold','late_window_index','late_margin_threshold','high_load_prompt_tokens','high_load_margin_threshold'):
 v=p.get(k); print('NONE' if v is None else v)
PY
)
ARGS=(--margin-threshold "${P[0]}" --policy-source "$POLICY")
[[ "${P[1]}" == NONE ]] || ARGS+=(--late-window-index "${P[1]}")
[[ "${P[2]}" == NONE ]] || ARGS+=(--late-margin-threshold "${P[2]}")
[[ "${P[3]}" == NONE ]] || ARGS+=(--high-load-prompt-tokens "${P[3]}")
[[ "${P[4]}" == NONE ]] || ARGS+=(--high-load-margin-threshold "${P[4]}")
for seed in 20274601 20274602 20274603 20274604 20274605; do
  echo "[$(date -Is)] START c16-W2 seed=$seed"
  "$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
    --manifest "$MANIFEST" --output "$OUT/p3/c16_w2/seed${seed}.json" \
    --oracle-cache "$OUT/oracle/base-c16-w2-seed${seed}.json" \
    --sessions 16 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --arrival poisson --arrival-scale-seconds 0.02 \
    --seed "$seed" --max-new-tokens 96 --authority-max-new-tokens 96 \
    --terminal-contract state-only --verifier-lanes 1 --slo-seconds 1.9 \
    --system revtrace --low-margin-policy holdback \
    --proposer-device cuda:0 --verifier-device cuda:1 "${ARGS[@]}" \
    >"$OUT/logs/p3-c16-W2-seed${seed}.log" 2>&1
  echo "[$(date -Is)] DONE c16-W2 seed=$seed"
done
# Re-run the synchronized W1 matrix under the exact same frozen source build
# as W2.  Earlier W1 results remain useful replication evidence but are not
# mixed into the final same-build headline matrix.
for seed in 20275101 20275102 20275103 20275104 20275105; do
  echo "[$(date -Is)] START c16-W1-final seed=$seed"
  "$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
    --manifest "$MANIFEST" --output "$OUT/p3/c16_w1_final/seed${seed}.json" \
    --oracle-cache "$OUT/oracle/base-c16-w1-final-seed${seed}.json" \
    --sessions 16 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --arrival sync --seed "$seed" --max-new-tokens 96 \
    --authority-max-new-tokens 96 --terminal-contract state-only \
    --verifier-lanes 1 --slo-seconds 1.9 --system revtrace \
    --low-margin-policy holdback --proposer-device cuda:0 \
    --verifier-device cuda:1 "${ARGS[@]}" \
    >"$OUT/logs/p3-c16-W1-final-seed${seed}.log" 2>&1
  echo "[$(date -Is)] DONE c16-W1-final seed=$seed"
done
touch "$OUT/.p3-c16-w2-complete"

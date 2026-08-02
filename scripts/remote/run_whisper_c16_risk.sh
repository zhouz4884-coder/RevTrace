#!/usr/bin/env bash
# Paper-critical c16 holdback-distribution certificates under the final build.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OLD="$ROOT/results/revtrace/whisper_w0_w7"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
POLICY="$OLD/w4-state-age-policy-base-c16-recovery-r4.json"
mkdir -p "$OUT/p3/risk" "$OUT/logs"
cd "$PROJ"; export PYTHONPATH="$PROJ/src"
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
pids=()
for spec in "0:20274400" "1:20274450"; do
 gpu=${spec%%:*}; seed=${spec##*:}
 CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$RUNNER" audit \
  --model "$MODEL" --model-name whisper-base.en --manifest "$MANIFEST" \
  --output "$OUT/p3/risk/c16-seed${seed}.json" --sessions 32 \
  --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --seed "$seed" --max-new-tokens 96 --authority-max-new-tokens 96 \
  --target-risk-entries 30000 --minimum-audits 500 --audit-probability 0.021 \
  --low-margin-policy holdback --proposer-device cuda:0 --verifier-device cuda:0 \
  "${ARGS[@]}" >"$OUT/logs/risk-c16-seed${seed}.log" 2>&1 &
 pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=$?; done
exit "$status"

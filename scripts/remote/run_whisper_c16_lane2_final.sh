#!/usr/bin/env bash
# Final c16 production matrix after the topology death gates. Two independent
# BS=1 canonical lanes preserve the reference arithmetic path; no speculative
# descendants, shape padding, cohort barrier, or proposer spillover is used.
set -euo pipefail

ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
POLICY="$OUT/p0/c16-policy.json"
mkdir -p "$OUT/p3/c16_w1_lane2_final_r6" "$OUT/p3/c16_w2_lane2_final_r6" \
 "$OUT/p3/risk_c16_lane2_final_r6" "$OUT/oracle" "$OUT/logs"
cd "$PROJ"; export PYTHONPATH="$PROJ/src"

"$PY" - "$RUNNER" "$PROJ/src/revtrace/whisper_state.py" \
 >"$OUT/p0/final_runtime_code_identity.json" <<'PY'
import hashlib, json, pathlib, sys
rows = []
for raw in sys.argv[1:]:
    path = pathlib.Path(raw)
    rows.append({
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
print(json.dumps({"schema_version": 1, "files": rows}, indent=2, sort_keys=True))
PY

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
for rule in "${WINDOW_RULES[@]}"; do
 ARGS+=(--window-margin-rule "$rule")
done

run_perf() {
 local arrival="$1" seed="$2" output="$3" oracle="$4" log="$5"
 local extra=(); [[ "$arrival" == poisson ]] && extra=(--arrival-scale-seconds 0.02)
 "$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
  --manifest "$MANIFEST" --output "$output" --oracle-cache "$oracle" \
  --sessions 16 --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --arrival "$arrival" "${extra[@]}" --seed "$seed" --max-new-tokens 96 \
  --authority-max-new-tokens 96 --terminal-contract state-only \
  --verifier-lanes 2 --slo-seconds 1.9 --system revtrace \
  --low-margin-policy verify --proposer-device cuda:0 --verifier-device cuda:1 \
  "${ARGS[@]}" >"$OUT/logs/$log.log" 2>&1
}

for seed in 20276701 20276702 20276703 20276704 20276705; do
 run_perf sync "$seed" "$OUT/p3/c16_w1_lane2_final_r6/seed${seed}.json" \
  "$OUT/oracle/base-c16-w1-lane2-seed${seed}.json" "p3-c16-W1-lane2-seed${seed}"
done
for seed in 20276801 20276802 20276803 20276804 20276805; do
 run_perf poisson "$seed" "$OUT/p3/c16_w2_lane2_final_r6/seed${seed}.json" \
  "$OUT/oracle/base-c16-w2-lane2-seed${seed}.json" "p3-c16-W2-lane2-seed${seed}"
done

pids=()
for spec in "0:20276900" "1:20276950"; do
 gpu=${spec%%:*}; seed=${spec##*:}
 CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$RUNNER" audit \
  --model "$MODEL" --model-name whisper-base.en --manifest "$MANIFEST" \
  --output "$OUT/p3/risk_c16_lane2_final_r6/c16-seed${seed}.json" --sessions 32 \
  --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --seed "$seed" --max-new-tokens 96 --authority-max-new-tokens 96 \
  --target-risk-entries 30000 --minimum-audits 500 --audit-probability 0.021 \
  --low-margin-policy verify --proposer-device cuda:0 --verifier-device cuda:0 \
  "${ARGS[@]}" >"$OUT/logs/risk-c16-lane2-seed${seed}.log" 2>&1 &
 pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
touch "$OUT/.c16-lane2-final-complete"

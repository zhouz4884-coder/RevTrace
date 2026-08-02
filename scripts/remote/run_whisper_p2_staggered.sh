#!/usr/bin/env bash
# Repair the c8 checkpoint burst while preserving the ten-revision per-session
# authority bound. Run only after the initial P0-P3 attribution pipeline.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
QUALITY_MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality.json"
OLD="$ROOT/results/revtrace/whisper_w0_w7"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
QUALITY="$PROJ/scripts/remote/run_whisper_w_quality.py"
POLICY="${2:-$OLD/w4-state-age-policy-base-c8-m80-recovery-r5.json}"
mkdir -p "$OUT/p2_staggered" "$OUT/p3/c8_staggered" \
  "$OUT/p3/risk_staggered" "$OUT/p3/quality_staggered" "$OUT/logs" "$OUT/oracle"
cd "$PROJ"; export PYTHONPATH="$PROJ/src"
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

run_perf() {
 local name="$1" seed="$2" proposer="$3" verifier="$4" output="$5"
 "$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
  --manifest "$MANIFEST" --output "$output" \
  --oracle-cache "$OUT/oracle/base-c8-stagger-seed${seed}.json" \
  --sessions 8 --duration-seconds 180 --window-seconds 10 --concurrency 8 \
  --arrival sync --seed "$seed" --max-new-tokens 80 \
  --authority-max-new-tokens 96 --terminal-contract state-only \
  --system revtrace --low-margin-policy holdback \
  --checkpoint-revisions 10 --checkpoint-phase-policy session-staggered \
  --verifier-lanes 1 --slo-seconds 1.9 \
  --proposer-device "$proposer" --verifier-device "$verifier" "${ARGS[@]}" \
  >"$OUT/logs/${name}.log" 2>&1
}

SEED=20274701
run_perf p2-stagger-dual "$SEED" cuda:0 cuda:1 "$OUT/p2_staggered/dual.json"
run_perf p2-stagger-colocated "$SEED" cuda:0 cuda:0 "$OUT/p2_staggered/colocated.json"
TOPOLOGY=$("$PY" - "$OUT/p2_staggered" "$OUT/p2_staggered/selection.json" <<'PY'
import json,pathlib,sys
r=pathlib.Path(sys.argv[1]); rows=[]
for name in ('dual','colocated'):
 d=json.load(open(r/f'{name}.json')); m=d['metrics']; c=d['counts']
 eligible=(c['state_violations']==0 and c['stale_commits']==0 and c['deadline_misses']==0 and c['display_deadline_misses']==0 and m['wall_speedup']>=2.2 and m['gpu_normalized_speedup']>=1.1 and m['energy_reduction']>=0.20 and m['display_latency_p99']<=1.9 and m['latency_p99']<=2.5)
 rows.append({'name':name,'eligible':eligible,'wall':m['wall_speedup'],'gpu_norm':m['gpu_normalized_speedup'],'energy':m['energy_reduction'],'state_p99':m['latency_p99']})
valid=[x for x in rows if x['eligible']]
selected=max(valid,key=lambda x:(x['gpu_norm'],x['wall']))['name'] if valid else None
pathlib.Path(sys.argv[2]).write_text(json.dumps({'schema_version':1,'candidates':rows,'selected':selected},indent=2,sort_keys=True)+'\n')
print(selected or 'NONE')
PY
)
if [[ "$TOPOLOGY" == NONE ]]; then touch "$OUT/.p2-staggered-blocked"; exit 0; fi
if [[ "$TOPOLOGY" == colocated ]]; then PROP=cuda:0; VER=cuda:0; else PROP=cuda:0; VER=cuda:1; fi
for seed in 20274801 20274802 20274803 20274804 20274805; do
 run_perf "p3-c8-stagger-seed${seed}" "$seed" "$PROP" "$VER" "$OUT/p3/c8_staggered/seed${seed}.json"
done

# Re-certify the state distribution created by staggered checkpoints.
pids=()
for spec in "0:20274900" "1:20274950"; do
 gpu=${spec%%:*}; seed=${spec##*:}
 CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$RUNNER" audit \
  --model "$MODEL" --model-name whisper-base.en --manifest "$MANIFEST" \
  --output "$OUT/p3/risk_staggered/c8-seed${seed}.json" \
  --sessions 32 --duration-seconds 180 --window-seconds 10 --concurrency 8 \
  --seed "$seed" --max-new-tokens 80 --authority-max-new-tokens 96 \
  --target-risk-entries 30000 --minimum-audits 500 --audit-probability 0.021 \
  --low-margin-policy holdback --checkpoint-revisions 10 \
  --checkpoint-phase-policy session-staggered \
  --proposer-device cuda:0 --verifier-device cuda:0 "${ARGS[@]}" \
  >"$OUT/logs/risk-stagger-c8-seed${seed}.log" 2>&1 &
 pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done

# Correctly matched quality path: the same staggered checkpoint schedule and
# low-margin holdback action are used here as in performance and risk runs.
"$PY" "$QUALITY" --model "$MODEL" --model-name whisper-base.en \
 --manifest "$QUALITY_MANIFEST" --output "$OUT/p3/quality_staggered/c8-holdback.json" \
 --sessions-per-split 64 --duration-seconds 180 --window-seconds 10 \
 --concurrency 8 --seed 20275001 --bootstrap-seed 20275002 \
 --bootstrap-replicates 10000 --max-new-tokens 80 \
 --authority-max-new-tokens 96 --reference-max-new-tokens 96 \
 --no-deferred-risk-authority --no-deferred-terminal-authority \
 --checkpoint-revisions 10 --checkpoint-phase-policy session-staggered \
 --device cuda:0 --margin-threshold "${P[0]}" --policy-source "$POLICY" \
 $( [[ "${P[1]}" == NONE ]] || echo --age-window-index "${P[1]}" ) \
 $( [[ "${P[2]}" == NONE ]] || echo --age-margin-threshold "${P[2]}" ) \
 $( [[ "${P[3]}" == NONE ]] || echo --late-window-index "${P[3]}" ) \
 $( [[ "${P[4]}" == NONE ]] || echo --late-margin-threshold "${P[4]}" ) \
 $( [[ "${P[5]}" == NONE ]] || echo --high-load-prompt-tokens "${P[5]}" ) \
 $( [[ "${P[6]}" == NONE ]] || echo --high-load-margin-threshold "${P[6]}" ) \
 >"$OUT/logs/quality-stagger-c8.log" 2>&1
touch "$OUT/.p2-staggered-complete"

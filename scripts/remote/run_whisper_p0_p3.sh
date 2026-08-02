#!/usr/bin/env bash
# P0-P3 closure: metric/evidence repair, c8 ceiling attribution, prompt-state
# holdback, independent c8 boundary and c16 headline validation.
set -euo pipefail

ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OLD="$ROOT/results/revtrace/whisper_w0_w7"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
QUALITY="$PROJ/scripts/remote/run_whisper_w_quality.py"
P8="$OLD/w4-state-age-policy-base-c8-m80-recovery-r5.json"
P16="$OLD/w4-state-age-policy-base-c16-recovery-r4.json"

mkdir -p "$OUT/p0" "$OUT/p1" "$OUT/p3/c8" "$OUT/p3/c16" \
  "$OUT/p3/risk" "$OUT/p3/quality" "$OUT/oracle" "$OUT/logs"
cd "$PROJ"
export PYTHONPATH="$PROJ/src"

read_policy() {
  "$PY" - "$1" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))['selected_policy']
for k in ('threshold','late_window_index','late_margin_threshold','high_load_prompt_tokens','high_load_margin_threshold'):
    v=p.get(k)
    print('NONE' if v is None else v)
PY
}

mapfile -t C8 < <(read_policy "$P8")
mapfile -t C16 < <(read_policy "$P16")

policy_args() {
  local policy="$1"; shift
  local -a row=("$@")
  printf '%s\n' --margin-threshold "${row[0]}"
  [[ "${row[1]}" == NONE ]] || printf '%s\n' --late-window-index "${row[1]}"
  [[ "${row[2]}" == NONE ]] || printf '%s\n' --late-margin-threshold "${row[2]}"
  [[ "${row[3]}" == NONE ]] || printf '%s\n' --high-load-prompt-tokens "${row[3]}"
  [[ "${row[4]}" == NONE ]] || printf '%s\n' --high-load-margin-threshold "${row[4]}"
  printf '%s\n' --policy-source "$policy"
}

mapfile -t A8 < <(policy_args "$P8" "${C8[@]}")
mapfile -t A16 < <(policy_args "$P16" "${C16[@]}")

common_workload() {
  local output="$1" oracle="$2" seed="$3" sessions="$4" duration="$5" concurrency="$6" maxnew="$7"; shift 7
  "$PY" "$RUNNER" workload \
    --model "$MODEL" --model-name whisper-base.en --manifest "$MANIFEST" \
    --output "$output" --oracle-cache "$oracle" \
    --sessions "$sessions" --duration-seconds "$duration" \
    --window-seconds 10 --concurrency "$concurrency" --arrival sync \
    --seed "$seed" --max-new-tokens "$maxnew" \
    --authority-max-new-tokens 96 --terminal-contract state-only \
    --verifier-lanes 1 --slo-seconds 1.9 "$@"
}

run_logged() {
  local log="$1"; shift
  echo "[$(date -Is)] START $log"
  "$@" >"$OUT/logs/$log.log" 2>&1
  echo "[$(date -Is)] DONE  $log"
}

# P0 source/runtime smoke.  Local tests are run separately; this records the
# exact remote code hashes used by every subsequent measurement.
"$PY" - "$RUNNER" "$PROJ/src/revtrace/whisper_state.py" >"$OUT/p0/code_identity.json" <<'PY'
import hashlib,json,pathlib,sys
rows=[]
for raw in sys.argv[1:]:
 p=pathlib.Path(raw); rows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps({'schema_version':1,'files':rows},indent=2,sort_keys=True))
PY

# P1: same-input performance ceiling and authority-cost decomposition.
SEED=20274001
ORACLE="$OUT/oracle/base-c8-seed${SEED}.json"
run_logged p1-unprotected \
  common_workload "$OUT/p1/unprotected.json" "$ORACLE" "$SEED" 8 180 8 80 \
  --system unprotected-batch --proposer-device cuda:0 --verifier-device cuda:1 "${A8[@]}"
run_logged p1-feedback-off \
  common_workload "$OUT/p1/feedback-off.json" "$ORACLE" "$SEED" 8 180 8 80 \
  --system feedback-off-batch --proposer-device cuda:0 --verifier-device cuda:1 "${A8[@]}"
run_logged p1-checkpoint-only \
  common_workload "$OUT/p1/checkpoint-only.json" "$ORACLE" "$SEED" 8 180 8 80 \
  --system revtrace --disable-risk-authority --proposer-device cuda:0 --verifier-device cuda:1 "${A8[@]}"
run_logged p1-risk-only \
  common_workload "$OUT/p1/risk-only.json" "$ORACLE" "$SEED" 8 180 8 80 \
  --system revtrace --disable-checkpoint-authority --proposer-device cuda:0 --verifier-device cuda:1 "${A8[@]}"
run_logged p1-full-verify \
  common_workload "$OUT/p1/full-verify.json" "$ORACLE" "$SEED" 8 180 8 80 \
  --system revtrace --proposer-device cuda:0 --verifier-device cuda:1 "${A8[@]}"
run_logged p2-holdback-dual \
  common_workload "$OUT/p1/holdback-dual.json" "$ORACLE" "$SEED" 8 180 8 80 \
  --system revtrace --low-margin-policy holdback \
  --proposer-device cuda:0 --verifier-device cuda:1 "${A8[@]}"
run_logged p2-holdback-colocated \
  common_workload "$OUT/p1/holdback-colocated.json" "$ORACLE" "$SEED" 8 180 8 80 \
  --system revtrace --low-margin-policy holdback \
  --proposer-device cuda:0 --verifier-device cuda:0 "${A8[@]}"

# Select the P3 c8 deployment using a frozen rule: among zero-violation
# holdback variants satisfying display/state deadlines, maximize
# GPU-normalized speedup, then wall speedup.  If neither is valid, stop c8 P3
# but continue c16 headline validation.
TOPOLOGY=$("$PY" - "$OUT/p1" "$OUT/p0/topology_selection.json" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); rows=[]
for name in ('holdback-dual','holdback-colocated'):
 d=json.load(open(root/f'{name}.json')); m=d['metrics']; c=d['counts']
 eligible=(c['state_violations']==0 and c['stale_commits']==0 and c['display_deadline_misses']==0 and m['display_latency_p99']<=1.9 and m['latency_p99']<=2.5)
 rows.append({'name':name,'eligible':eligible,'gpu_normalized_speedup':m['gpu_normalized_speedup'],'wall_speedup':m['wall_speedup']})
valid=[r for r in rows if r['eligible']]
selected=max(valid,key=lambda r:(r['gpu_normalized_speedup'],r['wall_speedup']))['name'] if valid else None
out.write_text(json.dumps({'schema_version':1,'candidates':rows,'selected':selected},indent=2,sort_keys=True)+'\n')
print(selected or 'NONE')
PY
)

run_p3() {
  local cell="$1" seed="$2"
  if [[ "$cell" == c8 ]]; then
    local sessions=8 duration=180 concurrency=8 maxnew=80 policy="$P8"
    local -a pa=("${A8[@]}")
    if [[ "$TOPOLOGY" == holdback-colocated ]]; then
      local proposer=cuda:0 verifier=cuda:0
    else
      local proposer=cuda:0 verifier=cuda:1
    fi
  else
    local sessions=16 duration=90 concurrency=16 maxnew=96 policy="$P16"
    local -a pa=("${A16[@]}")
    local proposer=cuda:0 verifier=cuda:1
  fi
  local oracle="$OUT/oracle/base-${cell}-seed${seed}.json"
  run_logged "p3-${cell}-seed${seed}" \
    common_workload "$OUT/p3/${cell}/seed${seed}.json" "$oracle" "$seed" \
      "$sessions" "$duration" "$concurrency" "$maxnew" \
      --system revtrace --low-margin-policy holdback \
      --proposer-device "$proposer" --verifier-device "$verifier" "${pa[@]}"
}

if [[ "$TOPOLOGY" != NONE ]]; then
  for seed in 20274101 20274102 20274103 20274104 20274105; do
    run_p3 c8 "$seed"
  done
else
  touch "$OUT/p3/.c8-topology-blocked"
fi

for seed in 20274201 20274202 20274203 20274204 20274205; do
  run_p3 c16 "$seed"
done

# Independent holdback-distribution certificates. Two seeds run in parallel
# on physically separate GPUs, with proposer and singleton authority colocated
# but temporally serialized inside each process.
run_audit_pair() {
  local cell="$1" duration="$2" concurrency="$3" maxnew="$4" policy="$5" base_seed="$6"; shift 6
  local -a pa=("$@")
  local s0="$base_seed" s1=$((base_seed+50))
  CUDA_VISIBLE_DEVICES=0 "$PY" "$RUNNER" audit \
    --model "$MODEL" --model-name whisper-base.en --manifest "$MANIFEST" \
    --output "$OUT/p3/risk/${cell}-seed${s0}.json" --sessions 32 \
    --duration-seconds "$duration" --window-seconds 10 --concurrency "$concurrency" \
    --seed "$s0" --max-new-tokens "$maxnew" --authority-max-new-tokens 96 \
    --target-risk-entries 30000 --minimum-audits 500 --audit-probability 0.021 \
    --low-margin-policy holdback --proposer-device cuda:0 --verifier-device cuda:0 \
    "${pa[@]}" >"$OUT/logs/risk-${cell}-seed${s0}.log" 2>&1 &
  local p0=$!
  CUDA_VISIBLE_DEVICES=1 "$PY" "$RUNNER" audit \
    --model "$MODEL" --model-name whisper-base.en --manifest "$MANIFEST" \
    --output "$OUT/p3/risk/${cell}-seed${s1}.json" --sessions 32 \
    --duration-seconds "$duration" --window-seconds 10 --concurrency "$concurrency" \
    --seed "$s1" --max-new-tokens "$maxnew" --authority-max-new-tokens 96 \
    --target-risk-entries 30000 --minimum-audits 500 --audit-probability 0.021 \
    --low-margin-policy holdback --proposer-device cuda:0 --verifier-device cuda:0 \
    "${pa[@]}" >"$OUT/logs/risk-${cell}-seed${s1}.log" 2>&1 &
  local p1=$!
  local status=0
  wait "$p0" || status=$?
  wait "$p1" || status=$?
  return "$status"
}

if ! run_audit_pair c8 180 8 80 "$P8" 20274300 "${A8[@]}"; then
  touch "$OUT/p3/.c8-risk-failed"
fi
run_audit_pair c16 90 16 96 "$P16" 20274400 "${A16[@]}"

# P3 paired quality: --no-deferred-risk-authority is the prompt-state
# holdback policy; terminal authority remains enabled for final WER scoring.
run_logged p3-quality-c8 \
  "$PY" "$QUALITY" --model "$MODEL" --model-name whisper-base.en \
  --manifest "$MANIFEST" --output "$OUT/p3/quality/c8-holdback.json" \
  --sessions-per-split 32 --duration-seconds 180 --window-seconds 10 \
  --concurrency 8 --seed 20274501 --bootstrap-seed 20274502 \
  --bootstrap-replicates 10000 --max-new-tokens 80 \
  --authority-max-new-tokens 96 --reference-max-new-tokens 96 \
  --no-deferred-risk-authority --deferred-terminal-authority \
  --device cuda:0 \
  --margin-threshold "${C8[0]}" \
  $( [[ "${C8[1]}" == NONE ]] || echo --late-window-index "${C8[1]}" ) \
  $( [[ "${C8[2]}" == NONE ]] || echo --late-margin-threshold "${C8[2]}" ) \
  $( [[ "${C8[3]}" == NONE ]] || echo --high-load-prompt-tokens "${C8[3]}" ) \
  $( [[ "${C8[4]}" == NONE ]] || echo --high-load-margin-threshold "${C8[4]}" )

touch "$OUT/.p0-p3-complete"
echo "[$(date -Is)] P0-P3 COMPLETE topology=$TOPOLOGY"

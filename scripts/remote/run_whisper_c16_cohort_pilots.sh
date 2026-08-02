#!/usr/bin/env bash
# Same-seed pilots for certified cohort release. The barrier changes only
# scheduling: no descendant executes until every parent state decision in its
# proposal batch has resolved.
set -euo pipefail

ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
POLICY="$OUT/p0/c16-policy.json"
PILOT="$OUT/pilot/c16_cohort"
ORACLE="$OUT/oracle/base-c16-cohort-seed20276002.json"
mkdir -p "$PILOT" "$OUT/logs" "$OUT/oracle"
cd "$PROJ"
export PYTHONPATH="$PROJ/src"

mapfile -t P < <("$PY" - "$POLICY" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))["selected_policy"]
for key in (
    "threshold", "age_window_index", "age_margin_threshold",
    "late_window_index", "late_margin_threshold",
    "high_load_prompt_tokens", "high_load_margin_threshold",
):
    value = p.get(key)
    print("NONE" if value is None else value)
PY
)
POLICY_ARGS=(--margin-threshold "${P[0]}" --policy-source "$POLICY")
[[ "${P[1]}" == NONE ]] || POLICY_ARGS+=(--age-window-index "${P[1]}")
[[ "${P[2]}" == NONE ]] || POLICY_ARGS+=(--age-margin-threshold "${P[2]}")
[[ "${P[3]}" == NONE ]] || POLICY_ARGS+=(--late-window-index "${P[3]}")
[[ "${P[4]}" == NONE ]] || POLICY_ARGS+=(--late-margin-threshold "${P[4]}")
[[ "${P[5]}" == NONE ]] || POLICY_ARGS+=(--high-load-prompt-tokens "${P[5]}")
[[ "${P[6]}" == NONE ]] || POLICY_ARGS+=(--high-load-margin-threshold "${P[6]}")

run_cell() {
    local name="$1" lanes="$2" spill="$3"
    local extra=()
    [[ "$spill" == 1 ]] && extra+=(--authority-spillover-on-proposer)
    "$PY" "$RUNNER" workload \
        --model "$MODEL" --model-name whisper-base.en \
        --manifest "$MANIFEST" \
        --output "$PILOT/${name}.json" --oracle-cache "$ORACLE" \
        --sessions 16 --duration-seconds 90 --window-seconds 10 \
        --concurrency 16 --arrival sync --seed 20276002 \
        --max-new-tokens 96 --authority-max-new-tokens 96 \
        --terminal-contract state-only --verifier-lanes "$lanes" \
        --cohort-commit-barrier --slo-seconds 1.9 --system revtrace \
        --low-margin-policy verify --proposer-device cuda:0 \
        --verifier-device cuda:1 "${extra[@]}" "${POLICY_ARGS[@]}" \
        >"$OUT/logs/pilot-cohort-${name}.log" 2>&1
}

run_cell lane2 2 0
run_cell lane4 4 0
run_cell lane2-spill 2 1
run_cell lane4-spill 4 1
touch "$PILOT/.complete"

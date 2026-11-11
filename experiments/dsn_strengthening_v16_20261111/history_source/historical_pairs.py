"""Pure functions for all110 frozen-metadata contrasts; root supplies frozen IO.

No frontier/window is used as a statistical unit. Exact sign calculations are
explicit exchangeability diagnostics: speakers co-served in the same physical
run are dependent, so these p-values cannot establish deployment generality.
"""
from collections import Counter, defaultdict
from itertools import combinations
from math import comb

ARMS = ("R0_S0", "R0_S1", "R1_S0", "R1_S1", "STANDARD_FULL")
RUN_METRICS = ("dual_credited_audio_seconds", "dual_audio_fraction", "display_P99",
               "commit_view_P99", "audio_rollback_events", "audio_rollback_seconds",
               "rollback_area_audio_seconds_x_wall_seconds", "erased_visible_characters",
               "physical_model_seconds", "physical_lease_seconds", "GPU_joules")
OP_METRICS = ("canonical_updates", "ahead_updates", "compatible_opportunities",
              "compatible_retained", "compatible_cleared", "incompatible_ahead_updates",
              "incompatible_cleared", "unresolved_ahead_updates")


def exact_sign_diagnostic(values):
    """Two-sided exact binomial sign test, excluding zero paired differences."""
    values = list(values)
    positive, negative = sum(x > 0 for x in values), sum(x < 0 for x in values)
    n = positive + negative
    numerator = min(2 * sum(comb(n, k) for k in range(min(positive, negative) + 1)), 2 ** n)
    return dict(positive=positive, negative=negative, zero=len(values) - n,
                nonzero_pairs=n, two_sided_p_exact_numerator=numerator,
                two_sided_p_exact_denominator=2 ** n,
                two_sided_p=numerator / 2 ** n,
                assumption="independent exchangeable paired signs; not established for co-served speakers",
                status="conditional diagnostic, not confirmatory deployment inference")


def audit_metadata(runs, opportunities, source_metrics):
    if len(runs) != 110 or len({r["cell_id"] for r in runs}) != 110:
        raise ValueError("expected exactly the original110 unique cells")
    if Counter(r["phase"] for r in runs) != {"primary": 60, "paired_jitter": 20, "coarse": 30}:
        raise ValueError("original phase denominators changed")
    run_by_id = {r["cell_id"]: r for r in runs}
    op_sum, op_source = defaultdict(Counter), {}
    for row in opportunities:
        if row["clock_scope"] != "consumer_apply": continue
        key = row["cell_id"], row["source_id"]
        if key in op_source: raise ValueError("duplicate Consumer opportunity source row")
        op_source[key] = row
        op_sum[row["cell_id"]].update({k: row[k] for k in OP_METRICS})
        if row["unresolved_ahead_updates"]:
            raise ValueError("UNKNOWN must be handled explicitly, never classified avoidable")
        if row["compatible_opportunities"] != row["compatible_retained"] + row["compatible_cleared"]:
            raise ValueError("compatibility count requires additional change/unmatched handling")
    blocks = defaultdict(dict)
    source_blocks = defaultdict(dict)
    for r in runs:
        block = blocks[r["paired_block"]]
        if r["arm"] in block: raise ValueError("duplicate arm in a five-arm block")
        block[r["arm"]] = dict(r, **{k: op_sum[r["cell_id"]][k] for k in OP_METRICS})
    if len(blocks) != 22: raise ValueError("expected22 original five-arm blocks")
    for s in source_metrics:
        r = run_by_id[s["cell_id"]]
        enriched = dict(s, **{k: r[k] for k in ("phase", "adapter", "rho", "arrival", "repeat", "paired_block")},
                        **{k: op_source[s["cell_id"], s["source_id"]][k] for k in OP_METRICS})
        key = r["paired_block"], s["source_id"]
        if s["arm"] in source_blocks[key]: raise ValueError("duplicate source/arm/block")
        source_blocks[key][s["arm"]] = enriched
    if len({s["speaker"] for s in source_metrics}) != 24:
        raise ValueError("24 acoustic speakers must remain24")
    result_blocks, pair_rows, factorial_rows = [], [], []
    metrics = RUN_METRICS + OP_METRICS
    for block_id, arms in sorted(blocks.items()):
        if set(arms) != set(ARMS): raise ValueError("incomplete five-arm block")
        first = arms[ARMS[0]]
        meta = {k: first[k] for k in ("phase", "adapter", "rho", "arrival", "cohort", "repeat")}
        for m in ("offered_audio_seconds", "sources", "whole_offered_frontiers"):
            if len({r[m] for r in arms.values()}) != 1: raise ValueError("arm denominators changed")
        result_blocks.append(dict(paired_block=block_id, **meta,
            arms={a: dict(cell_id=arms[a]["cell_id"],
                          **{m: arms[a].get(m) for m in metrics}) for a in ARMS}))
        for left, right in combinations(ARMS, 2):
            pair_rows.append(dict(paired_block=block_id, **meta, left=left, right=right,
                convention="right minus left",
                differences={m: None if arms[left].get(m) is None or arms[right].get(m) is None
                             else arms[right][m] - arms[left][m] for m in metrics}))
        factorial_rows.append(dict(paired_block=block_id, **meta,
            convention="R11 minus R10 minus R01 plus R00",
            interactions={m: None if any(arms[a].get(m) is None for a in ARMS[:4]) else
                arms["R1_S1"][m] - arms["R1_S0"][m] - arms["R0_S1"][m] + arms["R0_S0"][m]
                for m in metrics}))
    # Keep the ten predeclared strata separate; do not merge primary/coarse/jitter
    # or synthesize more speakers by concatenating source/run rows.
    speaker_groups = defaultdict(list)
    for (block, sid), arms in source_blocks.items():
        if set(arms) != set(ARMS): raise ValueError("missing source arm")
        first = arms[ARMS[0]]
        stratum = tuple(first[k] for k in ("phase", "adapter", "rho", "arrival"))
        for left, right in combinations(ARMS, 2):
            for m in ("dual_credited_audio_seconds", "dual_audio_fraction", "audio_rollback_events",
                      "compatible_cleared", "incompatible_cleared"):
                speaker_groups[stratum, left, right, m].append(dict(source_id=sid, speaker=first["speaker"],
                    cohort=first["cohort"], paired_block=block, difference=arms[right][m] - arms[left][m]))
    diagnostics = []
    for (stratum, left, right, metric), observations in sorted(speaker_groups.items()):
        if len({r["speaker"] for r in observations}) != len(observations):
            raise ValueError("merge repetitions within speaker before an exact sign diagnostic")
        diagnostics.append(dict(stratum=dict(zip(("phase", "adapter", "rho", "arrival"), stratum)),
            left=left, right=right, metric=metric, convention="right minus left",
            observations=observations, exact_sign_diagnostic=exact_sign_diagnostic(r["difference"] for r in observations)))
    return dict(cells=110, five_arm_blocks=22, acoustic_speakers=24,
                all_block_values=result_blocks, all220_paired_run_contrasts=pair_rows,
                all22_factorials=factorial_rows, source_paired_conditional_sign_diagnostics=diagnostics,
                inference_warning="No pooled significance claim:24 speakers share3 cohort service schedules;110 cells and offered windows do not create110 independent samples.")

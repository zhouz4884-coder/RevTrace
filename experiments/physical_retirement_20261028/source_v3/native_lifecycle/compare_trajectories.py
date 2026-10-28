"""Pair source-grounded cycle outcomes without filtering base-model failures.

This tool consumes independent audit JSONs. Different prior memories are the
effect under study; different actual source/request identities are not matched.
No oracle results enter the runtime or become substituted model outputs.
"""
import argparse
import json
from pathlib import Path


def compare(clean, changed):
    left = {r["cycle"]: r for r in clean["cycle_outcomes"]}
    right = {r["cycle"]: r for r in changed["cycle_outcomes"]}
    rows = []
    for cycle in sorted(set(left) | set(right)):
        a, b = left.get(cycle), right.get(cycle)
        matched = a is not None and b is not None and a["pair_key"] == b["pair_key"] and a["pair_key"]["source_sha256"] is not None
        row = {"cycle": cycle, "comparable_source_and_request": matched, "clean": a, "changed": b}
        if matched:
            row["clean_step_success_changed_failure"] = a["current_step_success"] and not b["current_step_success"]
            row["clean_failure_changed_success"] = not a["current_step_success"] and b["current_step_success"]
            row["both_fail"] = not a["current_step_success"] and not b["current_step_success"]
            row["both_success"] = a["current_step_success"] and b["current_step_success"]
            row["changed_has_valid_current_output"] = b["current_output_valid"]
            row["changed_repaired_invalid_prior"] = b["repair_observed"]
        rows.append(row)
    return {"rows": rows, "all_offered_cycles": len(rows),
            "comparable_cycles": sum(r["comparable_source_and_request"] for r in rows),
            "clean_audit_status": clean["status"], "changed_audit_status": changed["status"],
            "scope": "paired finite trajectories; no independence of cycles or permanent-harm inference; protocol and task outcomes remain separate"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("clean", type=Path); p.add_argument("changed", type=Path)
    a = p.parse_args()
    print(json.dumps(compare(json.loads(a.clean.read_text()), json.loads(a.changed.read_text())), indent=2))

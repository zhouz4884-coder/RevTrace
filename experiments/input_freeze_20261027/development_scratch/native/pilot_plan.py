"""Frozen, bounded native pilot plans and outcome gates; no GPU imports."""
from copy import deepcopy
import hashlib
import json

ARMS = {
    "candidate_only": {"mode": "minimal", "selection_mode": "candidate_only", "protected": False,
                       "required_roles": ["proposal"], "strict_required": False},
    "standard_direct": {"mode": "standard", "selection_mode": "direct", "protected": True,
                        "required_roles": ["authority"], "strict_required": False},
    "revtrace_direct": {"mode": "revtrace", "selection_mode": "direct", "protected": True,
                        "required_roles": ["authority"], "strict_required": False},
    "standard_strict": {"mode": "standard", "selection_mode": "strict_fallback", "protected": True,
                        "required_roles": ["proposal", "authority"], "strict_required": True},
    "revtrace_strict": {"mode": "revtrace", "selection_mode": "strict_fallback", "protected": True,
                        "required_roles": ["proposal", "authority"], "strict_required": True},
}


def hash_value(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def plan(tasks, stage, strict_go):
    assert stage in {"smoke", "development"}
    cells = []
    for repeat in range(1 if stage == "smoke" else 2):
        for ti, task in enumerate(tasks):
            conditions = ["clean"] if stage == "smoke" else ["clean", "cycle0_coherent"]
            for condition in conditions:
                names = list(ARMS)
                shift = (ti + repeat) % len(names)
                for name in names[shift:] + names[:shift]:
                    arm = ARMS[name]
                    cells.append({"id": f'{task["id"]}__{condition}__{name}__r{repeat}__unchanged',
                        "task": deepcopy(task), "condition": condition, "arm": name, "repeat": repeat,
                        "schedule": "unchanged", "eligible": not arm["strict_required"] or strict_go,
                        "skip_reason": None if not arm["strict_required"] or strict_go else "STRICT_PROVIDER_SELF_CHECK_NO_GO"})
    if stage == "development":
        for task in tasks:
            for name in ("standard_direct", "revtrace_direct"):
                cells.append({"id": f'{task["id"]}__clean__{name}__r0__crash-after-commit',
                    "task": deepcopy(task), "condition": "clean", "arm": name, "repeat": 0,
                    "schedule": "crash-after-commit", "eligible": True, "skip_reason": None})
    return cells


def cell_config(base, cell, runtime_source):
    cfg = deepcopy(base)
    arm = ARMS[cell["arm"]]
    cfg.update(mode=arm["mode"], repeat=cell["repeat"], runtime_source_path=str(runtime_source),
               adapter_module="revtrace_adapter", arm=cell["arm"], condition=cell["condition"])
    cfg["provider"]["selection_mode"] = arm["selection_mode"]
    cfg["provider"].pop("candidate_substitution", None)
    if cell["condition"] == "cycle0_coherent":
        cfg["provider"]["candidate_substitution"] = deepcopy(base["controlled_substitution"])
    cfg["candidate_fault_interpretation"] = (
        "not_exposed_direct_generation_does_not_read_candidate" if arm["selection_mode"] == "direct" else
        "one_frozen_cycle0_low_trust_return_replacement" if cell["condition"] != "clean" else "no_injection")
    return cfg


def self_check_gate(rows):
    direct = bool(rows) and all(r.get("actual_same_input") and r.get("calls_completed") for r in rows)
    strict = direct and all(r.get("full_stop") and r.get("repeat_tokens_equal") and r.get("self_verification_accepted") for r in rows)
    return {"direct_provider_go": direct, "strict_provider_go": strict,
            "strict_decision": "GO_BOUNDED_SELF_CHECK" if strict else "NO_GO_RETAINED_TF_OR_REPEAT_OR_STOP_DIFFERENCE",
            "scope": "same-input actual operator controls on development inputs; no general TF/autoregressive equivalence theorem"}


def evaluate_cell(cell, audit, runtime):
    arm = ARMS[cell["arm"]]
    bad = audit.get("violations", [])
    unknown = audit.get("unknown", [])
    if arm["protected"]:
        protocol = not bad and not unknown and audit.get("evidence_tier") == "ACTUAL_GPU_MODEL"
        gate = "PASS_PROTECTED_OBSERVATIONS" if protocol else "FAIL_OR_UNKNOWN_PROTECTED_EVIDENCE"
    else:
        allowed = all(x.startswith("unauthorized-state-admission:") for x in bad)
        protocol = allowed and not unknown and audit.get("evidence_tier") == "ACTUAL_GPU_MODEL"
        gate = "OBSERVED_UNPROTECTED_COUNTEREXAMPLE" if protocol and bad else "NO_ADMISSION_COUNTEREXAMPLE" if protocol else "FAIL_OR_UNKNOWN_NEGATIVE_CONTROL_EVIDENCE"
    complete = audit.get("native_multi_cycle_evidence_complete", False)
    return {"gate": gate, "audit_usable": protocol, "protected": arm["protected"],
            "native_multicycle_complete": complete, "offered_cycles": runtime["offered_cycles"],
            "committed_cycles": runtime["committed_cycles"], "unfulfilled_cycles": runtime["unfulfilled_cycles"],
            "task_success_cycles": sum(x["current_step_success"] for x in audit["cycle_outcomes"]),
            "current_output_valid_cycles": sum(x["current_output_valid"] for x in audit["cycle_outcomes"]),
            "fault_interpretation": "not_exposed_no_rejection_claim" if arm["selection_mode"] == "direct" else "actual_candidate_path",
            "verification_rejections": audit.get("verification_rejections_observed", 0)}


def smoke_gate(rows):
    failures = [r["id"] for r in rows if r.get("execution_status") == "FAILED" or
                r.get("evaluation", {}).get("audit_usable") is False]
    families = sorted({r["family"] for r in rows})
    missing = []
    for family in families:
        for arm in ("standard_direct", "revtrace_direct"):
            matches = [r for r in rows if r["family"] == family and r["arm"] == arm]
            if not matches or not all(r.get("evaluation", {}).get("native_multicycle_complete") for r in matches):
                missing.append(family + ":" + arm)
    ok = not failures and not missing and len(families) >= 2
    return {"status": "GO_FOR_SEPARATELY_REQUESTED_DEVELOPMENT" if ok else "REPAIR_OR_SCOPE_DECISION_REQUIRED",
            "failed_evidence_cells": failures, "missing_direct_native_lifecycles": missing,
            "development_automatically_started": False,
            "quality_scope": "base-model task errors retained; lifecycle gate is not a quality success or novelty claim"}

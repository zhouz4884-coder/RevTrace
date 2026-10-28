"""Two structural task families and objective scoring, independent of admission.

The oracle is for evaluation and the explicitly labelled CPU fixture only.
Production model outputs must never be replaced by oracle output.
"""
from __future__ import annotations

import itertools
import json
from copy import deepcopy


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def development_tasks():
    return [
        {
            "id": "ops-dev-0", "family": "runbook", "split": "development",
            "source": {"dependencies": {"inspect": [], "drain": ["inspect"],
                         "restart": ["drain"], "probe": ["restart"]}},
            "initial_memory": {"completed": [], "last_action": None},
            "requests": [{"action_budget": 1} for _ in range(3)],
            "revised_source": {"dependencies": {"inspect": ["isolate"], "isolate": [],
                                 "drain": ["inspect"], "restart": ["drain"], "probe": ["restart"]}},
        },
        {
            "id": "resource-dev-0", "family": "resource_plan", "split": "development",
            "source": {"capacity": 10, "jobs": {
                "alpha": {"cost": 4, "value": 7}, "beta": {"cost": 3, "value": 5},
                "gamma": {"cost": 2, "value": 4}, "delta": {"cost": 5, "value": 8}}},
            "initial_memory": {"reserved": [], "remaining": 10},
            "requests": [{"max_new_jobs": 1} for _ in range(3)],
            "revised_source": {"capacity": 8, "jobs": {
                "alpha": {"cost": 4, "value": 7}, "beta": {"cost": 3, "value": 5},
                "gamma": {"cost": 2, "value": 4}, "delta": {"cost": 5, "value": 8}}},
        },
    ]


def validate_schema(family, value):
    if not isinstance(value, dict):
        return False
    if family == "runbook":
        return (set(value) == {"completed", "last_action"}
                and isinstance(value["completed"], list)
                and all(isinstance(x, str) for x in value["completed"])
                and (value["last_action"] is None or isinstance(value["last_action"], str)))
    if family == "resource_plan":
        return (set(value) == {"reserved", "remaining"}
                and isinstance(value["reserved"], list)
                and all(isinstance(x, str) for x in value["reserved"])
                and type(value["remaining"]) is int)
    raise ValueError(family)


def validation_tasks():
    """Unseen structural instances, fixed before any model evaluation.

    Main harness must additionally check them against its full historical task
    manifest. Defining these here is not evidence of held-out execution.
    """
    return [
        {"id": "ops-val-fanin", "family": "runbook", "split": "validation",
         "source": {"dependencies": {"db_check": [], "cache_check": [], "backup": ["db_check"],
             "drain": ["cache_check"], "restart": ["backup", "drain"], "probe": ["restart"]}},
         "initial_memory": {"completed": [], "last_action": None},
         "requests": [{"action_budget": 1} for _ in range(4)],
         "revised_source": {"dependencies": {"db_check": ["isolate"], "isolate": [], "cache_check": [],
             "backup": ["db_check"], "drain": ["cache_check"], "restart": ["backup", "drain"], "probe": ["restart"]}}},
        {"id": "ops-val-diamond", "family": "runbook", "split": "validation",
         "source": {"dependencies": {"inventory": [], "network": ["inventory"], "rollback": ["inventory"],
             "deploy": ["network", "rollback"], "smoke": ["deploy"], "metrics": ["deploy"]}},
         "initial_memory": {"completed": ["inventory"], "last_action": "inventory"},
         "requests": [{"action_budget": 1} for _ in range(4)],
         "revised_source": {"dependencies": {"inventory": [], "network": ["inventory"], "rollback": ["inventory"],
             "capacity": ["inventory"], "deploy": ["network", "rollback", "capacity"], "smoke": ["deploy"], "metrics": ["deploy"]}}},
        {"id": "resource-val-bundle", "family": "resource_plan", "split": "validation",
         "source": {"capacity": 11, "jobs": {"heavy": {"cost": 7, "value": 12},
             "east": {"cost": 5, "value": 9}, "west": {"cost": 6, "value": 10},
             "tiny": {"cost": 2, "value": 2}, "small": {"cost": 3, "value": 4}}},
         "initial_memory": {"reserved": [], "remaining": 11},
         "requests": [{"max_new_jobs": 2}, {"max_new_jobs": 1}, {"max_new_jobs": 1}],
         "revised_source": {"capacity": 9, "jobs": {"heavy": {"cost": 7, "value": 12},
             "east": {"cost": 5, "value": 9}, "west": {"cost": 6, "value": 10},
             "tiny": {"cost": 2, "value": 2}, "small": {"cost": 3, "value": 4}}}},
        {"id": "resource-val-residual", "family": "resource_plan", "split": "validation",
         "source": {"capacity": 14, "jobs": {"large": {"cost": 8, "value": 13},
             "mid_a": {"cost": 7, "value": 12}, "mid_b": {"cost": 7, "value": 12},
             "small_a": {"cost": 3, "value": 5}, "small_b": {"cost": 3, "value": 5}}},
         "initial_memory": {"reserved": [], "remaining": 14},
         "requests": [{"max_new_jobs": 1}, {"max_new_jobs": 2}, {"max_new_jobs": 1}],
         "revised_source": {"capacity": 13, "jobs": {"large": {"cost": 8, "value": 13},
             "mid_a": {"cost": 7, "value": 12}, "mid_b": {"cost": 7, "value": 12},
             "small_a": {"cost": 3, "value": 5}, "small_b": {"cost": 3, "value": 5}}}},
    ]


def valid_prefix(family, source, memory):
    """Declared task repair: preserve the longest feasible recorded prefix.

    These are remembered plans, not irreversible real-world actions. A model may
    repair invalid stored plans. The gate itself never calls this function.
    """
    before = memory["completed"] if family == "runbook" else memory["reserved"]
    prefix, spent = [], 0
    for name in before:
        if name in prefix:
            break
        if family == "runbook":
            deps = source["dependencies"]
            if name not in deps or not set(deps[name]) <= set(prefix):
                break
        else:
            jobs = source["jobs"]
            if name not in jobs or spent + jobs[name]["cost"] > source["capacity"]:
                break
            spent += jobs[name]["cost"]
        prefix.append(name)
    return prefix


def score(family, source, prior, request, value):
    """Separate transition, stored-history and present-output task judgments.

    Per-step maximization is not claimed to be a multi-cycle optimal policy.
    Invalid prior memory does not force every later output to score as harmful.
    """
    if not validate_schema(family, value):
        return {"schema_valid": False, "current_output_valid": False, "transition_valid": False,
                "current_step_success": False, "source_grounded_prior_history": None, "reason": "schema"}
    prefix = valid_prefix(family, source, prior)
    if family == "runbook":
        deps = source["dependencies"]
        before, after = prior["completed"], value["completed"]
        action = value["last_action"]
        ready = [n for n, ps in deps.items() if n not in prefix and set(ps) <= set(prefix)]
        valid_prior = prefix == before
        output_valid = valid_prefix(family, source, value) == after
        output_valid = output_valid and (action is None or bool(after) and action == after[-1])
        if ready:
            transition = (action in ready and after == prefix + [action]
                          and request["action_budget"] >= 1)
        else:
            transition = after == prefix and action is None
        return {"schema_valid": True, "source_grounded_prior_history": valid_prior,
                "current_output_valid": output_valid, "transition_valid": transition,
                "current_step_success": output_valid and transition,
                "repair_needed": not valid_prior, "repair_observed": not valid_prior and output_valid,
                "preserved_valid_prefix": prefix, "eligible_actions": sorted(ready),
                "objective_scope": "one legal next step after declared invalid-suffix repair"}
    jobs, cap = source["jobs"], source["capacity"]
    before, after = prior["reserved"], value["reserved"]
    spent = sum(jobs[n]["cost"] for n in prefix)
    valid_prior = prefix == before and prior["remaining"] == cap - spent
    choices = []
    available = sorted(set(jobs) - set(prefix))
    for k in range(request["max_new_jobs"] + 1):
        for added in itertools.combinations(available, k):
            if spent + sum(jobs[n]["cost"] for n in added) <= cap:
                choices.append((sum(jobs[n]["value"] for n in added), added))
    best = max((v for v, _ in choices), default=0)
    subset = (len(after) == len(set(after)) and all(n in jobs for n in after)
              and after[:len(prefix)] == prefix)
    added = after[len(prefix):] if subset else []
    used = sum(jobs[n]["cost"] for n in after) if subset else cap + 1
    feasible = subset and len(added) <= request["max_new_jobs"] and used <= cap
    objective = sum(jobs[n]["value"] for n in added) if feasible else None
    output_valid = (valid_prefix(family, source, value) == after
                    and value["remaining"] == cap - sum(jobs[n]["cost"] for n in after))
    return {"schema_valid": True, "source_grounded_prior_history": valid_prior,
            "current_output_valid": output_valid,
            "transition_valid": feasible and value["remaining"] == cap - used,
            "newly_reserved_value": objective, "local_oracle_best_value": best,
            "current_step_success": feasible and output_valid and objective == best,
            "repair_needed": not valid_prior, "repair_observed": not valid_prior and output_valid,
            "preserved_valid_prefix": prefix,
            "objective_scope": "local constrained subset maximization; not multi-cycle optimality"}


def fixture_value(family, source, prior, request):
    """CPU fixture only. Never call from a real-model provider."""
    prefix = valid_prefix(family, source, prior)
    if family == "runbook":
        ready = sorted(n for n, ps in source["dependencies"].items()
                       if n not in prefix and set(ps) <= set(prefix))
        return {"completed": prefix + ready[:1],
                "last_action": ready[0] if ready else None}
    jobs, cap = source["jobs"], source["capacity"]
    spent = sum(jobs[n]["cost"] for n in prefix)
    candidates = []
    for k in range(request["max_new_jobs"] + 1):
        for new in itertools.combinations(sorted(set(jobs) - set(prefix)), k):
            if spent + sum(jobs[n]["cost"] for n in new) <= cap:
                candidates.append((sum(jobs[n]["value"] for n in new), new))
    new = sorted(candidates, key=lambda x: (-x[0], x[1]))[0][1]
    reserved = prefix + list(new)
    return {"reserved": reserved, "remaining": cap - sum(jobs[n]["cost"] for n in reserved)}


def messages(frozen):
    family = frozen["family"]
    instruction = (
        "Update runbook planning memory by recording exactly one next action whose dependencies are already recorded. "
        "Preserve the longest prefix of stored completed actions valid under the current dependency graph, discard any invalid suffix, "
        "and append one eligible next action; if none is eligible, append nothing. No real external command is executed by this task. "
        "Return JSON with exactly completed (string list) and last_action (string or null)."
        if family == "runbook" else
        "Reserve up to max_new_jobs previously unreserved jobs, maximizing newly reserved value within capacity. "
        "Preserve the longest prefix of stored reservations that has known unique jobs and fits current capacity; discard an invalid suffix. "
        "Then make the best additional subset for this request only and recompute remaining capacity. These are plans, not external allocations. "
        "Return JSON with exactly reserved (string list) and remaining (integer)."
    )
    return [{"role": "system", "content": instruction + " Do not include commentary."},
            {"role": "user", "content": canonical({k: frozen[k] for k in
              ("source", "prior_memory", "request")})}]


def trajectory_metrics(task, cycle, source, value):
    """Offline source-grounded global bound, never a policy/model input."""
    if not validate_schema(task["family"], value):
        return {"current_output_valid": False, "observed_objective": None, "global_bound": None}
    if task["family"] == "runbook":
        valid = valid_prefix("runbook", source, value) == value["completed"]
        initial = len(valid_prefix("runbook", source, task["initial_memory"]))
        bound = min(len(source["dependencies"]), initial + sum(r["action_budget"] for r in task["requests"][:cycle + 1]))
        observed = len(value["completed"]) if valid else None
        return {"current_output_valid": valid, "observed_objective": observed, "global_bound": bound,
                "objective_gap": None if observed is None else bound - observed,
                "scope": "maximum legal recorded progress through this many offered cycles; no runtime-performance claim"}
    jobs, cap = source["jobs"], source["capacity"]
    valid = (valid_prefix("resource_plan", source, value) == value["reserved"] and
             value["remaining"] == cap - sum(jobs[n]["cost"] for n in value["reserved"]))
    initial = valid_prefix("resource_plan", source, task["initial_memory"])
    slots = len(initial) + sum(r["max_new_jobs"] for r in task["requests"][:cycle + 1])
    upper = 0
    for n in range(min(slots, len(jobs)) + 1):
        for subset in itertools.combinations(jobs, n):
            if sum(jobs[x]["cost"] for x in subset) <= cap:
                upper = max(upper, sum(jobs[x]["value"] for x in subset))
    observed = sum(jobs[n]["value"] for n in value["reserved"]) if valid else None
    return {"current_output_valid": valid, "observed_objective": observed, "global_bound": upper,
            "objective_gap": None if observed is None else upper - observed,
            "scope": "offline current-source aggregate knapsack bound; not achieved multi-cycle optimality"}

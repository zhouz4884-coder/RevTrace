# Old native task fidelity checker

This independent standard-library CPU analysis compares all four original
sources and all 69 saved original-full neural calls with the original v8
sequential-r0 A/B histories, actual jobs, and canonical WAL. It performs no
neural inference and does not modify any execution source or old result.

Only the new cut's exact `contract.stage_execution` value may be removed.
Every other field, full selected C object, returned IDs, and appended text
must match. Source bindings remain. Original/new raw state hashes are checked
against their own complete states and are explicitly reported separately;
normalized hashes must match the prior original audit's state hashes.

The comparison fails for absent/extra/duplicate calls and unallowed field
changes. Seventeen CPU tests exercise valid tag-only projection and negative
mutations, including freshly rehashed but semantically changed states.
The formal runner reruns them on the clean manifest before reading results.

Invocation, only after allocation and the fresh full neural gate passes:

    python -B old_fidelity.py --plan PLAN.json --manifest SOURCE.json --out NEW_OUTPUT

All dependencies are read once, hashed, and checked again for mutation before
PASS. The completed output contains config, environment, run record, input
manifest, CPU logs, 69 value comparisons, summary, and gate. A failed analysis
preserves the error and inputs; it never restarts inference or changes metrics.

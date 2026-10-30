# Owned full-call refinement specification

Finite symbolic complete cuts, two physical workers, typed provisional projections,
original C/U allowed transitions, current-parent-only durable writes, independent
Consumer applications, incarnation/epoch fences, and same-storage recovery.

The external Supervisor, ingress clocks and Consumer survive Owner/worker faults.
Worker-only failure preserves already owned closed buffers. Recovery discards
uncommitted old-epoch outputs and replays durable facts without new neural work.

Original C/U is nondeterministic. A bit represents a whole opaque state; visible
text equality is deliberately weaker. This is not replay equality or extracted
Python/CUDA verification. Bounded exploration reports its exact bounds. Named
controls include semantically illegal mutants and progress after local rejection,
worker restart and recovery. They are controlled specification evidence, not
natural failure frequency or serving latency measurements.

Before actual execution, commit/freeze the complete source, import its bundle,
verify source identity, freeze plan/environment/run record, and place all formal
raw results on the designated experiment disk. Run only run_checks.py with the
frozen --plan, --manifest and exclusive --out. Source correspondence and runtime
trace checking must be linked separately to the final frozen runtime.

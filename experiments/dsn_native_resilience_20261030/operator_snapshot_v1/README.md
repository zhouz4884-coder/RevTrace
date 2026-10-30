# Frozen short-development campaign operator

This source is the process operator, not the neural runtime. Production CLI
accepts frozen9492d3f9cb35e2b2849ec020817750a221248f0e, its complete59 source
files and the unchanged six-cell short development plan. Operator and neural
source identities stay separate.

    python -B run_campaign.py --plan SHORT_PILOT_v1_FROZEN.json --manifest OPERATOR_SOURCE_v1.json --prerequisite RUNTIME_PREREQUISITE_v1_r2.json --prerequisite-sha256 SHA256 --out PLAN_RAW_RESULT_LOCATION

The operator validates its clean full source, neural source, all six configs,
exact prerequisite and complete zero-skip CPU gate, environment, reference,
and GPU release before serial calls to original resilience_trial.py. It does
no model, dataset, download or CPU-analysis work while a timed child runs.
Only bounded atomic progress metadata is written during a child.

A complete contiguous prefix from another launcher is adopted only after
source/config/task/reference/GPU checks. Such entries retain external-launch
provenance. Failed, incomplete, non-prefix or already operated campaigns are
never restarted, rerun, reordered or skipped. The first child failure retains
the validated prefix. HANDLE remains the root launcher's responsibility.

Cold-fault P99 failure stays an endpoint, not a task-fidelity failure. Separate
trace refinement, formal24 and sustained validation are not claimed here.

CPU tests use synthetic schema fixtures and tiny real subprocesses. They load
no trained model, query no real GPU and produce no serving evidence. The
production CLI exposes no fixture-source, mock-GPU or commit-override flag.
All actual raw logs/results remain on the designated8TB experiment disk.

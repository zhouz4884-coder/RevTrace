# RevTrace v16 pilot and new-runtime reference driver

This package adapts the old six-file confirmation driver and continuous/restored
reference generator. Actual neural runtime is immutable
`de0936b2e30179d63aeef6e235cd1af685578c58` (66 files), not original NN4f.
All reference outputs must be newly generated under that actual runtime; old
receipts or complete-state source markers are rejected. No reference inference
or GPU service was executed while preparing this source.

Main arms are conservative/dependency_versioned/ready_only/fullcall/uir. Strict
birth-root safe_versioned is auxiliary. Existing-bank pilot uses two metadata
chosen speakers, six arms and two fresh repeats:24 trials,20 main+4 auxiliary.
Each speaker's seeded r0 permutation is exactly reversed at r1; primary GPU
rotates0→1. Existing eight-source phase has96 total (80 main+16 auxiliary).
New confirmatory speakers initially use five main arms only,10*N. Speaker is
the acoustic cluster; the reused pilot bank adds zero independent speakers.

All durations retain16kHz/500ms/8000-sample cadence and original partial EOS.
Every selected/returned/abandoned/lifecycle/pending job has disjoint accounting;
promotions are annotations. Ready-reuse0 requests timing audit and proves no
policy equivalence. Resource drift>2% requests diagnosis while retaining every
outcome. UIR disables cooperative cancellation only; original input/AU/SUP and
durability checks remain required. Unsafe UseAll is never a live arm.

`prepare_pilot.py` is metadata-only: binds current byte/environment readiness,
freezes metadata-first four existing speakers for measured references and their
first two for the prospective24-cell pilot, builds a fresh actualv3 reference
plan, and reserves service paths. It does not create a reference PASS receipt
or actual service config before new references pass. Full4 references remain
available for the separate forthcoming2/4-session resource phase.

After measured full4 PASS, `bind_reference_subset.py` filters exact original row
objects and genesis for the already fixed first2. The child has a distinct
derived-binding status, parent reference/selection/bank hashes, and zero *new*
model calls; the full parent retains all paid reference energy/call costs.
Binding revalidates the full measured parent, exact source markers, full rows,
complete500ms/EOS chain, and metadata-first4/first2 scope. No row/state/C/ID can
be edited and rehashed into a valid child. This is scope derivation, not new
neural verification or a serving result.

Root then runs `make_prelaunch.py` using a CURRENT/no-argumentde0936 gate and a
separate explicit driver source gate; runs `run_reference.py`; after its PASS,
runs `make_service_plan.py`; creates the service prelaunch and invokes
`run_confirmation.py`. Production support `a13fa0a...` stays byte-matched and
supplies actual Consumer endpoints, complete-state/C/ID audit, both-board power,
allocator observations and ownership-bound cleanup. Reference cost is separate
paid work. SLO misses and ties continue the complete queue.

`run_cpu_controls.py` checks clean complete driver/runtime/support identities,
parses every Python source, blocks neural imports, and exercises matrix,
reference/provenance rejection, prelaunch and actual synthetic Owner→WAL→raw
accounting integration. CPU success is not neural/task-performance evidence.


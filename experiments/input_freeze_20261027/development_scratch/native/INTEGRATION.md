# Objective 6 implementation handoff

This directory is an uncommitted temporary implementation for parent review.
It is not a new GPU evidence release and not an executed native lifecycle study.
Before research execution: integrate into an isolated source tree, freeze the
full source/config/environment identity and the experiment/raw/summary/gate paths.

## Implemented

- `tasks.py`: dependency/runbook and capacity-constrained reservation families,
  three successive actual read/write operations, objective validators independent
  of admission. Oracle output is restricted to the explicitly named CPU fixture.
- `native_store.py`: persistent application.sqlite, separate checkpoint file;
  immutable input freeze, owned selection registration, atomic source/parent/epoch
  checks, historical receipt lookup, outbox/receiver, recorded application effects.
- `native_workflow.py`: audited LangGraph functional task API. First operation
  suspends after selection or exits after application commit; fresh process
  resumes the same native thread. Two further requests consume committed memory
  and write back new state. All processes and task executions are recorded.
- `independent_checker.py`: reconstructs state from events and actual SQL rows,
  checks input/receipt/source/parent/epoch/content independently. It imports no
  production admission or transition code. Missing independent GPU tokenizer or
  renderer emits UNKNOWN. Task correctness remains a separate result.
- `actual_provider.py`: actual FP32 authority generation; actual proposal then
  correct-context full-token/Stop verification with real fallback; fixed low-trust
  JSON return substitution and candidate-only negative arm. Model asset manifest
  is byte verified, selector settings are frozen, unsupported processors fail.
  Complete raw calls, consumed tensors, tokens, Stop, value, timestamps, GPU
  seconds and model-load time are returned. No task oracle is used by this file.
- `revtrace_adapter.py`: real production composed kernel gates before the actual
  provider call, then complete/drain receipts. Install after native resume restores
  complete durable history and actual input obligations, replays the already
  executed owned receipt, and issues admission/sync/install/publication/read/apply.
  Receipt replay restores the latest real head without re-applying the old write.
- `independent_codec.py`: tokenizer and render reconstruction, with verified model
  assets, for the read-only checker.
- `test_native.py`: 20 pure SQLite/provider-fixture/checker/actual-kernel checks
  passed. This includes real child-process exit after SQLite commit and kernel
  recovery. The 16 native LangGraph tests remain unexecuted/skipped because the
  dependency is absent in this local interpreter. This is still CPU evidence.

## Quality and pairing contracts (tightened before GPU execution)

Quality no longer has an ambiguous `correct` flag. Each selected output reports
source-grounded prior history, current-output validity, transition validity,
current-step success, and observed repair separately. Invalid prior memory does
not force every future output to fail: these tasks explicitly allow the model to
discard an invalid suffix of a remembered plan, preserve its longest valid prefix,
and generate a new valid step. This is task behavior shared by every arm; the
protocol gate never repairs a model value or invokes the task oracle.

These are runbook/project planning memories, not irreversible external commands
or physical resource allocations. Per-step resource maximization is deliberately
not described as multi-cycle optimality. `trajectory_metrics` reports a distinct
offline global bound. A regression test has three locally successful decisions
with total value23 while the global bound is24.

Four validation instances are fixed in `validation_tasks()` (fanin/diamond DAGs,
bundle/residual knapsack) before model use. The main controller must still verify
their independence against the complete historical manifest. `compare_trajectories`
pairs only identical actual source/request keys, allows prior memory to differ as
the effect of previous writes, retains clean-arm failures and records repair.
Missing, rejected and unfulfilled cycles remain in the offered-cycle denominator.

Controlled candidate substitution has frozen `on_cycles` (default `[0]`) and can
provide distinct fixed JSON via `by_family`. Later cycles use the real model
without reinjection, so their observed changes are not silently new fault inputs.
The injector is the experimental harness; trusted selection does not use those
fault labels for its decision.

The lifecycle output separates offered cycles, committed cycles, failed cycles,
rejected attempts, fresh retries, actual model calls, completed GPU compute,
asset-validation time, model-load time and full child-process wall. It never calls
loop completion three successful writes. GPU energy requires the parent's actual
recorded external sampler and is explicitly unknown in this module alone.

Tests locate runtime source via `REVTRACE_RUNTIME_SOURCE` or the integrated
`../runtime/src` default. A required production kernel missing from that location
is a test failure, not a skip. Only absent local LangGraph may skip native tests;
the fixed Linux study environment must execute them.

## Actual-model provider interface

Set provider config `kind=actual_model`, `module=<reviewed module>`, and a fixed
`identity`. Factory `create_provider(config)` returns an object with:

1. `tier == ACTUAL_GPU_MODEL`;
2. `prepare(frozen)` returns actual model input IDs, messages, frozen_request_hash;
3. `generate(request)` returns actual consumed input IDs, complete token sequence,
   explicit Stop/EOS/budget contract, independently reproducible rendered JSON,
   selected value, actual timing and paid GPU cost. See registration's required
   fields. The provider must report malformed/capped output as a retained result
   with an explicit unfulfilled request rather than silently synthesize an answer.

Structural/Stop/budget errors are explicitly unfulfilled, retaining original
tokens and raw decoded content. Provider exceptions retain completed calls and
mark the failing call cost unknown. The controller must retain all such cells
in denominators; it must not drop them or label retry work free. If an intended
post-commit crash cannot be reached because generation is unfulfilled, the driver
records that fault point as not reached rather than claiming a crash experiment.

For a process-persistent GPU actor, the factory can connect to an already owned
worker. Its request/result provenance, worker lifecycle and costs must be checked
and frozen. A `provider_identity` string is not cryptographic attestation. Threat
model remains trusted host/provider wrappers and intact local storage.

## RevTrace integration is mandatory before comparison

Set `mode=revtrace`, `adapter_module=revtrace_adapter` and the frozen
`runtime_source_path=.../runtime/src`. The supplied adapter reconstructs all
durable records and accepted-input obligations, invokes the real kernel and
records exact kernel source identity. A missing actual pre-execution lifecycle
receipt is rejected. Keep these checks when integrating it into the research tree.

The application DB is transactional but independent of LangGraph checkpoints.
The receiver is a local durable receipt projection, not a claim of exactly-once
arbitrary remote side effects. Actual subsequent model input is proved by the
following provider call's consumed-ID receipt, separately from outbox delivery.

## Formal draft

The formal files in this directory are retained early drafts. The owning formal
agent has produced the separate frozen formal_v1 source996430d; use that source
and its own exact execution receipts for the study. Do not promote these earlier
unexecuted draft files based on the other source's tool results.

`AdmissionLifecycle.tla/.cfg` describes bounded frozen-source/selected-content,
epoch, WAL/install/publication, source mutation, one crash and original receipt
replay. Each guard can be disabled in a copied config to obtain a diagnostic
counterexample. `LegalSelection.tla` separates safety from candidate-selection
completeness and includes a latest-only negative configuration. Fairness is
declared for eventual progress; there is no deadline or worst-case cost theorem.

These files have NOT been parsed/run by TLC or TLAPS. No TLA tool is available
in this subagent's checked environment. Do not call the draft a checked proof.
Before use: run SANY/TLC with version/hash capture, retain witnesses and state
counts, check against actual traces, then prove parameterized induction lemmas
in TLAPS for the chosen invariant. Finite checking alone is not a parameterized
proof or full-stack implementation refinement.

## Remaining work

- Native pinned dependency install and execute 16 actual CPU lifecycle tests.
- Actual provider/kernel/codec review and bounded real GPU environment validation.
- Freeze genuinely independent task instances in both structural families.
- Real multi-cycle GPU execution, base-model-error retention, same-input controls,
  cost/power records, actual propagation/harm recount.
- Run formal tools, fix any counterexamples, and produce explicit scope table.

No paper/source repository or GPU state was changed during this temp handoff.

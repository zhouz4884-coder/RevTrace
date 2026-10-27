# RevTrace frozen formal study v1

This source extends the already executed Python/JS models with real TLA+/TLC checks and separate parameterized TLAPS obligations. It does not claim that finite TLC enumeration proves the production Python/CUDA program. Standard can implement the same predicates.

## Premises and implementation mapping

- One serialized Owner and immutable job registry. `Freeze` records actual parent version/projection, owner epoch, read-source version and admitted interval before selection.
- `Select` abstracts trusted execution or a verifier satisfying its own complete-token/stop/Phi contract. It does not model neural arithmetic, GPU attestation, truthful recognition or model termination. `selectedZ` is trusted; `returned` can be coherently changed independently.
- `Phi` is deterministic under the fixed actual adapter contract. The finite model uses a small total projection `(p+z)%3` to expose dependencies; it is not claimed to numerically emulate Qwen. The parameterized proof treats `Phi` as an arbitrary fixed operator.
- Successful atomic WAL sync and intact persistent state are modeled by one durable append. Real write/fsync failure behavior and torn-frame checks have separate runtime tests. Group fsync is not inferred globally atomic across sessions.
- Acknowledged input prefixes survive restart independently of Canonical progress. Original input debt is not reset to the smaller certified frontier.
- `Publish` abstracts the actual trusted Consumer's application after installation, not network enqueue. Network faults and browser guarantees are outside scope.
- New writes require current epoch; exact historical receipt retrieval preserves its original fields and need not equal today's owner epoch.

Source mapping: `live_qwen._make_job` / frozen dispatch → Freeze; actual trusted selection/complete row → Select; existing `dgft`/D1 validation → Guard; `durable_journal` → SyncAdmission; installation and actual Consumer → Install/Publish; input journal → Accept/Recover; exact durable retry lookup → Replay. This is a correspondence map, not a checked refinement.

## Finite TLC cuts

Admission: two jobs, selected values {0,1}, three possible feedback projections, two audio units, one source-version change, at most one crash and two epochs. Explore all reachable interleavings under these bounds, including coherent returned-content mutation, independent projection corruption, incomplete stop evidence, sync-before-install gaps, crashes, retries and recovery. Preserve eight individual guard-deletion runs and their concrete counterexamples.

The bounded job and audio universes can terminate; `Spec` permits final stuttering. Configurations therefore disable TLC's additional deadlock diagnostic while continuing to check every stated invariant and temporal property. No deadlock-freedom or eventual completion of all accepted work is claimed: exhausted job identities after a stale-write rejection would require a replenishment/fair-execution model. The explicit liveness claims concern recovery and already durable facts only.

Selection: three typed nodes (an actual boundary node, an older complete legal preview, and a latest candidate). Compatibility checks session/epoch, complete received registered authorized nodes, exact boundary projection/frontier, predecessor identities, strictly increasing intervals and matching edge projections/generation. Seven fixed scenarios exercise wrong root, incomplete output, different session, old epoch, broken edge, revoked candidates and a fully legal latest candidate. Enumerate arrival orders and finite waits. Full scan must be safe, nonempty when a legal registered candidate exists, and maximal by frontier. Latest-safe is expected to preserve safety while violating completeness on the older-preview witness; unsafe-latest is expected to violate safety. This is the structural shape of LP1 S, not a new neural realization or prevalence count.

Wait: two finite budget decrements, unchanged trusted state/debt, no frozen job while waiting. Weak fairness ensures eventual dispatch in the bounded model. An explicit real-clock action can still pass the service deadline before dispatch; the negative timing configuration is expected to fail. Safety and eventual progress do not imply a service-time bound.

## Parameterized TLAPS obligations

1. Empty history satisfies the defined entry/identity invariant.
2. Functional append preserves every old record exactly.
3. Current parent/frontier/projection/selection/complete/epoch/source checks establish the next record's obligations.
4. A fresh guarded append preserves the whole arbitrary finite history, including ancestry, contiguity, selection and unique identity.
5. An old epoch cannot pass a new-write guard.
6. Identity lookup in a unique history returns the exact original receipt, without a current-owner condition.
7. Copying a validated durable prefix preserves its original record invariants.
8. Incremental legal-candidate scan preserves safety, completeness and frontier maximality for an arbitrary eligible predicate; the concrete bounded predicate is in LegalSelection.
9. A positive bounded-wait step preserves Canonical/durable/input state and decreases a natural-number variant.

The proofs must execute with TLAPS. A theorem left unproved remains unproved; do not substitute successful TLC runs or a tautological assumption of the desired postcondition. Parameterized append/scan induction steps are not an automatically checked proof of all production transitions, scheduler deadlines, arbitrary graphs or end-to-end cryptographic guarantees.

## Freeze and execution

Before TLC/TLAPS: commit all .tla/.cfg/protocol/build files into a standalone source Git history; record byte hashes, full source commit, installed tool receipt/hash, run ID, finite constants, environment, CPU limits, raw result path and intended decisions. Use a fresh 8 TB result directory. Single TLC worker, bounded heap, subprocess timeout. No GPU and no measurement overlap without parent scheduling approval.

Every negative run counts as successful counterexample coverage only if its expected named invariant is actually violated; parser errors, missing tools, timeout and unrelated invariants are failures/unknown. Preserve stdout/stderr and failed versions. Retain model-generated counterexample state traces. A complete-tooling smoke is not one of these study results.

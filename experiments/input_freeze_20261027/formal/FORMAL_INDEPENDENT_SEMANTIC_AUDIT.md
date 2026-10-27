# Read-only semantic audit of formal_v1

Reviewer: native_formal_next (separate from formal implementation/execution).
Files read: PROTOCOL.md, ProtocolProofs.tla, AdmissionLifecycle.tla,
LegalSelection.tla, BoundedWait.tla, run_formal.py. No model checks or GPU runs
were started by this review. Reported TLAPS/TLC execution counts must be taken
from the owning agent's exact-source execution receipts, not from this review.

## Decision

No contradiction found in the stated conditional lemmas or bounded model scope.
The scripts provide meaningful safety/selection counterexample tests, plus
parameterized induction steps. They do not establish full Python/CUDA refinement,
all accepted-work liveness, arbitrary-graph selection completeness or a deadline
guarantee. Those exclusions are already stated in PROTOCOL.md and must remain in
the final Property / Premise / Witness / Scope table.

## Checks that matter

1. **Append proof is conditional, not vacuously the postcondition.** Guard exposes
   individual parent/frontier/Phi/selection/completeness/source/epoch checks and
   identity freshness. HistOK of the old history plus those checks proves the
   new entry and preservation of prior entries. GuardSuppliesNewEntry is close
   to definition expansion; the substantive obligation is arbitrary finite
   history append including contiguity and unique identity. A proof of this
   algebraic implication does not prove the runtime actually implements Guard.

2. **Selection is explicitly trusted.** The concrete model treats selectedZ as
   trusted and allows returned Z/P corruption. It tests consistency binding and
   missing evidence; it does not prove neural truth, complete numerical greedy
   equivalence, GPU origin attestation, or an honest trusted host. Parameterized
   Phi is fixed, as needed for the append relation.

3. **Durable/current owner distinctions are correct.** EntryOK stores owner at
   commit and observedOwner at that historical commit. HistOK does not compare
   historical owners with today's epoch. Receipt retrieval returns the unique
   original entry; the old-epoch guard rejects new appends. This avoids the
   earlier native CPU v1 error of revoking legitimate historical facts on owner
   rotation.

4. **Debt recovery is separately represented.** accepted is volatile and reset
   by Crash; durableAccepted survives. Recover normally restores the original
   accepted input prefix, while the negative guard case only restores the
   smaller committed frontier. This distinguishes missing obligation accounting
   from merely replaying canonical records.

5. **LegalSelection represents a real type of witness, with finite limits.**
   Root/older/latest carry session, epoch, generation, source and target
   frontiers, P, predecessor identity, received/registered/authorized/complete
   predicates. The older legal preview remains reachable through an actual
   boundary node when newest is incompatible. Latest-safe can be safe while
   losing legal progress. The finite model waits for all three nodes before
   choosing; it does not prove that a live selector must wait for all possible
   future arrivals, nor that it is complete over unobserved candidates.

6. **The scan lemma assumes a fixed Eligible/Frontier view.** It proves one
   insertion preserves Best for an arbitrary predicate under its listed domain
   assumptions. A runtime scan concurrent with parent changes or revocations
   needs a stable snapshot/serialization and apply-time validation; that link
   is not supplied by the lemma alone. This is a scope requirement, not a wrong
   theorem.

7. **Fairness is distinct from deadlines.** BoundedWait's Wait step preserves
   canonical/debt and decreases the natural-number budget. Weak fairness gives
   eventual dispatch, without bounding how many real ClockTick steps precede
   it. The negative deadline configuration therefore addresses a real missing
   implication rather than an artificial arithmetic failure. No wait-performance
   benefit follows from these frame/variant lemmas.

8. **Admission liveness is restricted appropriately.** With a finite job set,
   stale jobs may exhaust identities and accepted work need not complete. The
   protocol explicitly restricts FairSpec claims to recovery and already-durable
   facts. CHECK_DEADLOCK FALSE is acceptable for final stuttering under these
   claims; it would be insufficient for a claimed deadlock-free service.

## Presentation and integration caveats

- D1 token-to-text / trusted renderer correctness is outside EntryOK's current
  Z/P fields. The model's source map mentions D1, but its claims must not say
  TLAPS independently proved text rendering or arbitrary Consumer text.
- ReceiptIsHistorical proves historical membership and preservation. It does
  not itself prove that no caller can confuse that receipt with eligibility of
  a new current input. The native runtime/checker must separately demonstrate
  the input-freeze/current-source boundary.
- In the model Truncate means missing declared complete-selection evidence.
  It must not automatically be identified with every budget-capped output in
  earlier ASR studies: some historical contracts deliberately admitted a fully
  evidenced budget termination. Match the declared Stop contract to each run.
- Publish abstracts actual trusted application after installation. It contains
  no network or browser queue, consumer restart implementation, or arbitrary
  remote exactly-once side effect. Runtime receipts are still needed.
- The latest-safe counterexample and guard-deletion traces establish insufficiency
  of those specified observations/rules in this model. They do not establish
  that all implementations must use RevTrace's names or exact data structures.

## Runner review

run_formal.py checks source/tool hashes, captures exact commands and raw output,
uses one TLC worker and bounded timeouts, and only counts a negative test when
the expected named invariant is reported violated. Parser error, timeout or an
unrelated invariant cannot substitute for the target counterexample. The tool
success condition remains a claim only about the named frozen modules.

No source edit is required by this review. The caveats above are required when
integrating the eventual tool receipts into a broader contribution claim.

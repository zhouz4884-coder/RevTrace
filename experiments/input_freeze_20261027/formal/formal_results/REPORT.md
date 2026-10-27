# RevTrace: actual TLA+/TLC and TLAPS results

Frozen source: `996430d24d110facb242b352ba69c2f42f26e69c`; source/config/controller manifest SHA256 `b61179e8b8449fd07a2bbebef3aea9ec3f305dd9caebe86a1e7ca11926d98f6a`. Complete source history is in `FORMAL_SOURCE_v5.bundle` beside this directory. The `formal_v1/` source folder name is a local project name; the actual commit and remote `source_v5` identify the executed bytes.

Raw root: `/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/freeze_boundary_20261027/formal/full_v5`.

Actual study results: **21/21 frozen TLC configurations matched their expected outcomes: 10 positive checks and 11 specific negative counterexamples. TLAPS proved 20 obligations covering 10 named parameterized theorems.** These are separate from earlier tool smoke and from the repeated development pilots. The controller exited and its PID was absent on the terminal check. No GPU work was performed.

The independent result recount reads the real stdout/stderr and source bytes, rechecks expected named violations, complete config membership, state counts and SHA256. It covers 321 bounded files / 803,284 bytes including failed versions. It is a separate analysis implementation, not an independent theorem prover or author-independent verification.

## What the finite models actually cover

| Model/cut | Actual result | Declared scope |
|---|---|---|
| Admission safety | 175,980 distinct states; 1,179,230 generated; no monitored violation | Two job identities, two selected values, three projections, two audio units, one source change and one crash |
| Admission with weak fairness | Same 175,980 state space; recovery and already-durable visibility properties pass | Fair Recover/Install/Publish; no bounded service-time or all-accepted-input completion theorem |
| Eight one-rule omissions | Named ancestry, writer-epoch, source, selected-content, projection, completeness, durable-view and input-debt violations | Executable counterexamples in this abstraction; not natural failures or universal necessity of each exact implementation guard |
| Seven typed maximum-selection scenarios | Each 25 states; safe choice, completeness, maximum frontier and eventual decision pass | Received/registered/authorized complete candidate nodes, exact boundary projection and edge chain; wrong-root, incomplete, other-session, old-epoch, broken-edge, revoked and fully legal latest cases |
| Latest-safe selection | Completeness counterexample: a legal older preview exists but choosing only the newest yields none | Safe rejection and maximal legal progress are different properties |
| Unsafe latest selection | Actual SafeChoice counterexample | Newest/highest frontier alone is insufficient |
| Bounded wait | 16 states; no admission/debt change and fair eventual dispatch pass | One local finite wait budget; no new job frozen during waiting |
| Bounded wait plus deadline assertion | DeadlineAlwaysMet counterexample, 6 states reached | Weak fairness and finite step count do not imply a wall-clock deadline |

TLC's extra deadlock diagnostic is explicitly disabled because the finite job/audio sets can terminate and `[][Next]_vars` permits final stuttering. This does not assert deadlock freedom. In particular, an exhausted finite job-ID set after stale rejection is not modeled as an endless service with automatic job replenishment. The accepted-input debt safety property remains active; eventual completion of all accepted work is not claimed.

The typed selection case is no longer `Legal(c)==1`. It checks session/epoch, complete and registered evidence, revocation, exact Canonical-boundary output projection, predecessor identity, contiguous increasing intervals and matching projection/generation along a bounded path. Its older-preview scenario corresponds to the already documented LP1 S structural gap. This new model is not an additional neural occurrence. The existing full CPU native fixture (Canonical 960 versus legal older view 1120) and 14 prior real-trace registered opportunities remain their own evidence tiers; none supplied new first-2s credit.

## What TLAPS actually proved

The module `ProtocolProofs.tla` contains 10 named theorems, each generating two proof obligations under the installed tool:

1. `GenesisSafe`: the empty indexed history meets the defined invariant.
2. `AppendFrame`: appending one entry preserves every old indexed record.
3. `GuardSuppliesNewEntry`: current parent/frontier/projection, trusted selected content, complete result, source and epoch checks supply the new entry's obligations.
4. `GuardedAppendPreservesHistory`: these guards plus fresh transaction identity preserve an arbitrary finite history's ancestry, contiguity, selected/projection binding and unique identity.
5. `OldWriterCannotAppend`: a result naming a different prior epoch cannot pass the new-write guard.
6. `HistoricalReceiptReturnsUniqueOriginal`: a unique matching durable identity returns its exact original record, without requiring its historical owner to equal today's owner.
7. `RecoveredPrefixPreservesOriginalFields`: exact prefix reconstruction preserves the history's original entry properties.
8. `EmptyScan`: the empty legal-candidate scan has the correct empty result.
9. `MaximumLegalScanStep`: adding a candidate preserves a scan's safe, complete, frontier-maximal answer for the declared eligible predicate.
10. `BoundedWaitPreservesTrustedStateAndDecreasesBudget`: a positive wait step leaves trusted Canonical/durable/input state unchanged and decreases its natural-number variant.

The guarded append result proves an inductive step; it does not assume its postcondition. The selection result proves a generic scan step, not a novel indexing algorithm. `Eligible` and `Frontier` are abstract in that lemma; the concrete finite predicate is checked separately in `LegalSelection`. `Phi` is an arbitrary fixed operator in the parameterized proof; neural truth and floating-point equivalence remain trust/execution premises.

Actual tool command: TLAPS 1.5.0, `--threads 1 --nofp --timing`, default SMT/Z3 4.8.9. The proof manager reports `All 20 obligations proved`, exit 0. The optional Isabelle `-C` proof-rechecking flag was **not** used. TLC was 2.19 from stable release 1.7.4, one worker and 1 GiB heap; full tool hashes and environment are in `full_v5/ENVIRONMENT.json` and the tooling receipt.

## Assumptions, correspondence and remaining obligations

- Trusted selection or a verifier satisfying its declared reference contract; immutable job/actual-input identity; deterministic declared adapter; one serialized Owner; successful durable append; intact recoverable input/storage; actual ordered local Consumer.
- The lifecycle graph models successful persistence as an atomic durable step. Torn frames, write failures, multi-session group sync, CUDA execution, networking, Python runtime races and operating-system fault isolation are not refined by this graph.
- The old writer remains represented in the model after a crash so the epoch guard can be removed in a negative control. Production registry fencing may reject it earlier. Therefore these omissions do not prove every implementation must place the same check at the same boundary.
- The parameterized lemmas and finite liveness checks are not a machine-checked proof of every transition in the real Python program, all graph depths or unbounded service availability.
- No deadline theorem, recognition-quality theorem, natural incident rate or universal need for a uniquely named RevTrace component follows.

The separate native/formal agent completed a read-only semantic review of the frozen modules and controller: `FORMAL_INDEPENDENT_SEMANTIC_AUDIT.md`, SHA256 `73a52c180df17d212ec7e8be80808dec3825eb3865db87507f6c71f08c4ad1f6`. It found no incorrect lemma or model bug requiring a source revision. This is a separate agent's logical review, not a second theorem-prover implementation or independent experimental rerun.

Three integration limits from that review are mandatory: EntryOK does not independently prove D1 token-to-text rendering; historical receipt membership does not establish eligibility of a new current input; and `Truncate` here means missing complete-selection evidence, whereas an earlier ASR contract can legally accept a fully evidenced budget-terminated output. The maximum-selection scan also assumes a fixed snapshot of Eligible/Frontier; parent/revocation races still require runtime serialization and apply-time validation.

## Preserved failures and documentation details

`pilot_v1` and `pilot_v2` retain two empty-sequence lexical failures. `pilot_v3` retains the bounded terminal-state deadlock diagnostic, followed by the explicit stuttering configuration. `pilot_v4` passed its three predeclared configurations before the full matrix. The parameterized proof module itself was unchanged and passed in each attempt; repeated checks are not extra distinct theorems.

The launch handle's scope text for `full_v5` accidentally retains the word “pilot”; its actual argv, run FREEZE, stage=full, 21-config completion list and source hashes unambiguously identify the full run. The original handle is preserved rather than silently overwritten.

`RAW_INDEX.json` identifies all bounded scientific records. TLC state databases, `.tlacache` and extracted temporary standard modules remain on the 8 TB disk as engine scratch and are explicitly excluded from the bounded publication payload. The retained stdout contains the concrete negative traces, and every executable source/config is included.

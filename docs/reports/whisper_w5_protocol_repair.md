# Whisper W5 protocol repair

## Contextual risk-frontier repair

Fresh, correctly sized W1 runs exposed two repeat-stable fast-path state
mismatches.  The first occurred at window 5 with 111 prior prompt tokens and
margin 0.0859375.  After renewing and independently validating that policy, a
new W1 seed exposed a second root at window 7 with 64 prior prompt tokens and
margin 0.1171875.  In both cases a second same-input canonical execution
reproduced the authority result, so neither row is canonical nondeterminism.

Each failed policy epoch is rejected and retained under `excluded/`.  The
replacement policy is reselected from frozen calibration rows plus all
adaptation-only roots.  The second renewal expands the prompt-load clause to
the smallest calibration-feasible contextual frontier: base margin
0.015626, window 2 margin 0.031251, and prior prompt load 64 margin
0.1171885.  Its frozen-calibration protection fraction is 18.75%, below the
predeclared 20% budget, with a 0.2707% one-sided calibration risk bound.  A
fresh independent W4 audit is mandatory before W5 can resume.  Neither
discovery row can contribute to a renewed confidence certificate.

## Status

All invalidated W5 epochs are excluded.  They are preserved under the
versioned `excluded/w5-*` directories on the experiment server and are never
selected by the W7 finalizer.

## P0-1: production offered-load mismatch

`run_whisper_w_matrix.sh` originally created 32 sessions for every cell while
declaring active concurrency 16 or 8. This changed W1/W2 into two waves and
W3/W4 into four waves. Because event latency correctly included initial queue
wait, the resulting P99 measured overload rather than the registered
production contract. The most visible symptom was a 12-second W3 P99.

The repair makes session count equal certified active concurrency in W1-W4:
16 for c16 and 8 for c8. B1 alone retains 32 offered sessions and explicitly
reshapes them to active c16. B2 uses 16 sessions at c16. Every renewed matrix
uses a new seed epoch; adaptation data are never reused as final validation.

## P0-2: replay attribution without a repeat control

The first implementation replayed each fast-path write once after service
timing. A disagreement with that later FP16 singleton draw was added directly
to `state_violations`. This could not distinguish:

- a stable batch-versus-singleton disagreement; from
- a repeat-unstable FP16 singleton canonical draw.

The repair performs a second same-input singleton replay whenever the first
replay disagrees. A mismatch is attributed to the fast path only when the
canonical repeat is stable. Repeat-unstable cases remain visible as ambiguous
finite-precision evidence. Raw, stable, ambiguous, and canonical-repeat
disagreements are reported separately.

The repeat control runs after wall-clock and energy timing. It therefore
cannot improve the measured service trajectory. W4 pre-outcome randomized
shadow audits remain the formal statistical content certificate.

## Additional safeguards

- The finalizer now checks the expected session count for every production and
  boundary cell.
- It requires the v2 repeat-controlled replay fingerprint.
- Resume skips still advance the Latin-square order index.
- The old epoch was moved, not deleted, so code/protocol diagnosis remains
  auditable.

## Long-session tail diagnosis and revision-work contract

The renewed small-model W1 matrix remained state-safe but missed the 1.9 s
tail-latency gate in three of five seeds.  The slow events were not caused by
the verifier: their verification fraction was zero.  The full c16 proposer
round itself took 2.05--2.08 s when one row consumed the complete 96-token
decode allowance.  This is a batch-coupled latency mechanism: one long
autoregressive row delays every session in the same proposer round.

Three candidate repairs were tested before changing the contract.

- An authority-idle second c8 proposer lane preserved safety but increased P99
  to 2.484 s and reduced wall speedup to 3.457x.  Splitting c16 destroyed batch
  efficiency without shortening the slow autoregressive lane.
- Prompt-state capacity thresholds were non-monotonic across seeds.  Rebase
  changes the future trajectory, while the measured tail was dominated by
  next-segment decode work rather than prompt padding.
- A revision work budget directly bounded the responsible work.  The 80-token
  candidate produced 1.081--1.124 s P99, 5.180--5.564x wall speedup and
  68.3--70.2% energy reduction in three independent stress seeds.

The final candidate therefore makes `max_new_tokens` an explicit fingerprinted
part of the revision contract.  It is shared by proposer and canonical
authority, is certified independently for every model/concurrency contract,
and is evaluated against a 96-token quality reference.  It is not treated as
an implementation-only knob.

## Max80 risk renewal

The first max80 small-c16 audit uses frozen calibration data plus two
adaptation-only roots discovered at windows 1 and 4.  Its selected contextual
frontier is a near-zero global threshold together with a prior-prompt clause:
prompt tokens at least 28 and margin at most 0.031251.  On a new audit seed it
completed 30,008 risk-eligible state entries and 621 pre-outcome randomized
audits with no caught state error.  The adaptation rows do not contribute to
this certificate.

The base-c8 max80 contract exposed additional roots during independent audits.
Attempt 1 found a window-14 state error at margin 0.078125, motivating a
revision-age clause.  Attempt 2 found a window-2 state error at margin
0.0234375 and prior prompt length 14, motivating an additional contextual
prompt-load clause.  Both attempts are rejected adaptation epochs; only a
later 30k-entry, zero-error seed may become the final c8 certificate.

## Quality-reference correction

The initial W6 implementation instantiated the canonical authority with the
same decode budget as the deployed method.  Under a max80 candidate this would
measure Holdback quality relative to an already truncated max80 authority and
could hide quality loss caused by the work budget itself.  The repaired
protocol uses:

- deployed RevTrace budget: model/concurrency contract value;
- quality reference budget: 96 tokens;
- paired LibriSpeech sessions and the existing mean/upper-bound WER gates.

Thus W6 covers the total user-visible effect of the risk mechanism and the
revision-work contract.

## W6 paired-reference capacity bug

The first paired W6 implementation applied the architectural capacity rebase
to RevTrace but not to the singleton reference.  The report nevertheless
described both paths as sharing the W-suite authority semantics.  This was a
code/protocol defect: the two systems entered different prompt histories
before quality was compared.  It produced five apparent catastrophic
outliers even after risky state entries were repaired.

The correction applies the same declared-work capacity predicate to the
reference executor before every segment.  A reference with a different
revision-work budget still uses its own declared budget, so W6 continues to
measure the method budget as part of the contract rather than silently
forcing identical truncation.

The same defect was then found, before the final W5 matrix started, in the
cached all-canonical workload oracle.  Its prompt state previously relied on
the 224-token suffix truncation while RevTrace rebased before the declared
next-segment budget could overflow.  The final W5 oracle now applies the same
declared-work predicate and records its rebase count in both the cache
contract and result payload.  All pre-repair W5 rows remain excluded; no
paper-facing speedup is computed against the unequal-work oracle.

## Deferred state and final-output authority

Prompt-state safety and stable-output quality are separate authority
boundaries.  A batched revision can differ in text while its bounded suffix
projects to the same next prompt, so a state-only certificate does not by
itself protect the displayed transcript.  Contract v2 therefore uses:

- high-margin nonterminal proposals: contract-admitted fast state entry;
- risky nonterminal proposals: immediate provisional display, followed by
  singleton-canonical prompt-state and stable-output authority;
- periodic checkpoints: singleton-canonical state authority;
- terminal proposals: immediate provisional display, followed by
  singleton-canonical stable-final-output authority.

The terminal authority is reported separately from the state-verification
fraction.  Its compute remains included in wall time and energy, and its
stable-final latency is reported explicitly.

## LocalAgreement capacity parity

Source review before the final W6 run found that the LocalAgreement-2 quality
foil advanced its feedback prompt without the declared-work capacity rebase
used by the canonical reference and RevTrace.  Even though the 90-second
quality workload is unlikely to exercise this boundary often, leaving it
asymmetric could make the foil fail for a capacity reason unrelated to display
agreement.  The final runner applies the same architectural capacity predicate
to LocalAgreement and records its rebase count separately.  This change does
not modify RevTrace or its gate; it prevents an unfairly weakened comparator.

## W5 fail-closed renewal and cache versioning

The first capacity-rebase-v2 W5 epoch exposed one legal post-timing mismatch
in `whisper-base.en` W1.  The batch result at window 3 had margin 0.03125 and a
47-token parent prompt.  It changed both the stable output and the next prompt
state.  Repeating the canonical execution was exact, so this was not a random
canonical failure or a state-routing defect; the contextual risk frontier was
too aggressive.  The runner correctly failed closed after recording the
event.

That entire W5 epoch is adaptation-only.  A hash-linked extractor converts the
single same-input mismatch into an external W4 adaptation root, and the source
seed is excluded from all performance aggregates.  The recovery objective was
also corrected from performance-first ordering to fail-closed ordering:
within the frozen 20% verification budget it now minimizes observed
state-entry errors before minimizing verification work.  The selected renewed
policy has zero calibration state errors, 13.53% calibration verification,
and combines a window-3 margin frontier with the existing high-prompt frontier.
Only a new 30k-entry independent audit may certify it, after which W5 restarts
from a disjoint seed epoch.

The excluded epoch also exposed a terminal-authority burst: sixteen sessions
ended together while one BS=1 canonical lane served them serially.  This was a
runtime scheduling limitation, not a risk-policy failure.  Independent
32-request probes froze two isolated singleton lanes after observing exact
agreement with serial canonical execution and authority-throughput gains of
1.451x for `whisper-base.en` and 1.333x for `whisper-small.en`.  Three lanes
were weaker (1.287x on base) and four lanes regressed (0.806x), so the final W5
contract uses two lanes and records the exact warmup fingerprint.  Requests
remain BS=1 and retain isolated reduction paths; this is not ordinary fused
batch verification.

The same excluded seed showed that the proposer GPU became idle while a
synchronized terminal burst drained on the authority GPU.  The final runtime
therefore permits one additional terminal-only canonical lane on the proposer
device, but only after every session has reached its terminal frontier.  The
lane cannot overlap any future proposal work, never handles a state-writing
nonterminal transition, and executes the same BS=1 canonical function already
checked across both identical RTX 3090 devices.  This phase-aware role switch
uses otherwise stranded compute without weakening the state-entry contract.

The repaired all-canonical trajectories live under
`oracle-capacity-rebase-v2/`.  Older unversioned caches remain archived rather
than being overwritten or silently accepted.  This prevents a stale cache
from making an unequal-work comparison appear to be a method result.

## Terminal-authority scheduling: measured negative result

The two-lane and proposer-spillover design above was a development candidate,
not the final paper-facing contract.  Live ablations showed that additional
BS=1 authority lanes reduced queueing but contended for the same GPU memory
bandwidth.  Two, three, and four lanes did not improve the end-to-end state
entry tail over one lane.  Reclaiming the proposer device at terminal or at a
general authority frontier likewise failed to recover the serialized terminal
cost: terminal arrivals were distributed across the run, the eligible idle
windows were short, and cross-device work increased synchronization cost.

A one-step speculative prefetch was also rejected.  It reused 19 of 22
prefetches in its first development run, but three descendants entered a
different prompt state.  Those failures followed a low-margin parent even
though the descendant margins were high.  Changing the batch composition had
changed the numerical execution domain, so a margin certificate from the
parent did not transfer to the speculative child.  The final production
protocol therefore uses one canonical lane, no spillover, and speculation
depth zero.  All negative runs remain under the development/excluded result
tree.

## State-only terminal contract and display-timing repair

Terminal text has no outgoing feedback edge.  Forcing every terminal revision
through singleton canonical authority protects a stronger output contract than
the state-pollution problem requires, while synchronized terminal work creates
the dominant tail bottleneck.  The final W5 contract is therefore explicit:

- every nonterminal transition that writes future prompt state remains subject
  to the independently certified contextual risk policy and canonical
  authority when selected;
- terminal batch output is not claimed canonical-exact;
- paired W6 quality evaluation bounds terminal output degradation against a
  96-token singleton reference on disjoint long sessions;
- W5 must still report zero stable nonterminal state disagreement under its
  post-timing repeat-controlled audit.

This is a state-entry contract, not a relabeling of terminal output exactness.
The W7 finalizer requires `terminal_contract=state-only` and W6 quality/UX PASS
for both models before it can emit the strong cross-family decision.

Source review also found a reporting defect: the runtime displayed the batch
proposal as soon as proposal generation finished, but did not serialize the
corresponding display latency.  The summarizer consequently fell back to state
commit latency and made deferred verification look like delayed display.  The
repair records two separate clocks:

- `display_latency_seconds`: ready-to-proposal completion;
- `latency_seconds` / state-entry latency: ready-to-authoritative state commit.

Display SLO goodput and display deadline misses are now computed only from the
first clock.  Stable-state P99 remains a separate required gate and is never
replaced by the faster display metric.  Development cross-scale runs are used
only to select this protocol; the final W5 seed epoch is disjoint.

The first state-only base development run exposed one repeat-stable state root
at window 2, margin 0.03125, and 54 prior prompt tokens.  It is adaptation-only:
the source run is excluded from performance aggregation, the root was added to
the frozen policy dependency graph, and a new 30k-entry randomized audit on an
independent seed is mandatory before final W5 starts.  The renewed candidate
has zero calibration state error and remains below the predeclared 20%
verification budget.  Discovery data do not contribute to its confidence
certificate.

## Target-capacity accounting and dynamic work authority

The first state-only `whisper-small.en` quality development run exposed three
large WER outliers. Four controlled reruns separated their cause from the
state contract: canonicalizing all nonterminal state, canonicalizing terminal
output, or canonicalizing both did not remove the same three examples. The
shared difference was instead a smaller max-80 proposal budget against the
frozen max-96 authority/reference target.

A first repair treated max-80 exhaustion as a deterministic work-authority
event: the proposal can be displayed, but max-96 singleton execution owns its
state or final output. It removed one outlier but left two repetition loops.
Event-level replay then showed that both remaining loops did invoke extended
authority; the authority was operating on an already different prompt.
Canonical trajectory hashing localized the discrepancy to capacity-rebase
timing. The quality runner had used the speculative max-80 budget to decide
whether the prompt could fit the next segment, while the canonical target used
96. Consequently 31 of 64 development sessions could retain different history
even when all earlier output tokens agreed. The two catastrophic sessions
first diverged exactly at the subsequent budget-saturated authority window.

The corrected contract distinguishes two quantities:

- `max_new_tokens` is a speculative proposer work cap;
- `authority_max_new_tokens` defines both target output semantics and the
  declared next-segment capacity used before any state transition.

The implementation now records decoder decision count separately from exposed
transcription token count (EOS is intentionally omitted from the latter), uses
target-authority work for capacity rebase, and fingerprints both repairs as
`decoder-step-saturation-extended-canonical-v1` and
`target-canonical-declared-work-v1`. Old max-80 risk certificates cannot be
reused. Every max-80 model/concurrency fingerprint requires a fresh 30k-entry
independent randomized audit before the final W5 seed can be released.

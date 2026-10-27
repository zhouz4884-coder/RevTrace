# Shared repaired waiting controller: bounded closure

Runtime`ffaa7ab41dd8d6099efd0eb9abe2334951dc5932`, c16staggered, fixed
rho1, twoRTX3090, original full-row executor, FP16P/FP32A, durable WAL,
D2/C8and actual Consumer. All six policies received the same frozen393row
history bank, conditional-residual ETA, finite0.4smaximum waiting budget,
actual-Consumer AIMD feedback and controller CPU accounting. The bank rows
are not393independent physical batches. This is one development repeat.

| Policy | Dual-deadline offered-audio Goodput | DisplayP99 | CommitP99 | GPUJ/offered-audio-s | Actual wait targets | Waits with a dispatched input | Changed declaredP |
|---|---:|---:|---:|---:|---:|---:|---:|
|Immediate|2.0032|8.584s|8.757s|42.046|0|0|0|
|Fixed|1.8481|8.337s|8.927s|40.586|80|28|7|
|Pending ETA|1.6175|8.551s|8.738s|42.315|3|0|0|
|Backpressure|1.4847|8.759s|8.759s|40.916|50|14|2|
|Recent gain|1.8329|9.081s|9.081s|42.777|0|0|0|
|State aware|2.0711|9.091s|9.118s|42.688|0|0|0|

All six normalized135commit histories match in Parent/frontier/fullZ/P/text.
The normalized history SHA256is
`9faf967cc16cbcb3c09f8fbb4d3bcf23712668616ef1c3db5c2a26eb20af6f2e`.
All WER denominators are14errors/687reference words (2.037846%). All
whole-run dual-P99targets fail; original deadlines and offered work remain
in the denominator. The current independent observer reports no unauthorized
admission, invalid-root actual view or silently lost unfinished obligation.

The apparent3.4%state-aware Goodput point advantage is **not attributable to
waiting**: the actual runtime recorded zero state-aware wait actions. Recent
gain also had zero actions and a different Goodput point. Timing/grouping
variation and policy-observation overhead cannot be relabelled as an input-
refresh benefit. State-aware Display/CommitP99and energy are also worse than
Immediate at this point. No statistical or independent-source superiority is
claimed.

Fixed waiting did act, but only28of80wait targets led to a dispatched input,
and only7changed its declaredP. Pending ETA's3waits produced no subsequent
job for those targets. Backpressure had50waits,14dispatched inputs and2P
changes. These are not GPU saved-work counts: Canonical coverage, expiry,
physical queues and changed batching must remain separate. In particular,
zero intervention is not evidence that an unimplemented CPU algorithm ran.
The implemented, tested policy simply found no admissible action under its
current information/ETA/state/deadline gates.

The closure check independently verified the complete archived raw bytes and
normalized WAL chains. Its first version mistakenly searched`event`rather
than the real JSONLkey`kind`, producing invalid zero-action counts. The
original source/output and an explicit erratum are retained; a positive real-
schema CPU fixture and missing-key failure gate were added. Corrected source
`539a1ef6be5f6db8d21744b46e1e46ef5f47d8fa`re-counted the same immutable
GPU data without re-running models. Existing service metrics came from the
separate full-offered Consumer observer, not the erroneous action parser.

**Decision: NO-GO for a new exclusive feedback-sensitive scheduling/formal
performance matrix from this closure.** This is a scoped absence of demonstrated
benefit, not an impossibility theorem. Keep the two paid old/new-input causal
operators, including their opposite cost signs. Do not increase waiting until
a desired winner appears, relax admission rules, drop late frontiers or spend
the untouched holdout on a policy that did not act.

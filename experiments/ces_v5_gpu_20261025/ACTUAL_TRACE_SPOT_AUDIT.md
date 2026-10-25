# Independent actual-trace spot audit

Date: 2026-10-25. This audit reads the collected compressed events, Canonical
witnesses and physical batch records directly. It does not rely on the summary
CSV to establish the scheduling sequence, and it makes no new GPU call.

Result: **PASS for the checked case, late-Commit counts and Commit-P99 group
columns. No disagreement with the checked local_review CSV entries was found.**
This is a scoped independent spot audit, not a second full audit of all 48
runs or every metric in GROUPS.csv.

## 1. The key case really is the same parent and frontier repeatedly deferred

Cell: `validation-staggered-mixed-progress_joint-r0`.
Job: `authority-4-249`.
Source: `1988-148538-0004`; Session 4; target window 6.

The raw Canonical witness and enqueue event agree on Parent 5, epoch 1,
audio interval `[160000,192000)` samples and the exact prompt Token sequence.
Parent 5 committed audio through sample 160000 at run time 12.909895974 s.
The target audio released at 13.000000000 s, so its actual Parent was already
available before release. The eventual target commits as version 6.

For every relevant decision, the audit independently reconstructs the latest
installed Session-4 version from raw commit events. It remains version 5,
with the same frontier and exact prompt Tokens. No Authority job for this
Parent has already been dispatched. The physical Authority Worker has no live
lease at the decision time. The feature snapshot names this same window,
release, 8-second Commit deadline, 12-second audio prefix and 2-second interval.

There are **14 observed eligible decision points**. At the first 13, Session 4
appears in the second batch of the scored plan but is absent from the issued
first batch. At the fourteenth it is selected. Eleven of the 13 deferrals
occur after the candidate is already ready. Candidate absence at the first
two observations does not forbid the independent Generate operation.

| Run time of decision (s) | Candidate ready | Target plan position | Selected first? |
|---:|---|---:|---|
| 14.494506 | No | 2 | No |
| 15.693419 | No | 2 | No |
| 16.736223 | Yes | 2 | No |
| 18.042778 | Yes | 2 | No |
| 19.435392 | Yes | 2 | No |
| 20.652849 | Yes | 2 | No |
| 21.525922 | Yes | 2 | No |
| 22.598047 | Yes | 2 | No |
| 22.831399 | Yes | 2 | No |
| 23.525141 | Yes | 2 | No |
| 23.758411 | Yes | 2 | No |
| 24.624385 | Yes | 2 | No |
| 25.095782 | Yes | 2 | No |
| 26.023286 | Yes | 1 | Yes |

The job is enqueued at 26.068000838 s and installed at 26.339664062 s.
Its actual selected mode is Strict Verify; the candidate passes, no fallback
is used, and the selected tokens match that candidate. This final acceptance
does not prove that an earlier, differently shaped batch would have produced
the same verification result.

## 2. The critical path closes without overlapping components

| Actual component | Seconds |
|---|---:|
| Audio release to legal Parent/target eligibility | 0.000000000 |
| Eligibility to enqueue | 13.068000838 |
| Enqueue to Worker start | 0.003642788 |
| Worker start to complete row | 0.226821233 |
| Complete row to Trusted Render completion | 0.001423667 |
| Render completion to emission | 0.000012440 |
| Emission to Owner receipt | 0.008520301 |
| Owner receipt to durable install | 0.031242796 |
| **Total Commit latency** | **13.339664062** |

The components sum to the raw commit latency within 1e-7 s and match
AUTHORITY_CRITICAL_PATHS.csv. The row timing comes from the immutable receipt
and executor-complete event, not the full physical batch duration. This case's
long tail is therefore located before its own execution, while the same
legally executable target is repeatedly omitted from the first batch.

The 13.068-second interval includes time while other physical batches execute;
it is not 13.068 seconds of idle GPU time. This audit does not convert that
interval into a free or wholly recoverable speedup.

## 3. Late-Commit counts independently reconstructed from six raw event streams

Each run contains the same 135 requested source/frontier pairs and exactly
135 commits. Latency is independently computed from installed and actual
audio-release clocks, then checked against the event's latency field.

| Method | Repeat | Commit > 8 s | Already > 8 s at enqueue | Crossed 8 s after enqueue | Commit P99 (s) |
|---|---:|---:|---:|---:|---:|
| progress | 0 | 11 | 9 | 2 | 10.048595 |
| progress | 1 | 11 | 6 | 5 | 10.835359 |
| progress | 2 | 19 | 19 | 0 | 13.045190 |
| progress_joint | 0 | 22 | 22 | 0 | 13.255138 |
| progress_joint | 1 | 12 | 11 | 1 | 10.687458 |
| progress_joint | 2 | 22 | 16 | 6 | 15.814266 |

Totals are **41/405 for progress** and **56/405 for progress_joint**. Of those
late commits, respectively **34/41 and 49/56 were already beyond the deadline
before enqueue**. Each method has another seven records that cross the
deadline after enqueue. It would be wrong to describe all late records as
already expired at dispatch.

The group medians of the three independently recomputed per-run Commit P99s
are 10.835358983 and 13.255138062 seconds, matching GROUPS.csv. These are
medians of per-run P99s, not a P99 pooled across 405 events.

**405 is three repeated observations of the same 135 source/frontier pairs,
not 405 independent acoustic samples.** No independence-based significance
claim is made from these counts.

## 4. What this establishes and what remains unproven

The requested key case confirms that suffix postponement is present in an
actual GPU serving trace, not only in the prior CPU counterexample. It is not
a stale-parent rejection, a target with unreleased audio, or a long fallback
for that job. Its Parent and target remain unchanged across all 14 choices.

This does not make every late commit the same phenomenon. Among the late
records, 17/41 progress records and 26/56 progress_joint records already lack
a usable Parent until after their own eight-second deadline. Those are
downstream availability delays and need their predecessor histories traced.
Only 4/41 and 13/56, respectively, spend more than eight seconds in their own
eligible-to-enqueue interval. These categories are not additive and are not
claimed to partition all causes.

The observations support inspecting persistent service obligations and
predecessor deadline propagation. They do not establish how much Goodput a
different scheduling rule would recover, whether earlier verification would
pass under a different physical batch, or whether protecting Commit would
reduce other Display credit. Such claims require legal, paid-work matched
controls. The existing first-visible metric and safety predicate are unchanged.

## Reproduction and evidence

`audit_actual_spot.py` reads original collected files and writes a new audit
artifact. The final machine-readable output is
`ACTUAL_TRACE_SPOT_AUDIT_FINAL.json`; it contains all 14 decisions, each of the
97 late records, the path decomposition, per-run/group checks, script hash
and SHA256 hashes of every source file used. The initial output is retained.

Re-run with a fresh destination:

`python audit_actual_spot.py --output <new-output-name>.json`

The original collected evidence, local_review outputs and frozen runtime are
not modified by this audit.

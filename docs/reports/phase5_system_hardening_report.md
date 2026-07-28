# RevTrace Phase 5 system-hardening report

Decision:

`PAPER_CORE_GO_WITH_PHASE5_MEASURED_BOUNDARIES`

Phase 5 completed all A--E work packages. It did not pass every frozen hard
gate. The paper core remains supported by the deployed Phase 1--3 system and
the Phase 4 causal evidence, while Phase 5 supplies live adaptation,
cross-family protection, workload breadth, and explicit failure boundaries.

## Phase 5A — live adaptive risk window

### Method

A persistent two-GPU service executed the contract sequence
`c16 -> c64 -> c16`. Every switch changed the contract fingerprint, discarded
old evidence, and set the fast-path window to zero. A fresh split-sample
certificate selected the margin boundary without a manually chosen threshold.
A second run used prior-certified thresholds and a disjoint stream seed as an
independent static performance reference.

### Results

| Stage | Learned threshold | Risk upper | Goodput | Independent static reference | P99 | Deadline misses | Output/state violations |
|---|---:|---:|---:|---:|---:|---:|---:|
| c16 initial | 0.03125 | 0.4508% | 21.013 events/s | 16.857 events/s | 1.406 s | 0 | 3/1 |
| c64 drift | 0.015625 | 0.4989% | 42.900 events/s | 32.159 events/s | 2.889 s | 448 | 4/7 |
| c16 return | 0.015625 | 0.4481% | 22.305 events/s | 20.050 events/s | 1.293 s | 0 | 0/0 |

Recovery to 90% of the disjoint static reference took 67.90 s, 35.78 s, and
67.26 s. The corresponding adaptation regret was 17.67, 0, and 17.95 event
equivalents.

### Gate and cause

Decision: `PHASE5A_LIVE_ADAPTIVE_CONTROL_FAIL`.

The thresholds and reported upper bounds are statistical. They allow rare
canonical disagreement and therefore cannot satisfy a simultaneous
zero-observed-violation hard gate over thousands of new entries. The disjoint
static run also observed disagreements, confirming that the failure is not
specific to the adaptive implementation. c64 additionally exceeds the
two-second RTX 3090 service region. These are risk-contract and physical
capacity boundaries, not state-routing or random-sampling defects.

## Phase 5B — Whisper protected intervention

### Protocol repair

The first queued run incorrectly used a 48 kHz Qwen smoke manifest and looked
for Phase 4 pairs under the remote source checkout. Whisper requires the
16 kHz LibriSpeech manifest, and the paired-world results live under the
designated data-results root. Both inputs were corrected and all four jobs
were rerun.

### Results

With previous-text feedback ON, every feedback-bearing transition was
fail-closed to singleton canonical execution.

| Model | Events | Known pairs protected | Output/state violations | Wall speedup |
|---|---:|---:|---:|---:|
| whisper-tiny.en | 300 | 5/5 | 0/0 | 1.006x |
| whisper-base.en | 300 | 16/16 | 0/0 | 1.002x |

The mechanism passes safety but not the throughput target. It is retained as
cross-family protection evidence rather than a second main performance result.

With previous-text feedback OFF, decoded text never enters future model state,
so certification is bypassed:

| Model | Events | Local output differences | State-propagation violations | Wall speedup |
|---|---:|---:|---:|---:|
| whisper-tiny.en | 300 | 281 | 0 | 6.117x |
| whisper-base.en | 300 | 284 | 0 | 6.444x |

This is a strong causal boundary: local execution-shape disagreement is common
in these batches, but it cannot create a feedback contamination chain when the
feedback edge is absent.

Replication consistency is not a singleton-equivalence certificate. The
diagnostic policy leaves 10/5 state violations for tiny and 32/16 for base
(output/state), because all replicated rows can move together relative to the
singleton path.

Decision: `PHASE5B_PROTECTION_PASS_PERFORMANCE_BOUNDARY`.

## Phase 5C — workload and energy frontier

Eight live two-GPU cells cover both Qwen3-ASR sizes, concurrency 8/16/32,
30/60/120-second sessions, synchronous/Poisson/burst arrivals, and
English/Chinese/mixed inputs.

- Wall speedup: 2.932x--6.767x.
- GPU-normalized speedup: 1.466x--3.383x.
- SLO goodput: 3.801--15.872 events/s.
- Energy: 7.743--22.652 J per processed audio-second.
- Seven of eight cells have zero observed state violation.
- Two of eight cells have zero deadline misses.

The failing safety cell is `0p6b-c32-d120-burst-zh`. Revision `s023:8` has
margin 0.109375, exceeds the frozen 0.10 c16 threshold, is not verified, and
changes the state projection. The next revision differs in full output but
reconverges at the state projection. This is evidence that contract identity
must include concurrency/language/arrival regime and that a c16 certificate
cannot be silently transferred to c32.

Five other failing cells preserve state safety but exceed the two-second
deadline. They are capacity/tail boundaries, not correctness failures.

Decision: `PHASE5C_WORKLOAD_FRONTIER_COMPLETE_WITH_BOUNDARIES`.

## Phase 5D — live release-aware audit packing

A warmed Qwen3-ASR GPU executed the mandatory stream and real packed audit
requests. Admission used a measured audit P99 plus a 10% guard.

- Mandatory outputs remain exact.
- Deadline misses: 0.
- Packed audits: 19/20.
- First-audit detection-time improvement: 98.49%.
- Mandatory P99: 0.8229 s -> 0.8422 s.
- P99 change: +2.3547%.

The final value is above the preregistered 2% ceiling. The failure is close to
the threshold but is not repaired by post-hoc guard tuning. Full-request
packing stops here; token/block-level preemption is outside this paper.

Decision: `PHASE5D_LIVE_SLACK_PACKING_NO_GO`.

## Phase 5E — consequential state-pair corpus

The corpus contains 72 hash-distinct records:

- Qwen3-ASR: 51.
- Whisper feedback: 21.
- Natural: 36.
- Stress: 23.
- Targeted: 13.

Every record preserves the paired states, margin and source metadata needed
for mechanism and damage analysis. The corpus is not a production prevalence
sample.

Decision: `PHASE5E_CONSEQUENTIAL_CORPUS_COMPLETE`.

## Paper interpretation

The main innovation is structural and systems-oriented:

1. a Feedback-Edge State Model identifies when generated output becomes future
   model state;
2. versioned state-entry transactions prevent provisional or stale revisions
   from silently updating that state;
3. contract-scoped risk control decides when the fast path may bypass
   canonical execution;
4. the deployed proposer/verifier pipeline overlaps the fast batched path with
   sparse canonical work.

The strong speedups arise from batching the common proposer path, restricting
canonical work to the state boundary, and overlapping two GPU service lanes.
Phase 5 also shows exactly where this architecture stops being sufficient:
statistical certificates are not deterministic, contract transfer is unsafe,
c64 can exceed the service region, and coarse audit packing can violate a
tight P99 budget.

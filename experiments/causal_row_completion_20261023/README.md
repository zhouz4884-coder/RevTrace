# RevTrace: Causal Row Completion and Certified Progress

Completed bounded study based on `9aa23a4d3a5d73076c5e8a87fe669e96f49594aa`.
Executed runtime: `2bc71af5457de5d065ff9e771d2fad428c5c6ed9`.
No manuscript, title, abstract or submission materials were changed.

## Result

**GO for a safe, shared row-completion runtime improvement. NO-GO for an
additional independent C2 scheduling-algorithm claim or the tested Rescue route.**

- All 150 real dual-RTX3090 cells passed admission, WAL, D1, actual Consumer,
  physical-lease, input-replay and fixed-configuration audits: 120 core cells
  plus 30 validation cells, using two disjoint cohorts of 16 sources.
- Registered core sync16/F2 DGFT batch-to-row Goodput improved by a paired
  median **53.56%**, conditional 95% interval **[16.94%, 67.38%]**. All three
  repeats improved; its own final Canonical WER/CER was unchanged. Median
  physical fsyncs increased from 10 to 43 and were charged.
- Equally equipped Standard also improved by 43.71%. Clean-workload effects
  were not uniformly positive. This does not establish an exclusive new
  dispatcher or rebase algorithm.
- DGFT did not dominate Fine. On independent F2 sources, Fine-row achieved
  10.369 Goodput at 34.543 GPU J/audio-s, versus DGFT-row's 6.129 at 36.296.
  The 32-source WER delta was +0.207 percentage points; its 95% upper bound,
  +0.607 points, exceeded the frozen +0.5-point noninferiority margin.
- Six frozen new-parent inputs received two fresh FP32 cost calls each.
  Five exceeded their windows even at their best measured cost; all three
  tested F2 cases failed. The lone clean fit had only 7.497 ms worst-case
  headroom. No integrated Rescue or additional online comparison was started.

Read the [Chinese research report](reports/RESEARCH_REPORT.zh.md),
[Claim–Evidence Matrix](reports/CLAIM_EVIDENCE_MATRIX.csv), and
[GO/NO-GO record](reports/GO_NO_GO.json). All workload limits, SLO misses,
quality findings and negative comparisons are retained.

## Evidence highlights

The F2 audit recorded 1,200 consumed injections with actual processed-ID changes;
all 30 paired source–target-window maps matched. Potential co-batch shape
exposure is not asserted neural corruption or a deterministic rejection cascade.

There were 5,033 actual Canonical Consumer applications before physical batch
drain, including 812 verified-success applications before failed peers completed
fallback. These are local Consumer observations, not internal commit markers
or browser/network delivery measurements.

Supporting evidence includes the old 72-cell rejection audit, original-peer GPU
probes, 36 production-operator controls, 210 Linux CPU regressions, separately
labelled CPU/WAL crash fixtures, and 54 Windows CPU checks. CPU fixtures,
operators and online serving are never merged into one evidence tier.

R3 used eight native 30–33 s sources, two adapters, two full repeats and 652
actual trajectory calls. Both finite state recovery and endpoint recognition
harm occurred. It supports neither permanent pollution nor automatic healing.

The real GPU row-crash case is **post-WAL, before publication and client ack**:
59 unique final admissions and no duplicates; cold restart to certified Consumer
took 36.216 s. The raw `acknowledged` field names an internal synchronization
marker. See the [scope correction](protocol/RECOVERY_EVENT_SCOPE_CORRECTION.md).
It is not evidence of GPU failure after client acknowledgement or host power loss.

## Layout and reproduction

- `runtime/`: the byte-frozen executed SDK and its source manifest.
- `source_archives/`, `source_bundles/`: retained revisions and 17 verified
  standalone Git histories, including failures. These snapshot commits are
  distinct from GitHub-main commits; see `BUNDLE_MANIFEST_v4.json`.
- `research/`, `protocol/`: controllers, independent audits, execution plans,
  safety obligations and metric definitions.
- `evidence_checkpoint/`: unchanged earlier evidence.
- `evidence_formal/`: all 150 bounded configuration/provenance/result records,
  aggregate tables, audits and the separately hashed Consumer addendum.

The full original measurement bank remains on the designated 8 TB disk:
3,736 closed files, approximately 1.216 GB. Its index is
`evidence_formal/FINAL_CLOSED_EVIDENCE_v1/RAW_EVIDENCE_INDEX.json`, SHA256:

`11a3b5b101891e27b4684a016aba9b53e734bfcbc9605d83ec4cc2cd9f5ecd55`

Ephemeral/self-index exclusions are explicit. This measurement index predates
the derived Consumer addendum; the final artifact MANIFEST also hashes every
distributed derived file. No credentials, models, audio, environments or large
worker/event banks are redistributed.

Controllers require the recorded asset layout and exact model/tokenizer profile.
Deploy the frozen filenames and verify hashes first; do not blindly rerun them
against existing outputs. This artifact never automatically downloads assets
or starts GPU work. Old Z is never presented as new-parent generation.

Goodput uses the declared version-compatible Provisional frontier; WER/CER is
final Canonical text, not temporary transcript accuracy. Energy is GPU-only;
bootstrap intervals condition on observed schedules. See the
[methods](protocol/ANALYSIS_METHODS.md) and
[provisional scope](protocol/PROVISIONAL_METRIC_SCOPE.md).

The research queue is closed and task GPU resources released. Original C1/C2/C3
and earlier NO-GOs remain intact. No forbidden route or paper rewrite follows.
This is not a guarantee of DSN acceptance or a claim of exhausting the topic.

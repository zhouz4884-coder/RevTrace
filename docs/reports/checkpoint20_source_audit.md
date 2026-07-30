# Checkpoint-20 source and evidence audit

## Decision

`REVTRACE_EXPERIMENTAL_EVIDENCE_COMPLETE_FOR_FGCS_SUBMISSION`

This audit did not run new model inference. It reviewed the frozen raw
evidence, repaired offline accounting and provenance, captured a post-run
content identity on the original server, rebuilt the bounded artifact, and
verified the result from a fresh Git clone.

## Findings and repairs

| Finding | Root cause | Repair | Effect on experimental result |
|---|---|---|---|
| Empty provisional text was assigned overwrite 1 | denominator used `max(1, len(left))` without an empty-display boundary | empty display now returns overwrite 0; regression test added | no frozen event was empty, so headline numbers do not change |
| P1/P2 consecutive holdbacks were each compared only with final authority | event log stored resolution-relative metrics, not the actual visible transition sequence | reconstruct P1->P2->...->authority, per-episode churn, maximum modification, and burst length | overwrite mean changes from the old endpoint-only 7.20% to 8.01% for actual display transitions |
| `--resume-quality` checked only session IDs | resume path lacked contract and source-lineage validation | fail closed on mechanism digest, exact contract hash, B=12 deployment, threshold, session set, ordered source IDs, references, and inherited transcripts before GPU startup | current resume relation passes all checks; no transcript changes |
| 3,600 opportunities were called state-entry events and 10% was called verification | checkpoint rounds and holdbacks were conflated in reporting | report 3,600 revision opportunities, 3,539 committed state transitions, 61 holdbacks, 10% checkpoint authority, and zero synchronous low-margin verification | terminology corrected; raw performance is unchanged |
| Quality bootstrap silently assumed constructed sessions were adequate inferential units | each session has distinct internal utterances but sources are reused across sessions | source-overlap graph and dependence audit added | observed fixed-sample means remain; independent-source population noninferiority remains unresolved |
| Runtime identity omitted GPU UUIDs, package/source versions, and audio bytes | first identity captured only model/data-manifest/runtime hashes and GPU names | byte-hash 128 audio files; record GPU UUID/PCI identity, package versions, Torch/CUDA, Qwen-ASR source tree, model, and authority runtime | post-run artifact identity is stronger; it does not retroactively change the mechanism digest |
| Live seed JSON did not embed a runner SHA | early runner wrote a placeholder commit label | resolve the unique Git blob and label it as a retrospective source snapshot; retain at-run SHA claims only where present | evidence boundary is stricter; system metrics are unchanged |
| Windows-generated evidence hashes failed after a fresh clone | CRLF bytes were hashed before Git normalized files to LF | all evidence writers now emit LF; bounded artifacts are marked non-transcoding; Phase 3/4/5 legacy manifests were regenerated | fixes artifact reproducibility only; no model or performance value changes |

## Recomputed evidence

- Five service seeds: 3,600 revision opportunities, 3,539 committed state
  transitions, 61 holdbacks, zero deadline misses, maximum P99 1.414 seconds,
  and mean 8.670 J/audio-second.
- Quality: observed mean total delta is +0.929 percentage points WER and
  +1.149 percentage points CER, with zero catastrophic outliers.
- Holdback incremental delta is +0.027 points WER with 95% interval
  [-0.049, 0.103] and -0.027 points CER with interval [-0.071, 0.000].
- Continuous provisional display: 69 resolution episodes, three multi-holdback
  episodes, maximum burst length three, transition overwrite mean/P95/max
  8.01%/48.73%/100%, and episode cumulative churn mean/P95/max
  0.087/0.655/1.399.
- English and Chinese session-source graphs each form one 32-session connected
  component. The existing bootstrap is therefore descriptive for the frozen
  constructed-session sample.

## Main code used

- `src/revtrace/evidence_audit.py`
- `src/revtrace/provenance.py`
- `scripts/remote/run_deployed_checkpoint20_quality.py`
- `scripts/remote/capture_checkpoint20_identity.py`
- `scripts/audit_checkpoint20_submission_evidence.py`
- `scripts/bind_checkpoint20_evidence.py`
- `scripts/finalize_checkpoint20_submission.py`
- `scripts/build_checkpoint20_submission_artifact.py`
- `scripts/verify_checkpoint20_submission_artifact.py`
- `tests/test_provisional_experience.py`
- `tests/test_checkpoint20_submission_finalizer.py`

## Verification

- 144 tests pass.
- Raw-result tampering and missing binding roles are rejected.
- Undeclared artifact files are rejected.
- The bounded artifact verifies its exact declared file set and content hashes;
  its current digest is recorded in `MANIFEST.json`.
- A fresh clone of the published `main` branch passed tests, checkpoint
  finalization, bounded artifact verification, Phase 5 artifact verification,
  and full repository validation without dirtying the worktree.

## Remaining scientific boundaries

- Margin is an empirical scheduling signal, not a deterministic arithmetic
  certificate.
- The time-uniform risk bound concerns its declared admitted-state population.
- Population quality noninferiority is unresolved.
- The identity extension is a post-run attestation.
- Service prevalence and provisional UX prevalence are not production
  prevalence estimates.

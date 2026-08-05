# Informal review triage — 2026-08-05

This file separates missing experiments from evidence that already existed but
was not visible enough in the manuscript. It is an author-side audit, not a
rebuttal letter and not an editor decision.

| ID | Review concern | Triage | Evidence/action |
|---|---|---|---|
| W1 | No fair external baselines | Partly valid | Added H6 and Table 6. Faithful same-trace adaptations show MarginGate-inspired and owner/version-only policies each retain one state error; LLM-42-style always-verify is safe at 1.565 evt/s; RevTrace is safe at 3.046 evt/s. These are explicitly adaptations, not source-system end-to-end rankings. |
| W2 | No ASR quality/user metrics | Mostly stale, presentation valid | Existing F1/R10/R9 evidence already includes WER, CER, terminal exactness, partial revision edit rate, provisional display P99 and commit latency. Added the standard Qwen metrics and denominator to H5/Table 4. TTFT and subjective user studies remain unmeasured. |
| W3 | Safety trace too small / no abnormal paths | Valid | Added a deterministic 250,000-attempt, 64-session DGFT transaction fuzzer: 10,000/10,000 valid accepted; 240,000/240,000 tampered, stale, gap/overlap, duplicate or replay attempts rejected; zero invalid accepts and zero invariant violations. Kept explicit exclusions: Byzantine trusted components, wall-clock expiry, GPU crash/floating point. |
| W4 | Scale/generality | Partly valid | Existing results span two revision semantics and five checkpoints, but only one host with two RTX 3090s. Added an explicit scale boundary; did not inflate this into a multi-node claim. |
| W5 | Cost-model validation weak | Valid wording issue | Reframed as an authority-cost decomposition and sufficient operating condition, not a workload-independent fitted predictor. H3 remains a complete-configuration measurement and explicitly does not isolate granularity alone. |
| W6 | Definitions/theory assumptions unclear | Mostly stale, assumption scope valid | Existing draft already defines legal paired interventions, RAF, contracts, certificates and serving scopes. Added a direct statement that proposer determinism, greedy decoding, synchronous kernels and proposer-cache equality are not theorem assumptions; the realized authority projection and configuration must be certificate-bound. |

## New protocol-fuzz artifact

- Runner: `scripts/run_dgft_transaction_fuzzer.py`
- Result: `results/paper_review_closure/transaction_fuzz.json`
- Seed: `20260805`
- Attempts: `250000`
- SHA-256 recorded inside the result artifact.

## Remaining defensible limitations

1. No multi-node or data-center-scale deployment.
2. No end-to-end execution of the original text-only LLM-42/MarginGate systems
   on ASR; only clearly named faithful revision adaptations.
3. No Byzantine authority, GPU crash/restart, wall-clock certificate-expiry or
   psychophysical user study.
4. The cost equations explain and constrain the operating point; they are not
   a universal numerical performance predictor.

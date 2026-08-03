# RevTrace pre-submission offline audits

Overall: **PASS**

## A. CJK-aware coverage replay

- Decision: `PASS_R9_COVERAGE_REPLAY_NO_DECISION_CHANGE`
- Replayed: 2050 segments from 22 files.
- Latin-only: 2050; CJK-containing: 0.
- Recorded-decision changes: 0.
- Legacy-vs-current Latin-only changes: 0.
- Boundary: this is a regression test on English Whisper traces, not a Chinese-quality experiment.

## B. Motivation denominator audit

- Decision: `PASS_PAPER_DENOMINATOR_AUDIT`
- Legal state pairs: 21.
- Feedback-on propagation: 8/21.
- Feedback-off propagation: 0/21.
- Persistent pairs: 6; maximum measured RAF: 153.
- Manuscript 8/8 claim violations: 0.

## C. Contract inventory

- Decision: `PASS_PAPER_CONTRACT_INVENTORY`
- Evidence groups: 5.
- Inventory digest: `ec126bcbb119ff5294a1b0df91298b3fd9024d289b753c9b4715e785a8b0c64d`.
- Groups: R9.E Whisper service, R10 Qwen service/ablation, SG anytime risk, Qwen quality, Whisper quality.
- Risk and quality estimands remain family/path scoped and are not pooled.

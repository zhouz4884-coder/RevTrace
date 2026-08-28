# Final corrections to senior-author figures

The revised Figure 2 supplied on 2026-08-27 passes the technical review and
has been inserted into the manuscript. Preserve its current layout.

## Figure 1: required corrections only

1. Replace `Unitary/Standard Execution` with `Singleton/Standard Execution`.
2. Render the output notation as `Y_t^a` and `Y_t^f`; both executions refer to
   the same serving round `t`.
3. Replace both repeated `State Pollution Propagation` labels with one label:
   `Feedback-State Contamination Propagates`.
4. Remove the Chinese labels in Panel B:
   - retain only `Proposer (Fine Path)`;
   - use `State-Write Request`;
   - use `Authorize & Write State`.
5. Replace the bottom attribute line with:
   `DGFT Core Attributes: No certificate, no write; fork-free committed
   history; granularity-independent safety.`

The shared parent `H_t/V1`, canonical `H_{t+1}^a/V2`, contaminated
`H_{t+1}^f/V2`, 8/21, 0/21, and measured RAF=153 annotations are correct.
Other visual details do not require revision.

## Figure 2: accepted

The revised architecture/timeline figure correctly includes evaluated FP16
and FP32 implementations, risk/coverage-evidence non-authority, certificate
and parent-version binding, frontier checking, and distinct display/commit
clocks. No further correction is required.

## Figure 3: one required correction

The Stratum IV sentence is truncated after `Whisper: paired WER delta vs`.
Complete it as:

`Qwen: mixed-unit edit rate vs FP16 singleton; Whisper: paired WER delta vs
unprotected feedback.`

All other Figure 3 content can remain unchanged.

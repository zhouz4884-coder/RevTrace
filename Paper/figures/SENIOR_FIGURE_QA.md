# Senior-author figure QA

The paper provisionally uses the supplied senior-author artwork for Figures 1--3. The
alternative Visio redraws were rejected because they reduced the information
density and visual hierarchy of the supplied figures. Before final upload,
the remaining Figure 1/3 text corrections in
`SENIOR_FIGURE_CHANGE_REQUEST.md` should be applied to the senior-author
source files. The revised Figure 2 supplied on 2026-08-27 is accepted.

## Technical review

- **Figure 1:** the causal problem/solution structure is consistent with the paper:
  the batched output can contaminate feedback state, whereas DGFT separates
  provisional display from certificate-authorized state installation. The
  left post-output state must be changed from `H_t/V1` to canonical
  `H_{t+1}^a/V2`, and RAF=153 must be labeled as a measured tail quantity.
  The supplied 1536x1024 PNG has
  an effective density of about 224 ppi at the frozen 0.96-text-width layout;
  a vector or at-least-2160-pixel-wide export is preferred before final upload.
- **Figure 2:** proposer/authority separation, projection adapter, certificate,
  version check, ledger, and dual display/commit clocks match the system. The
  revised artwork qualifies FP16/FP32 as evaluated implementations, scopes R4
  to risk/coverage evidence, and binds authorization to certificate and parent
  version. The
  supplied 2400x1792 JPEG is about 357 ppi at the frozen layout.
- **Figure 3:** four certification strata and the no-transfer rule match H5.
  The Stratum IV body must replace the inaccurate generic `WER/CER reference`
  wording with the exact per-family estimands. The red double-headed arrow
  should become a non-directional divider with X markers. The caption defines
  the exact semantic-quality estimands: Qwen uses an
  independent FP16 reference; Whisper reports paired WER deltas against
  unprotected feedback; these quantities are never pooled. The supplied
  2400x1792 JPEG is about 365 ppi at the frozen layout.

## Manuscript review

- Final length: 18 pages.
- No blocking overfull float, undefined reference, or Type 3 font issue.
- No visible clipping or overlap after placement at the frozen widths.
- Repository test suite: 258 passed.

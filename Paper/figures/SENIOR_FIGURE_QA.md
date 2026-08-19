# Senior-author figure QA

The paper uses the supplied senior-author artwork for Figures 1--3. The
alternative Visio redraws were rejected because they reduced the information
density and visual hierarchy of the supplied figures.

## Technical review

- **Figure 1:** causal problem/solution structure is consistent with the paper:
  the batched output can contaminate feedback state, whereas DGFT separates
  provisional display from certificate-authorized state installation. The
  8/21, 0/21, and RAF=153 annotations match H1. The supplied 1536x1024 PNG has
  an effective density of about 224 ppi at the frozen 0.96-text-width layout;
  a vector or at-least-2160-pixel-wide export is preferred before final upload.
- **Figure 2:** proposer/authority separation, projection adapter, certificate,
  version check, ledger, and dual display/commit clocks match the system. The
  caption explicitly limits FP32 to the evaluated coarse-authority
  implementation and limits R4 non-authority to risk/coverage evidence. The
  supplied 2400x1792 JPEG is about 357 ppi at the frozen layout.
- **Figure 3:** four certification strata and the no-transfer rule match H5.
  The caption defines the exact semantic-quality estimands: Qwen uses an
  independent FP16 reference; Whisper reports paired WER deltas against
  unprotected feedback; these quantities are never pooled. The supplied
  2400x1792 JPEG is about 365 ppi at the frozen layout.

## Manuscript review

- Final length: 18 pages.
- No blocking overfull float, undefined reference, or Type 3 font issue.
- No visible clipping or overlap after placement at the frozen widths.
- Repository test suite: 258 passed.

# Requested corrections to senior-author figures

The visual style and overall layouts should be preserved. Only the following
technical text and local alignment changes are requested.

## Figure 1: problem and DGFT overview

1. The left post-output state is currently labeled `Feedback State H_t / Version
   V1`. Because it is downstream of `Output Y_t^a`, replace it with:
   `Canonical Feedback State H_{t+1}^a / Version V2 (Canonical)`.
2. For symmetry, replace the right state with:
   `Feedback State H_{t+1}^f / Version V2 (Contaminated)`.
3. Add a small label below `Audio Input` and before the fork:
   `Shared parent state H_t (Version V1)`.
4. Replace `Max RAF = 153` with:
   `Measured tail RAF = 153 (6 persistent pairs)`.
   RAF is an empirical trajectory quantity, not a theoretical maximum.

All other Figure 1 content may remain unchanged.

## Figure 2: architecture and timeline

1. Replace `Proposer (Fine Path / FP16)` with:
   `Proposer (Fine Path; evaluated FP16)`.
2. Replace `Authority (Coarse Path / FP32)` with:
   `Canonical Authority (Coarse Path; evaluated FP32)`.
   FP32 is the frozen implementation used in the experiments, not a DGFT
   protocol requirement.
3. Replace `Evidence never authorizes installation (R4)` with:
   `Risk/coverage evidence never authorizes installation (R4)`.
   A valid certificate is an authorization object, so the unqualified word
   `Evidence` is too broad.
4. Replace the authorization formula with:
   `Authorize(Phi(Y_t; H_t), Gamma_j, v_parent) => State-Write Permission`.
5. Replace `Certificate & Version Check` with:
   `Certificate + Parent Version + Frontier Check`.
6. Keep only one callout stating that display and certification have distinct
   clocks. Use:
   `Display P99 and certified-commit P99 are reported separately.`
   Delete the duplicated lower callout.

The node positions, palette, icons, lanes, ledger, and timeline may remain.

## Figure 3: stratified certification

1. Replace the Stratum IV body:
   `Independent per-family WER/CER reference. Qwen: FP16 singleton reference;
   Whisper: unprotected-feedback baseline.`
   with:
   `Independent per-family quality reference. Qwen: mixed-unit edit rate vs
   FP16 singleton; Whisper: paired WER delta vs unprotected feedback.`
2. Keep the right-side scope wording `Qwen edit rates / Whisper WER deltas;
   never pooled`.
3. Prevent the number `1,048` from breaking after the comma in the Stratum III
   scope block.
4. Replace the red double-headed vertical arrow with a plain red divider and
   aligned X markers. Arrowheads visually imply cross-stratum transfer, which
   conflicts with R4.
5. Align each right-side `Scope` block horizontally with its corresponding
   stratum and maintain consistent line spacing.

The dark blue cards, four-stratum layout, no-transfer separators, icons, and
outer dashed boundary may remain unchanged.

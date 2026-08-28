# Figure layout contracts

## State-entry motivation (double column)

- Core conclusion: Batch-created output differences become durable only when
  an uncertified projection is allowed to enter feedback state; DGFT preserves
  provisional display while denying that write.
- Figure archetype: two-panel causal contrast.
- Target/output: FGCS, 0.96 text width, senior-author 2400-pixel JPEG artwork.
- Hero evidence: 8/21 legal state pairs propagate with feedback, 0/21 without,
  and measured tail RAF up to 153.
- Reviewer risk: DGFT does not promise bitwise-identical provisional output;
  the protected object is the future-state parent.

## RevTrace architecture and timeline (double column)

- Core conclusion: Display and state-write permission are separate; only a
  certificate-bearing, version-valid transaction advances committed state.
- Figure archetype: architecture plus dual-clock commit timeline.
- Target/output: FGCS, 0.94 text width, senior-author 300 dpi JPEG artwork.
- Required modules: proposer, projection adapter, contract-specific canonical
  authority, risk/coverage witness, certificate, version/frontier checks,
  ledger, and committed feedback state.
- Reviewer risk: FP32 is an evaluated authority implementation, not a protocol
  requirement; risk evidence schedules verification but never authorizes a
  commit.

## Contract-scoped certification (single column)

- Core conclusion: Numerical risk, implementation invariance, transaction
  integrity, and semantic quality provide non-transferable guarantees.
- Figure archetype: full-width four-stratum ladder with aligned scope column.
- Target/output: FGCS, 0.92 text width, senior-author 300 dpi JPEG artwork.
- Evidence: SG anytime UCB at most 0.48%, frozen FP32 preflight, exhaustive
  accepted-commit checks, and separate per-family quality references.
- Reviewer risk: Qwen reference edit rate and Whisper paired WER delta must
  never be pooled or described as the same quality estimand.

## Authority frontier (single column)

- Core conclusion: Authority granularity creates a measurable speed-quality
  frontier while provisional display and certified commit remain distinct
  latency contracts.
- Figure archetype: vertical quantitative composite.
- Target/output: FGCS, 89 mm single column, vector PDF/SVG plus 300 dpi PNG
  and 600 dpi TIFF.
- Panel map: (a) same-workload speed-quality-energy frontier; (b) aligned SG
  state-entry and DGFT display-to-commit intervals with separated scopes.
- Hero evidence: 6.88x peak wall-clock speedup and the paired model paths.
- Validation evidence: SG P99 state-entry misses and DGFT display/commit
  separation.
- Reviewer risk: the 2 s line must not be visually transferred from SG
  state entry to DGFT segment commit.

## Cross-family production (double column)

- Core conclusion: One transaction abstraction transfers across Qwen and
  Whisper, while performance magnitudes remain contract and family specific.
- Figure archetype: two-family quantitative grid.
- Target/output: FGCS, 183 mm double column, vector PDF/SVG plus 300 dpi PNG
  and 600 dpi TIFF.
- Panel map: rows show wall speedup, GPU-normalized speedup, and service-energy
  reduction; columns keep the two non-poolable contracts separate.
- Hero evidence: Qwen 6.88x peak and Whisper 16/16 passing production cells.
- Controls: per-model and per-arrival-mode points rather than pooled bars.
- Reviewer risk: no horizontal Qwen-versus-Whisper ranking is implied.

## Quality contracts (single column)

- Core conclusion: Qwen stays close to its independent canonical reference,
  while protected Whisper feedback improves WER in both cohorts.
- Figure archetype: vertical distribution and forest-plot composite.
- Target/output: FGCS, 89 mm single column, vector PDF/SVG plus 300 dpi PNG
  and 600 dpi TIFF.
- Panel map: (a) Qwen session-level edit distributions and P95; (b) Whisper
  paired WER deltas and one-sided 95% upper bounds.
- Hero evidence: Qwen P95 at most 3.43% and all Whisper upper bounds below 0.
- Reviewer risk: the two quality estimands are defined once and never pooled.

## V100 dual-plane scaling (double column)

- Core conclusion: balanced proposer-authority replication sustains the
  display SLO through c64, while certified commit has a distinct bounded
  capacity boundary.
- Figure archetype: four-panel scaling and attribution grid.
- Target/output: FGCS, 183 mm double column, vector PDF/SVG plus 300 dpi PNG
  and 600 dpi TIFF.
- Hero evidence: c64 157.8x/111.7x real-time throughput with 1.089/1.394 s
  display P99 and zero display misses in repeated cells.
- Validation evidence: certified commit P99, c128 failed boundary, and
  authority-heavy allocation sensitivity.
- Reviewer risk: internal experiment IDs are prohibited; display and commit
  SLO semantics remain visibly distinct.

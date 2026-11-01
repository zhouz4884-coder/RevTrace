# Three-figure visual direction

2026-11-01. Read-only design review. I viewed the three current `FIGURES_v3/*_PDF_PAGE.png` files and actual cached PDF-page renders of ReCraft, PRAXIS, VampOS and iPrism. No data, source, TeX or CURRENT changes; no new measurements. This is a figure-design recommendation, not a final-page QA claim.

## What the accepted papers actually show

| Actual figure inspected | Useful visual device | What not to imitate |
|---|---|---|
| VampOS 2024, PDF p4 Fig1 and p5 Fig2 | Thin neutral outlines; small repeated components; one clear system boundary; labels sit near their object/edge. The structure, rather than a large colored tile, carries the meaning. | The very small component-level text would be too dense for RevTrace's first mechanism explanation. |
| ReCraft 2025 author v1, p4 Fig3 | Same geometry and object identity repeat across steps; each panel changes only the relevant relation. Limited accent color exposes the changed state. | Its eight tiny panels and rotated labels are not a model for final-size readability. |
| PRAXIS 2026 author v3, p3 Figs1–2 and p10 Fig7 | Clear compartments distinguish observation, dependency object and decision; arrows connect specific objects, not every paragraph. A compact case can show why the mechanism matters. | The iconography and many saturated colors are not necessary for RevTrace. |
| ReCraft p11 Figs6–8; VampOS p10 Figs6–7 | Quantitative plots keep the data, axes and comparison visible, with compact legends and shared geometry. | Do not copy tiny source labels, rainbow bars or dense legend placement merely because a paper was accepted. |

These samples support a restrained systems-paper vocabulary, not a uniform DSN house style. “More advanced” should mean stronger hierarchy, alignment and relation design; it should not mean more colors or decorative effects.

## Four high-leverage changes

**1. Replace the colored-box wall with a small number of object types.** Use near-white background, dark gray text/strokes, one navy accent and a secondary teal only where object semantics require it. Typical border/edge weights:0.6–0.8pt; accent/check paths at most1pt. Reserve heavier emphasis for the main conclusion. Use9–9.5pt main labels and8.5pt secondary labels at the final7.125in width. Keep titles shorter and less dominant than the current long bold sentences. No shadows, gradients, 3D, pictorial GPU/robot icons or enlarged rounded cards.

**2. Fig2 should be a three-lane causal drawing, not a flowchart of paragraphs.** A workable composition is `owned execution / later selection evidence / actual Consumer` with a shared left-to-right grid. Put the already-started call on a narrow gray strip, with compact ASR and Correct/Update operator labels. Show predicted input as a small state token, not a giant filled panel. A separate selected-parent token feeds an EL check. The complete original result and EL evidence merge at a compact AU gate, then a small durable-fact/install object. The same parent independently branches to SUP in the Consumer lane. Retain whole h / render installed state are short endpoints, not two large cards. State tokens, unchanged operators and our check gates need different shapes or border treatments. Solid neutral edges carry data; dashed accent edges carry evidence. This preserves the actual possibility that the child result completes before or after confirmation. Original model work remains visibly distinct from RevTrace's coordination.

**3. Fig1 needs an exterior information rail and an uncluttered plot area.** Keep every real step, the shared axes, D2 line and exact gap limits. Put each policy name and `first visible / certified` numbers in a slim header rail above its axes. Keep just the measured gap label within the gap; place the joint first-delivery miss and `coverage retained after first delivery` outside the data rectangle. An annotation must never get a white box that masks the F16 line or selected-state vertical edge. Use the legend's solid/dashed distinction once, light horizontal grid lines and a restrained hatch for the actual loss. The geometry should show the result before the reader reads a long title. Do not turn27.4ms into an inter-arm tradeoff or label the entire earlier time window as a joint zero gap.

**4. Fig3 should look like a compact analytical figure, not a dashboard.** Keep the two evidence populations explicitly separate. For the2×2, replace four heavy boxes with a hairline grid; large withdrawal counts can be about16–18pt, with smaller timely-audio values aligned below. Highlight the RevTrace row/cell with a thin accent rule or text rather than a large blue card. On the right, use slimmer horizontal bars, constant row spacing and a narrow, aligned Pass column. Preserve100% widths, hatching and external0.8%/3.3% labels with small leaders. The three long category labels should occupy a controlled bottom legend band or two-row key, rather than dominate the plot. Keep `later selected text` explicit so this cannot become a safety/accuracy legend. Never use a color gradient for the left matrix, or compare its counts to the right fractions through shared color intensity.

## Acceptance checks for the new composition

- First glance: state/call/check/view can be distinguished without reading every word.
- One grid: aligned panels, margins, label baselines and arrow landings; consistent gutter rather than ad hoc free text.
- Final-size print: axis and label text stay at least8.5pt; grayscale retains solid/dashed/hatch/shape cues.
- Data and semantics: exact numerical JSON unchanged; no new timeline alignment, zero-gap claim, confidence interval or causal comparison.
- Inspect the actual three PDFs and final paper pages before freezing the release. The parent should accept a coherent redesign once, rather than continue moving a single annotation around the old composition.

Primary-paper identities and URLs are already archived in `experiments/dsn_writing_closure_20261031/DSN_STYLE_AND_FIGURE_READING.zh.md`. The inspected images here are cached local renders under `C:/Users/LENOVO/AppData/Local/Temp/RevTrace_dsn_style_20261031/`; no author figure is copied into RevTrace.

## Mechanism style preview: two local corrections

Actually viewed `STYLE_PREVIEW/coordination_protocol_PDF_PAGE.png`. The lane grid, smaller state tokens, thin neutral operator path and compact gates are materially clearer; keep this composition.

1. **Add the frozen-input operand to EL.** At present EL has only the selected-parent incoming arrow. Route a dashed evidence branch from the already-owned predicted/frozen input token into EL, labelled `frozen full input` if needed. The existing selected-parent solid input stays. This makes the equality check visibly compare two objects and prevents EL being read as validation of the parent alone. Route in the gutter, not through the ASR/Correct-Update operator strip.
2. **Attach AU's conditions to AU.** The three-line `Complete result + current parent + owned identity` note currently floats at the far right of the later-selection lane, while AU is in the execution lane. Place it next to AU or add a restrained leader/explicit `[AU] requires` label. Use `confirmed current parent` to match the gate's actual premise. No additional boxes or gate are needed.

The selected-parent-to-SUP branch, visible-view-to-SUP input, and supported/otherwise outcomes already correspond to the intended independent Consumer decision. Keep solid data/state and dashed check-evidence semantics. No broad redesign or extra labels recommended.

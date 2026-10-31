# RevTrace DSN writing-closure figure delivery

2026-10-31. 独立绘图执行源提交 `60211b74f78b8420ea48f7a08746aedbbcbfb868`；零神经调用。旧模型实验和旧 CPU 提取提交只作为来源，未改写成此次绘图运行身份。

## Figure roles, main captions, and source anchors

### Fig.1: `timely_full_interval_case`

**正文职责：** Introduction: explain the measured service gap before protocol terms
**允许结论：** One actual c16 computation-only interval; first display and continuous availability are distinct.
**来源：** experiments/dsn_full_interval_case_20261029/RESULTS_v2/{SUMMARY,ACTUAL_TRACE,ACTUAL_SNAPSHOTS}.json; extraction source_v2/case.py (8970f923c2ef8ca066eb963e7a1ba8664829159e CPU extraction; f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf neural execution).

**Main caption (English):**

Timely first delivery can still leave a gap in delivered progress. In an actual computation-only c16-staggered run, a complete non-EOS two-second interval ending at F=14 s is first displayed at 1.444 s, withdrawn by a compatible selected-root update at 1.544 s, and restored with identical whole text in the certified view at 3.720 s. The update returns the frontier to F=12 s; shading marks the 2.176 s visibility gap, and the vertical line is the original two-second D2 read point. The view introduces 37 raw Unicode code points (31 non-whitespace), replacing one punctuation mark; these are not character/audio alignments. Compatibility uses the actual complete consumed input and selected parent state, not text equality alone. First-delivery D2/C8 credit is unchanged. This post-hoc c16 overload case illustrates a failure mode, not its incidence or a whole-run SLO win.

### Fig.2: `coordination_protocol`

**正文职责：** Coordination: mechanism bridge beside the native Full-call algorithm
**允许结论：** A complete original call may remain eligible despite wrong own prediction or producer exit; UI support is independently checked.
**来源：** Native source_v2/fullspec_policy.py:29,48,139,151,166; resilience_policy.py:150,274; candidate_bridge.py:20; resilience_channel_close.py:58; resilience_consumer.py:26,48. Final native execution source 4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47; diagram itself makes no measured-performance claim.

**Main caption (English):**

Eligibility, original selection, and whole-view support are separate decisions. (a) Child j runs the complete original call on frozen P-hat_2. Its prediction P-hat_3 may be wrong while original C/U legitimately returns P_3. Strictly accepted complete buffer B survives producer exit with its original UID/birth/incarnation; future messages are fenced. Matching actual selected P_2 later confirms the input; ordered selection requires durable sync before install and Consumer use. (b) A failed whole-view guard withdraws h without refuting an unresolved future call input. UNKNOWN authorizes neither commit nor a cancellation proof. Assumptions are complete feedback-sensitive state and frozen audio/target/EOS/model/decoding contract, faithful owned original C/U, single-Owner selection, exact input/identity checks, durable sync, and Consumer order/parent checks. Sealed-channel tail receipts are validated before fencing. Retained views are whole, without suffix splicing. This causal schematic has no measured time axis.

### Fig.3: `service_region`

**正文职责：** Evaluation: operating-workload comparison and negative boundary
**允许结论：** First visibility, all-offered timely credit, and later compatible deficit are different endpoints; all48 including c12 remain.
**来源：** experiments/dsn_midpoint_continuity_20261029/combined_source_v3/plot_48.py; COMBINED_DATA_v1/RUN_ENDPOINTS.json. Original plot commit e3bd518babdba3edb05156739451ea3464676da8. Original36-only plot_service_region.py is read-only context, not the 48-run source.

**Main caption (English):**

First visibility, timely credit, and subsequent visibility loss are different endpoints. All 48 fresh-process runs are shown: four explicit development workloads 脳 four arms 脳 three repeats. R retains eligible computation; S retains supported whole views. Shapes and colors identify arms; horizontal ticks are medians and vertical lines span the three observed values, not confidence intervals. Panel (a) uses actual Consumer first-visibility P99, with the original D2 threshold; (b) uses all offered audio intervals and the original 2 s display / 8 s certified-view deadlines. Panel (c) is the secondary deficit area from later loss of previously dual-timely intervals whose complete prior view remains compatible with the new selected root. Single-root windows are right-censored at the next Canonical root if no covering view returns sooner; necessary incompatible revisions remain separate and original first credit is unchanged. The exploratory c12 midpoint and its negative deadline result are retained. Original36 plus midpoint12 reuse development audio; c16 expands the metadata-nested source mix. Sync arrivals are simultaneous and staggered arrivals are 0.25 s apart. Workloads are not a pure capacity sweep; no lines interpolate between them.

## Explicit mechanism contract and notation

- `P` denotes the complete sufficient cross-call state at its actual frontier, including bound text. Hat states are predictions, not selected facts. Other frozen inputs include audio/source, target/EOS, model, decoding and runtime contract. Equal text alone never confirms a complete input.
- The child is one complete owned original ASR→C/U call. Its early typed identity prediction `P-hat_3` is not the original selected result `P_3`; input confirmation does not certify its own prediction. There is no candidate suffix splice or substitute correction/update.
- Eligibility requires exact current parent equality; a decisive unequal selected witness must be at that call’s own start frontier. An earlier lost ancestor can break view support without refuting an unknown future complete input. UNKNOWN has no commit authority and is not a cancellation proof.
- Strictly accepted complete B is retained with its original UID, birth, and worker incarnation. Confirmed OS exit / closed readers allow sealed-channel validation before incarnation fencing; future new old-incarnation messages are fenced. Producer exit does not delete accepted B. Ordinary native terminal release and death replacement do not adopt the core batch-drain rule.
- The single Owner retains original selection authority; durable sync D precedes install. Consumer checks bound fact order and actual parent before use. Supported h is retained whole; unsupported h is withdrawn separately.
- Conditional guarantees rely on the sufficient complete state cut, faithful execution of frozen original input, owned identity binding, exact matching, durable storage, serial selection and ordered Consumer checks. They do not establish human transcript correctness, whole-program refinement or arbitrary GPU bitwise repeatability.

## Numeric and rendering QA

- Fig1 exact seconds: D=1.4439057689160109; withdrawal=1.543663284741342; certified return=3.7196051217615604; gap=2.1759418370202184. 37 raw Unicode code points / 31 non-whitespace; complete non-EOS interval F=12→14 s; original D2=2 s lies in the gap. c16 overload remains explicit.
- Fig3: all48 original cell IDs and raw numeric metric values are exact; only credit is scaled ×100 for percentages. Medians and observed min/max use the original plot formula. No CI, fitted line, interpolation, denominator change or extra independent source is introduced.
- c12 Joint P99 values remain 2.196642, 2.298685 and 2.227745 seconds (rounded here only); all exceed D2. Compatible deficit is the original secondary single-root right-censored metric; incompatible revision losses remain separate.
- Final sizes: Fig1 7.125×2.65 in; Fig2 7.125×3.00 in; Fig3 7.125×2.65 in. Minimum plotted font 8.5 pt at 7.125 in width. PDF fonttype42 yields embedded CID TrueType, no Type3; SVG keeps editable text. Gray cues use marker shape, hatching, dashed borders/lines, and explicit action labels.
- Actual PDF page images were inspected. The initial Fig1 withdrawal note crossed the certified line; the final review2 source moves it clear. Initial outputs are preserved separately in FIGURES_dev_v1_initial and the annotation-refined intermediate in FIGURES_dev_v1_review1.

## Reproduction and artifacts

- `figure_source_dev/` is an independent clean Git repository containing 97,136 bytes of byte-matched bounded JSON inputs and the renderer, config, and source map. The old plot sources and v2 manuscript figures remain unchanged.
- `FIGURE_SOURCE_dev_v1.json` records the full resolvable renderer commit and all10 tracked file bytes/SHA. `FIGURE_SOURCE_dev_v1.bundle` carries its Git history. No CURRENT or GitHub action was taken.
- Run `python redraw_figures.py --out ../FIGURES_dev_v1_reproduction` from figure_source_dev. The output directory must not yet exist. The sibling complete source manifest is checked before and after rendering; original protected file hashes are verified where specified.
- `FIGURES_dev_v1/` contains final PDF/SVG/PNG, actual PDF page and grayscale previews, captions, CONFIG/ENVIRONMENT/RUN_RECORD/SUMMARY/GATE, exact PLOTTED_NUMERIC_VALUES, and source/output SHA records.
- `FIGURE_QA_dev_v1.json` is the human visual plus exact numeric/source QA record. Automated output GATE does not itself pretend to be human visual review.

Final palette refinement: blue denotes protected computation (open triangle for R-only; filled dark-blue diamond for Joint), teal denotes provisional whole-view retention, and red is reserved for unsupported/refuted withdrawal. The final Fig3 PDF and grayscale render were re-inspected; all48 values were rechecked exactly.

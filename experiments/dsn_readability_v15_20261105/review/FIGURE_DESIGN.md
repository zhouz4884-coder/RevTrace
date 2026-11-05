# Fig. 1 action callouts (v15)

The causal point is the response to an actual compatible selected-state
application. The two policies have different interleavings, so these are two
recorded examples on the same input interval, not an aligned counterfactual.

Design changes are limited to two short neutral leaders and a modest height
increase from 3.10 to 3.25 in at the unchanged 7.125-in final width. The first
leader states `12-s snapshot replaces valid 14-s view`; the second states
`14-s state installs; 16-s view remains`. The first is anchored at the real
1.543663284741342-s selected-12-s application; the second is anchored to the
retained whole view at the real 3.7943886145949364-s selected-14-s application.
The original stair samples, x and y limits, deadline, first-delivery and
certification times, miss disclosure, and compatible gap are unchanged.

The upper callout occupies white space above the withdrawal band. The lower
callout sits above the 14-s whole-view segment and leads to the retained
16-s whole view, avoiding the selected-coverage stair. A direct diagonal
leader to the 14-s selection would cross the real 16-s arrival vertical at
3.4643774135038257 s; anchoring to the whole view at the exact later
installation time makes the `remains` action explicit. Font sizes remain
8 pt for labels and 9 pt for panel titles and the gap number. The original
teal/blue semantics and hatch treatment remain in use. PDF and SVG remain
editable vector output; 300-dpi color and gray previews support print QA.

Frozen rendering and color/gray visual QA are complete. Source commit is
`fd8fe368e7327d36221fd1860767ec60cfd0ceeb`; the complete five-file source
manifest is `FIGURE_DESIGN_SOURCE_v1.json`, SHA-256
`3983d7b8ce4f71843899abd7b7597c36547b16b8f84c404302d870899aae1044`.
The root no-argument preflight passed before rendering; the explicit
source/manifest/run-record preflight passed and is preserved in
`FIGURE_DESIGN_PREFLIGHT_v1.json`. The default current-source pointer remains
unchanged. Config, environment, run, and final QA records use the same `v1`
suffix in this review directory.

The local bounded derived output is `../figures/EXPORT_v1/`. Both previews
were inspected. The PDF is 513 by 234 pt (7.125 by 3.25 in), contains no
embedded raster image, and its smallest text span is 8.0 pt. Both action
callouts and leaders remain clear of the observed stairs. The gap hatch,
the 1.444/2.027-s first deliveries, and the D2 +27.4-ms miss remain visible.
The lower leader identifies retained F16 at the selected-F14 event rather
than falsely identifying the earlier F16 arrival. The original immutable
case input was verified byte-identical after rendering. The source checkout
remains clean. No model call, service reader, or other figure render occurred.

The final local editorial gate is PASS. Root will copy/archive these derived
outputs to the designated 8-TB experiment-disk path recorded in
`FIGURE_DESIGN_RUN_v1.json`; that archive step remains outside this bounded
figure task. This change supports readability only, not a new service result.

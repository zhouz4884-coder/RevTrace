# Figure 7 contract -- V100 dual-plane scaling

- **Core conclusion:** balanced proposer/authority replication scales the
  display plane to c64, while certified commit latency and authority balance
  expose a distinct, model-dependent state-write boundary.
- **Archetype:** quantitative 2x2 grid with one scaling hero panel.
- **Backend:** Python/matplotlib only.
- **Target/output:** FGCS two-column width; editable SVG/PDF, 300 dpi PNG, and
  600 dpi TIFF.
- **Panel a:** independent V100 c16 operating points (SG, Hybrid, Coarse) show
  that the main method benefit survives the separate hardware contract.
- **Panel b (hero):** repeated p4a4 audio throughput over c32/c64/c128, with
  median and min--max ranges; c64 is the display-SLO headline.
- **Panel c:** display P99 and certified segment-commit P99 are shown as
  separate estimands, with the 2 s line scoped only to display.
- **Panel d:** c64 allocation sensitivity (p1a1, p4a4, p3a5) relates
  throughput and authority/proposer service ratio to the two-stage cost model.
- **Primary evidence:** repeated V5 p4a4-c64 throughput and display P99.
- **Validation evidence:** repeated c32/c128 boundaries and p3a5 sensitivity.
- **Statistics:** three deterministic repeats per V5 cell; center is median;
  interval is min--max. No significance claim is made from n=3.
- **Source data:** V1--V4 frozen V100 summary plus the V5 repeated headline
  summary and raw per-repeat JSON records.
- **Reviewer risk:** do not call c64 a universal certified-state capacity; do
  not transfer the display SLO to segment commit; do not pool V100 values with
  the RTX 3090/vLLM contract.

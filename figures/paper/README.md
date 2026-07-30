# RevTrace paper figures

This directory contains the non-architecture manuscript figures:

- `figure2_batching_opportunity_and_state_risk`
- `figure3_deployed_efficiency_and_risk`
- `figure4_contract_adaptation_and_generality`
- `figure5_long_horizon_holdback_closure`

Each figure is exported as editable SVG, PDF, 600 dpi TIFF, and a 300 dpi PNG
preview. The generator renders a raw TIFF and uses `tiffcp` for lossless LZW
compression when available because the compressed-TIFF codecs in the current
Windows/Pillow runtime terminate during encoding. SVG and PDF are the primary
submission formats.

Rebuild and validate the redesigned main figures from the repository root:

```powershell
python scripts/figures/plot_revtrace_paper_figures_v2.py
python scripts/figures/validate_revtrace_paper_figures_v2.py
```

The exact plotting tables, including a `source` provenance column, are under
`figures/source_data/`. Figure contracts and complete manuscript legends are
under `docs/figures/`.

The earlier `plot_revtrace_paper_figures.py` is retained as the provenance
extractor and first-layout reference. The v2 renderer consumes the frozen CSV
tables and produces the submission candidates. The experimental evidence atlas
is an exploratory composite and is not part of the numbered main-figure
sequence.

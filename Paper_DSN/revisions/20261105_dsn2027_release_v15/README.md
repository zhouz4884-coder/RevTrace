# Anonymous DSN 2027 manuscript source, v15

Compile main.tex with PDFLaTeX, BibTeX, then PDFLaTeX twice. All manuscript
and vector inputs are included. The original v13 scientific evidence
companion remains frozen and is supplied separately under its original name.
The v15 source archive additionally includes the standalone updated Fig. 1
renderer, configuration and exact original numeric input in
figures/figure1_source/. With Python, matplotlib and PyMuPDF installed:

    python figures/figure1_source/render.py --out new_figure1_export

This reproduces the v15 action annotations without private Git metadata.
It does not rerun models, change events or align the two executions.
The frozen companion contains original source/configuration snapshots,
summaries and raw-log indices; full journals, recordings and weights are
external resources. Other three main figure inputs remain unchanged.

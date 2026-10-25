# Physical cost / grain / workload boundary — before plotting

Conclusion: smaller/larger certification grains exchange real GPU energy and
certification latency under a workload-specific visibility deadline. This plot
does not establish an exclusive DGFT advantage, a universal grain optimizer,
a nonmonotonic transition, or a maximum steady-state capacity.

Three separate facets:PhaseD new-pool c4stagger/c8sync, and repairedT1 c16sync.
Never connect the low-load PhaseD points to T1 as one scaling curve. Different
source pools and visibility clocks remain explicitly labeled. Within each
method/load there are3measured repeats; error bars show range, not confidence.

Source:byte-verified published CSVs, old measured identities preserved. T1 uses
onlyobs1/full-observer rows, notobs0. PhaseD uses only final R4_strict/R2_transfer
with strict task-audio warmup isolation; preliminaryR4_formal is excluded, not
silently used because of its name. Full Standard remains a successful control.
Quality is supplied in source data/caption, not asserted equal acrossrho.

Layout:three faceted energy-vs-displayP99 scatter panels; same units, separate
limits marked,2sdisplaytarget; exact CommitP99/quality in associated data and
caption. PDF/SVG vector plus300dpiPNG, Times New Roman house font, print-safe
shape+color; noType3. No newGPU measurements or incomplete N5 results plotted.
Paper2column width7.2in; final candidate may choose a subset only with same caption.

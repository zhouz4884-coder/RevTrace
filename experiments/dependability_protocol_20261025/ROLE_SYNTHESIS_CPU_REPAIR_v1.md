# Auxiliary aggregation fixture repair, no runtime/GPU changes

First pilot-control run of summarize_role_formal_v3.py failed while exporting
an empty REPEAT_HISTORIES table:the pilot has only repeat0, so no repeat1 pair
exists. First three partial CSVs retained under role_pilot_synthesis_v3; no
SUMMARY was written. This is not a failedGPUcell, changed model output or
evidence of equality. Repaired exporter supplies the empty table's explicit
columns and prints repeated-history status null when no repeatpair exists.
New destination v4 keeps old partial outputs rather than overwriting them.
Formal64 remains2freshrepeats and requires32actual repeat-history comparisons.

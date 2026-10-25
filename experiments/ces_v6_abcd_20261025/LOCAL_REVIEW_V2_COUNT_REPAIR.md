# Local audit metadata count repair

V1 independently recomputed all98 actual service cells (events/frontiers,
quality, power integral and physical calls). Its per-stage `online_cells`
metadata was incorrectly3 because a reused loop variable `n` in the four
quality components shadowed the expected stage size. The actual CSV counts
were2/24/18/18/36 and all metric checks ran, but the final metadata summed15.
The final98-cell publication gate rejected that report. V1 outputs/source are
preserved and must not be treated as the final complete audit receipt.

V2 uses a distinct expected_cells variable and asserts the actual verified
check count matches the frozen summary. It reruns the same raw bytes with no
GPU execution or measurement changes. Final audit path is local_review_v2/.
The old and corrected numerical CSV files are also compared byte-for-byte.

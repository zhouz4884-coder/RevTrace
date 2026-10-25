# V1 diagnostic output, not the final audit receipt

The numerical tables checked all98 real service runs, but the per-stage count
metadata was shadowed by a quality-loop index and incorrectly reported3.
Use ../local_review_v2/ for the corrected final98-run audit. The15 numerical
CSV pairs are byte-identical; see ../LOCAL_REVIEW_NUMERIC_EQUIVALENCE.json.
V1 is retained so the checker failure is visible, not deleted or relabeled.

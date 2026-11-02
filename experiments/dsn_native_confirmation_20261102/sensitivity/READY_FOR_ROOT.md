# Old final4f deadline sensitivity: ready for freeze

Only static source/file work has been performed. No tests, sensitivity calculation, raw reader, model, remote operation, CURRENT or paper change occurred.

## Minimal input index

1. `experiments/dsn_strengthening_20261031/PAIRED32_V2_RESULTS/{SUMMARY,GATE,CONFIG}.json` (select all16 `version=final` cells; retain bdfa archive unchanged).
2. `experiments/dsn_strengthening_20261031/RESIDENT4_V2_RESULTS/{SUMMARY,GATE,CONFIG}.json` (four trials,16 original-clock requests).
3. `experiments/dsn_streamcorrect_independent_20261029/SOURCE_RECEIPT_v1.json`,7808bytes, SHA256 `2040995aa06a5c7958479fe42397d65e299c8a4505de18b35f44099edd9e3b9e`. This binds each source's original EOS/frame extent independently of the endpoint lists. It is historical acquisition metadata, not the final4f execution source.

These seven bounded JSON files are enough; original waveform, model, Consumer raw and text-normalization replay are unnecessary. Root may point the frozen config at their existing byte-identical8TB counterparts.

## Source

`source_dev/` contains five new Python files plus README/DEPENDENCIES and two byte-identical a13 pure-stdlib helper files under `vendor/`. Original endpoint source is `a13fa0a335529dc188f7e738877a3acd027ce4a7`; the full manifest SHA8cadff… is recorded. Only its original quantile/finite implementation is reused; new analysis has its own complete source identity.

Root freezes this independent directory and complete manifest, runs formal controls (`test_sensitivity_controls`,nine controls), then calls `make_config.py` and the formal `analyze_sensitivity.py` with config/manifest/prelaunch. Entries/required prelaunch fields are in source README. New raw/summary/gate remain8TB.

## Contract

- Fixed23-point display grid0.5–6s in0.25s increments; C8 fixed8s. Original D2 point, unweighted linear P99, all offered/partial EOS, matched6/8 and resident7/8 remain hard positive controls. No alternate-budget pass counters are produced.
- Audio-duration weighting uses the original intervals; denominator is always all offered audio, including missing/C8-failed mass. Full finite CDF uses every observed D knot; there is no tail cutoff or renormalization.
- Combine two timing repeats inside each source. Show four paired source gains separately for matched and resident, which reuse the same four speakers. No272/544-frontier significance, no pooled8-speaker claim. Four-source envelopes and two-repeat whiskers are descriptive ranges, not CI.
- Curve direction, crossovers and negative source gains are results, not failure gates; no favorable threshold selection.

Optional `--render` produces the two-bank deadline plot, complete-CDF companion and source-paired D2 plot (editableSVG/vectorPDF/PNG). It follows the scientific-figure-making skill, existing Python/matplotlib backend, full0–100% scale, D2 marker, minimum8.5pt at full7.125in width. Root must inspect actual PDF pages before publication; core CPU analysis does not require matplotlib.

## Duplicate check and independent review

Filename search across experiments/docs/Paper_DSN for sensitivity/CDF/threshold/budget_sweep and modern strengthening/writing/story/editorial report search found no existing equivalent final4f deadline-sensitivity artifact. The only new matches are this directory; historical hashes/path substrings were not treated as evidence of an existing CDF.

The independent feedback/statistics reviewer agreed with all-offered weighting, four-source pairing, fixed grid and unchanged positive controls; its suggested independent source-EOS binding was added using the original7808-byte source receipt. Review was read-only; no execution PASS is claimed.

# RevTrace Experimental Evidence Atlas

## Intended paper claim

The atlas is a dense main-results candidate, not an architecture diagram. It supports one
linked conclusion: RevTrace converts execution-shape-sensitive revision generation into a
fast deployed service while jointly respecting tail-latency, risk, quality, energy, and
display-authority contracts.

## Evidence grammar

| Panel | Visual form | Encoded evidence | Boundary |
|---|---|---|---|
| a | 3D configuration landscape | concurrency, audio horizon, wall-clock speedup, joint-contract outcome, energy efficiency | Configurations are directly measured cells; marker color is categorical, not a continuous score. |
| b | risk-latency phase trajectory | learned threshold, anytime risk upper bound, P99, goodput, live c16-c64-c16 path | The risk boundary is 0.5%; the shaded region is the joint safe region. |
| c | replicate scatter plus covariance ellipses | two-GPU speedup, state-entry P99, five independent runs per model, energy reduction, risk UCB | Ellipses summarize replicate covariance; they are not confidence regions for population prevalence. |
| d | causal flow plus exactness profile | execution-shape divergence, feedback amplification, same-input controls, token/partial/final exactness | The controls separate numerical execution effects from state leakage and random decoding. |
| e | long-horizon progression plus seed fan | continuous baseline, checkpoint/rebase, checkpoint-20 holdback, five 120-s seeds | The seed fan reports P50/P95/P99 and does not claim mathematical zero failure. |
| f | forest plus authority distribution | paired WER/CER deltas, holdback quality, provisional-to-authoritative overwrite behavior | Shaded quality band is +/-2 percentage points; authority behavior is reported independently. |

## Visual design contract

- One information-dense master figure with six complementary visual grammars.
- Only the configuration landscape uses 3D, because it encodes two independent workload
  axes and a performance surface; no decorative perspective is used elsewhere.
- Direct labels replace a large detached legend where practical.
- Navy, teal, and coral retain stable meanings: baseline/model identity, joint pass, and
  boundary failure or unsafe drift.
- Vector exports preserve editable text. PNG is 300 dpi class; TIFF is 600 dpi class.

## Automated and manual QA

Run:

```powershell
python scripts/figures/plot_revtrace_results_atlas.py
python scripts/figures/validate_revtrace_results_atlas.py
```

The renderer fails closed on major title/subtitle collisions. The validator checks source
table counts, sentinel values, vector editability, raster resolution, risk/SLO contracts,
and the completed original-resolution manual review.

# RevTrace Phase 3C RIR population report

Decision: **PHASE3C_MECHANISM_CONFIRMED_POPULATION_GATE_NOT_MET**

| Model | Distinct pairs | Natural | Stress | Mean RAF | Terminal difference | Unrecovered at horizon | 50-pair gate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | 19 | 6 | 13 | 5.481 | 0.316 | 0.316 | NOT MET |
| Qwen3-ASR-1.7B | 15 | 4 | 11 | 4.744 | 0.200 | 0.200 | NOT MET |

The execution-shape stress produced many output flips, but most were either
absorbed by the official state projection or repeated the same state pair.
This confirms that output-flip counts cannot substitute for a state-pair
population.

Natural, waveform-stress, and independent-speech stress evidence remain
separately labeled in `summary.json`. Stress pairs are eligible for the legal
distinct-pair population gate, but their trigger rate is never used as a
production prevalence estimate. Numerical
State Exposure uses the preregistered natural flip-rate multiplier and is
therefore reported as a bounded exposure index, not a production error rate.

The mechanism-level RIR results are retained, while the preregistered
50-distinct-pair generalization claim remains outside the paper unless the gate
is met by additional independent inputs.

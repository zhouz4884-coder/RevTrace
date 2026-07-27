# Revision Impulse Response pilot

This is a two-model, one-pair-per-model pilot. It is not the preregistered
Phase 3C population gate.

| Model | Decision | Initial state distance | Half-life | RAF | Terminal difference |
|---|---|---:|---:|---:|---:|
| Qwen3-ASR-0.6B | `RIR_PILOT_NO_STATE_IMPULSE` | 0 | N/A | N/A | N/A |
| Qwen3-ASR-1.7B | `RIR_PILOT_PASS` | >0 | 1 revision | 1.0 | 0 |

For 0.6B, the legal FP16 execution-shape output flip was absorbed by the
official rollback/state projection, so it is invalid to initialize an impulse
response with `D(0)=0`. The runner records this boundary instead of inventing
an amplification statistic.

For 1.7B, the state-entry impulse was real but reconverged after one future
canonical revision under identical future audio. The measured numerical state
exposure is `0.0041666667`, using the frozen natural flip-rate estimate.

These results reject a universal persistent-amplification claim. A paper-facing
amplification result still requires the Phase 3C gate of at least 50 legal
state-entry flip pairs per architecture, with natural and stress evidence
reported separately.

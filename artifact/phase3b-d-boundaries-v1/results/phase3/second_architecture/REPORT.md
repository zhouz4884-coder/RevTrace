# RevTrace Phase 3D second-architecture report

Decision: **PHASE3D_SECOND_ARCHITECTURE_BOUNDARY_PASS**

Architecture: **Voxtral-Mini-4B-Realtime-2602**

- revisions: 10
- execution rows: 120
- singleton repeat mismatches: 0
- cross-shape mismatches: 0
- pollution half-life: None
- RAF: 0.0
- NSE: 0.0
- input tiled to requested duration: True

The second architecture is interpreted through its actual state semantics.
Decoded text is not automatically treated as model-feedback state.  A
growing-prefix Transformers probe is a boundary experiment and is not
presented as vLLM websocket-serving performance.  Zero observed
execution-shape flips is not a deterministic certificate, and a deterministically
tiled public waveform provides revision coverage rather than dataset
generalization.

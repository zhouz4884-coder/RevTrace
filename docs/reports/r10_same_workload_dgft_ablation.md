# R10 same-workload SG / DGFT ablation

Decision: **COMPLETE_R10_ABLATION_WITH_SG_TAIL_BOUNDARY**

All cells use the same 16 bilingual 30-second sessions, synchronous arrival, two RTX 3090 GPUs, and 2-second fine revisions. SG uses an FP16 singleton authority per selected revision; DGFT groups three fine revisions under a 6-second FP32 batched authority. Event counts therefore differ and are not used as throughput.

| Model | Adapter | Wall | GPU-norm | Energy reduction | Replay / verify | Authority / proposer | Display P99 | State/segment commit P99 | SG 2s state-entry miss | Reference edit P95 | Tx/trace violations | Path SLO |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.6B | sg | 5.10x | 2.55x | 69.1% | 8.33% | 0.430 | -- | 2.735s | 3.33% | 0.00% | 0 | FAIL |
| 1.7B | sg | 4.68x | 2.34x | 66.1% | 9.58% | 0.478 | -- | 2.964s | 4.17% | 0.00% | 0 | FAIL |
| 0.6B | coarse-dgft | 6.88x | 3.44x | 59.8% | 0.00% | 0.684 | 0.826s | 2.582s | -- | 3.43% | 0 | PASS |
| 1.7B | coarse-dgft | 6.06x | 3.03x | 51.0% | 0.00% | 0.829 | 1.018s | 3.219s | -- | 1.79% | 0 | PASS |
| 0.6B | hybrid-dgft | 5.19x | 2.59x | 51.3% | 5.00% | 0.700 | 0.782s | 3.853s | -- | 2.15% | 0 | PASS |
| 1.7B | hybrid-dgft | 3.92x | 1.96x | 33.2% | 8.75% | 0.853 | 0.990s | 4.437s | -- | 1.79% | 0 | PASS |

Quality is path-relative. SG reports exact revision-trace disagreement against an independent FP16 singleton replay. DGFT reports mixed-unit final edit rate against an independent FP16 singleton reference. These columns are not pooled with Whisper's WER delta against unprotected feedback execution.

Latency scopes are also explicit. SG reports the latency at which a 2-second revision acquires feedback-state authority. DGFT reports provisional display latency separately from the 6-second authority-segment commit latency. A dash means the SG runner did not separately instrument pre-authority provisional display.

SG is the same-granularity special case of DGFT: proposal and authority granularities coincide, the directional-coverage witness degenerates, and selective fine replay becomes risk-triggered re-verification. The FP16 singleton and FP32 batched authorities are distinct versioned canonical paths; no bitwise identity is claimed between them.

The SG terminal-burst SLO result is retained even when it fails. It is a tail-latency boundary, not a transaction-correctness failure.

## Direct same-workload delta versus SG

These ratios use measured service wall time and service joules for the identical 480-second audio workload; they do not divide two separately measured baseline-normalized speedups.

| Model | Adapter | Service throughput vs SG | Wall-time reduction | Service-energy reduction |
|---|---|---:|---:|---:|
| 0.6B | coarse-dgft | 1.385x | 27.8% | 4.4% |
| 0.6B | hybrid-dgft | 1.033x | 3.2% | -16.8% |
| 1.7B | coarse-dgft | 1.276x | 21.6% | -15.1% |
| 1.7B | hybrid-dgft | 0.847x | -18.0% | -54.2% |

## Excluded-run repeat control

The provenance-incomplete 1.7B run is excluded from headline metrics but retained as a repeat control. Across 240 matched revisions it has 0 selected-output, 0 state-projection, and 0 verification-decision mismatches versus the accepted rerun.

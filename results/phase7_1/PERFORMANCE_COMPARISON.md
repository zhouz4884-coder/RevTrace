# Phase 7.1 corrections and performance comparison

## Decision

`PHASE7_1_EVIDENCE_REPAIRED_AND_PERFORMANCE_POSITION_FROZEN`

RevTrace has a strong measured systems advantage over the all-canonical
deployment baseline.  It does **not** yet support the claim that it beats every
published SOTA end to end: the published systems target text-LLM decoding,
request-owned TTT state, or deterministic operator subgraphs rather than
Qwen3-ASR revision feedback on the same hardware.

## P0 — canonical provenance

- Phase 6D used a **float32 fixed-shape authoritative draw** (`b16`).
- Phase 7D used a **float16 fixed-shape authoritative draw** (`b16`,
  `FLASH_ATTN` requested).
- The two are separate versioned contracts.  The runner now derives the
  fingerprint from runtime provenance rather than hand-written text.
- Kernel accumulation and vLLM sampling/log-softmax dtypes were not exported
  by the historical runs and remain explicitly `unrecorded`.

## P1/P2 — corrected event and risk semantics

- Online selection-authority violations: **0**.
- Later canonical replay disagreements: **2 output / 1 state**.
- Unverified selected-vs-later-replay disagreements: **1 output / 0 state**.
- Stale/wrong-epoch commits: **0**.
- Phase 7D therefore establishes an authoritative draw per commit, not
  repeatability across two independent canonical draws.
- The finite correlated trace is reported as `1/960 = 0.1042%` state replay
  disagreement.  The invalid iid Clopper-Pearson population claim is removed.
  Formal risk evidence remains the Phase 2 anytime audit.

## Intuitive same-system comparison

| Comparison | RevTrace result | What it means |
|---|---:|---|
| 0.6B c16 wall/SLO speedup vs all-canonical | 5.99x | strong live serving gain |
| 0.6B c16 GPU-normalized gain | 3.00x | gain remains after charging two GPUs |
| 0.6B c16 P99 / misses | 1.336s / 0 | meets 2s SLO |
| 1.7B c16 wall/SLO speedup vs all-canonical | 4.83x | strong live serving gain |
| 1.7B c16 GPU-normalized gain | 2.42x | gain remains after charging two GPUs |
| 1.7B c16 P99 / misses | 1.730s / 0 | meets 2s SLO |
| c64 overlap vs sequential verifier path | 1.68x, P99 -40.3% | overlap is a causal runtime win |
| c64 energy reduction from overlap | 34.4% | not just latency shifting |

Five-run replication is also strong:

- 0.6B: mean 6.052x,
  worst run 5.935x,
  max P99 1.582s.
- 1.7B: mean 4.949x,
  worst run 4.830x,
  max P99 1.730s.
- Across these runs: zero deadline miss, output/state violation, and stale
  commit.

## RevTrace versus the strongest same-trace unsafe policy

The overloaded c32/Chinese/burst cell is deliberately retained:

| Mechanism | Goodput | P99 | Energy | Observed state disagreement |
|---|---:|---:|---:|---:|
| fixed-margin 0.05 | 3.910 evt/s | 5.591s | 13.760 J/audio-s | 1 |
| RevTrace scoped repair | 3.046 evt/s | 6.107s | 15.268 J/audio-s | 0 |

RevTrace is 22.1%
slower in goodput, 9.2%
higher in P99, and
11.0%
more energy-intensive in this overloaded cell.  The benefit is removal of the
observed state error.  The cell remains outside the 2s SLO and is not a
performance win.

## Published SOTA context (not an apples-to-apples leaderboard)

| Work | Published headline | Why it is not directly rankable |
|---|---|---|
| [LLM-42](https://arxiv.org/abs/2601.17768) | 2.2x decode throughput over deterministic SGLang in a selective-determinism setting | text-token serving, different hardware/workload |
| [MarginGate](https://arxiv.org/abs/2605.30218) | 15.05–18.56% verifier triggers; 1.99–2.23x lower latency increment than LLM-42 | text LLMs, no ASR revision transaction |
| [RW-TTT](https://arxiv.org/abs/2605.28053) | 9.31x vs sequential, 3.44x vs per-stream replicas | request-owned TTT state, different semantic object |
| BIO/TBIK source probes | operator/subgraph determinism | incomplete audio-to-token dependency path |

The defensible position is:

1. RevTrace is **clearly ahead of all-canonical execution** on the same
   Qwen3-ASR workload: 4.83–5.99x wall/SLO and 2.42–3.00x GPU-normalized.
2. It is **safer but not always faster** than an unsafe fixed-margin policy;
   c32 quantifies the price of removing a real state disagreement.
3. Published SOTA headline numbers cannot be used to claim a direct win until
   they natively run the same revision-feedback workload.  Our faithful
   adaptations show their missing transaction/risk-contract semantics, not an
   end-to-end speed ranking.

## P3 — capacity boundary

Phase 7D c16-wave measured P99 is
1.941840s.  It meets the hard
2s deadline, but with the registered 100ms guard reaches
2.041840s and therefore
fails guarded admission.  It is retained as an overload/backpressure boundary.

The fresh c14 cell completed 1470 events across 98 session episodes: P99 1.413s, guarded P99 1.513s, 0 deadline misses, and 0 observed replay-state disagreements.  It therefore passes the registered 100ms headroom contract.  Its 93.33% verification fraction is dominated by the deliberately long 1,350-event cold-start evidence window, so it is a capacity result rather than a steady-state throughput headline.

## P4/P5 — stopped branch and guarantee matrix

- BIO was not expanded: the current integration intercepts only part of the
  graph and cannot certify the complete audio-to-token path.
- The guarantee is now named **canonical-authoritative commit**:
  the selected state equals the online authoritative draw, while replay
  determinism is explicitly false.

## Runtime warnings retained

- The c14 log repeats the upstream tokenizer-regex warning.  All comparisons
  use the same frozen tokenizer, so same-contract scheduling and performance
  conclusions remain valid; the run does not establish external transcript
  semantic quality.  Changing tokenizer behavior would create a new contract
  and requires a separate quality rerun.
- vLLM first tries to treat the local model path as a remote repository when
  looking up safetensors metadata, then successfully loads the local shard.
  This is a noisy lookup fallback, not a failed model load.
- Worker shutdown reports `destroy_process_group()` cleanup warnings after the
  result is written.  No result loss was observed, but explicit distributed
  cleanup remains a runtime-hygiene repair rather than a paper claim.

## Strongest current paper metrics

- 0.6B: **5.99x wall/SLO**, **3.00x GPU-normalized**, P99 **1.336s**.
- 1.7B: **4.83x wall/SLO**, **2.42x GPU-normalized**, P99 **1.730s**.
- Five-run mean: **6.052x** and **4.949x**.
- Anytime-risk audits: **30,025/30,155 eligible entries**, upper risk
  **0.480%/0.478%** at 95% time-uniform confidence.
- Causal overlap ablation: **1.684x** wall improvement, **40.3%** P99
  reduction, **34.4%** energy reduction, and deadline misses **128 -> 0**.
- Dynamic contract adaptation: **21.541–28.052 events/s**, P99
  **0.881–1.350s**, no admitted deadline miss, and **95.29%** fewer
  recertification events than flat relearning.

## Code and evidence changed

- `src/revtrace/phase7_1.py`: runtime provenance, corrected violation taxonomy,
  and guarded-capacity calculation.
- `scripts/remote/run_phase5a_live_adaptive.py`: automatic canonical
  fingerprint and provenance export.
- `scripts/finalize_phase7_c64_queue.py`: removes iid population-risk
  promotion and writes corrected taxonomy.
- `scripts/run_phase7_1_audit.py`: auditable performance/SOTA/capacity tables.
- `scripts/remote/run_phase7_1_c14_capacity.sh`: fresh c14 capacity run.
- `src/revtrace/phase7.py`: re-frozen guarantee matrix.
- `results/phase7_1/c14_capacity/run.log`: retained runtime warnings and
  loading provenance for the fresh capacity cell.

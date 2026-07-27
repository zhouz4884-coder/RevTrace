# RevBatch Gate artifact

Decision: `NO_GO_FOR_REVBATCH_EXACT_REVISION_GATE_B`.

Gate A passed with maximum live audio-throughput speedups of 11.073x for
Qwen3-ASR-0.6B and 8.752x for Qwen3-ASR-1.7B. Gate B failed after 1,699
revision events per model: neither model preserved the required 100% token,
partial-transcript, and final-transcript exactness. Gate C was therefore not
run.

The artifact includes the frozen contract, D0 source audit, full compact
per-cell records and bounded mismatch examples, formal logs, environment and
data hashes, report, and reproduction scripts. The public bilingual inputs are
performance/semantics stimuli only; no ASR quality claim is made.

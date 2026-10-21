# T1 instrumentation version ledger

T1 v2 finished all 18 cells; originals are retained, not overwritten. Its
canonical-content, certificate, WAL and display-publication audits pass.

Before final attribution, two observer issues were identified:

1. A last-observed `executing` message is not proof that the GPU is still
   executing at every later owner instant; completion might not yet be polled.
   Likewise the whole owner WAL call is not all physical fsync. V3 uses UNKNOWN
   for those instantaneous states where appropriate, keeps owner-call separate,
   and independently intersects actual start/complete/fsync stamps afterward.
2. Rich processor-input JSON was serialized/flushed inside the owner loop.
   Fine is overloaded at this tested c16 point, so even modest instrumentation
   work can accumulate in commit tails. V3 stores the already captured immutable
   rows in memory and writes the rich sidecar after run/power measurement.
   Actual input construction/hashing remains charged; no zero-overhead claim.

No scheduling predicate, source audio, model, dtype, rho, arrival, journal or
display contract is changed by this observer repair. V3 repeats the complete
12-cell factorial and six matched controls rather than splicing new timing
onto old results. Same-input and per-rho canonical/WAL equivalence are audited.
Both versions' performance, including any decline, will be reported.

V4 additionally separates worker start/preprocessing, synchronized GPU
model-call start/completion, worker postprocessing/completion, and owner
receipt. V2/V3's worker interval is NOT retroactively renamed GPU execution.
Missing model-call clocks remain UNKNOWN. The final complete factorial and
matched controls are rerun with the V4 clock carrier. Model-call time includes
the autoregressive launch loop; it is not literal summed CUDA kernel busy time.

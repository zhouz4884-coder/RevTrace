# RevGuard mechanism gate artifact

Decision: `MECHANISM_ORACLE_VALIDATED_EXACT_CERTIFICATE_UNRESOLVED`.

Same-input controls isolate BF16 batch-shape/runtime divergence from revision
feedback. A margin-threshold selective canonical verifier had zero observed
violations on the held-out c=16 shape and retained 2.88-2.99x single-GPU
speedup, but margin is not a deterministic certificate and verifier work was
not fully hidden. FP32 made singleton and batch execution internally exact in
the tested cells, while changing the frozen BF16 trajectory.

The artifact contains compact live records, frozen gates, report, environment
and data hashes, reproduction scripts, and a hash manifest. It makes no ASR
quality, production-frequency, or deployed two-GPU serving claim.

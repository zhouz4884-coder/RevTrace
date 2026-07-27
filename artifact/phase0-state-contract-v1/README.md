# RevGuard state-contract artifact

Decision:
`LIVE_MECHANISM_GATE_PASS_DETERMINISTIC_CERTIFICATE_UNRESOLVED`.

The packaged raw subset contains the default BF16 c=16 state-projection
controls, the default FP16 c=16 precision controls, and the two FP16 live
selective-verification runs. `RAW_INDEX.json` hashes all 18 repository raw
records, including attention-backend ablations.

The live mechanism had zero observed full-output and state-projection
violations over 480 events, 7.92-9.17% verification, 4.12-4.57x single-GPU
speedup, and verifier/proposer service ratios of 0.581-0.626. The margin rule
is an empirical scheduler signal, not a deterministic certificate.

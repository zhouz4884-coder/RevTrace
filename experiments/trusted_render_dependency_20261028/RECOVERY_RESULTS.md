# Declared equivalent renderer: actual cold recovery result

Actual runtime040fcc95f4cd3bbc4d918bc1dd4502b0b768990c; c4staggered,
fine2s/rho3, FP16P/GPU0+FP32A/GPU1, full row/kernel/D1, group-ready WAL,
accepted-input journal and actual local FIFOConsumer. All prefix histories use
the full native renderer. Both restart implementations declare the same new
allowed-renderer contract before those histories exist; restart order is
workers-first in all four arms. Cold process groups and GPU weights reload
with existing filesystem caches; not host/power/storage failure.

| Method / owner renderer | All old facts visible RTO | First new fact RTO | Precrash debt cleared | GPUJ/offered-audio-s |
|---|---:|---:|---:|---:|
|RevTrace/native|15.592s|19.714s|21.688s|130.42|
|RevTrace/light|2.471s|20.272s|22.292s|132.42|
|Standard/native|15.807s|19.041s|20.844s|122.18|
|Standard/light|2.515s|20.162s|21.990s|128.70|

All four exact logical fault cuts match
`18b46a217aff36de3fc045b92edafba83c743fa620cf01f517babaa2d5c3951e`.
Durable frontiers are unchanged, and18.51s of prepared accepted audio debt
survives in every arm. The independent full-native checker reconstructed185
observed rows,87complete physical-batch frontend inputs and56durable text
bindings, then recounted all three clocks directly from actual Consumer
records. It did not import the light renderer or call production admit().

Separate read-only postcheck source88d068b470660c7288d390633c19911a2ecfc2aa
confirmed identical precrash/recovery configs, both allowed implementations
in the contract, correct actual selected backend and the light owner's absence
of torch/transformers/qwen_asr/librosa before old-fact publication.
All four final certified coverage ratios are1;14unique transitions each;
recorded acknowledged-input loss/unauthorized admissions/false fresh views are0.
WER6.0606% and CERabout1.85% agree. Whole-runD2/C8fails in all four arms.

## Interpretation and gate

Old-fact RTO is reduced by13.121s (RevTrace) and13.292s (Standard), about84%.
This is real local-consumption recovery, not a CPU-only estimate or ledger-only
clock. It does not make new inference ready: first-new-fact and accepted-debt
clocks are slightly worse in these single trials, as is sampled board energy.
No statistical significance, universal RTO, full service recovery or exclusive
RevTrace algorithm advantage is claimed.

The implementation separates a deterministic, identity-pinned token→P/text
program from the heavyweight inference-stack import. It still re-renders
each selected fact, checks all bound fields, and restores the original input
obligations/clock. It does NOT trust cached published text plus a checksum.
Trusted program preparation and installed dependency identity remain premises;
this is not a claim that PyTorch can be absent or the host compromised.

Gate: PASS_DECLARED_RENDERER_REAL_COLD_AND_NATIVE_REPLAY. This closes the
previously unexhausted minimal-dependency part of goal5 and supports a practical
C3improvement/typed-recovery argument. Context-recovery quality and state-aware
scheduling NO-GO decisions remain intact. Original manuscript is unchanged.

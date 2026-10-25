# N5 independent validation freeze, 2026-10-26

This extends P0–P5 and GOAL_ADDENDUM, not a new CES/rho search. Development v1
(4 runs) and v2 (12 runs, one repeat) remain separate and cannot supply validation
significance. The four v1 pilot runs and all twelve v2 runs passed the independent
input/frame/actual-consumer audit. Asset/WAL replay remains a separate gate.

## Input and implementation identity

Independent metadata-only SHA-ranked selection:32 native 16–28s LibriSpeech
dev-clean/dev-other clips,32 distinct speakers disjoint from the conservative
historical pool; no output filtering. Manifest SHA256
c58574c1d5744f6b1bd078de4600da3077ba19cf1082b8d5e19011a4d870dba6.
Every reference, waveform digest and historical exclusion is retained. Nested
prefix source sets permit matched-input method comparisons, not independent
between-load confidence intervals. No repetitions of audio to fill concurrency.

Runtime v3 only adds opt-in SIGKILL observer traces to frozen v2 (21d15cb).
Normal episodes do not enable this diagnostic. All fault comparators enable
the same traces, including full pre-dispatch jobs, immutable worker receipts
and applied local Consumer rows. Diagnostic overhead is paid, not subtracted.
No CPU fixture is GPU evidence; observers are not a network/OS isolation proof.

## Controls and common budget

fine_fair (rho1); dgft_original (rho3, legacy no-expiry/nonbinding ingress budget);
standard_fair (rho3, complete Standard+fair limiter+ordinary expiry); queue_expiry
(same + ordinary queue gate); cde_age (age-only ablation); cde_full (actual
current-root visible progress, accepted debt and real queue/lease feedback);
standard_cde (complete conventional implementation given identical CDE policy).

All use fine2s, Proposer FP16 GPU0/Authority FP32 GPU1, row-complete/batch-drained,
same actual model/dtype/budget256, seed20261026, full A/B/C/D/D1/two_lane/WAL.
Shared fixed parameters:96 audio-s accepted/reserved debt cap (originalDGFT
exception explicit), warning4s/critical8s/clear2s, queue threshold8, new-session
unaccepted rejection after8s, tick5ms, Display2s/Commit8s. Not refit on validation.
No deadline bypass, cancellation of in-flight GPU or private Canonical writes.

## Frozen independent episodes

Seven methods × three fresh-process paired repetitions × six workload classes:

1. nonsaturated:4 synchronous streams;
2. near-capacity probe:8 uniform0.25s offsets (label is design, not measured capacity);
3. burst:16 synchronous streams;
4. finite sustained overload:32 uniform0.25s offsets;
5. return-low:24 unique streams, first4 at0s, next16 at20s, final4 at60s;
6. fault/recovery:8 uniform0.25s streams, SIGKILL of the owned process group at
   the first observed Authority physical dispatch at/after original episode14s
   (bounded waiting to22s; absence is a retained gate failure, not retiming by
   model outcome). Cold restart on the same physical GPUs, manifest, policy,
   original origin and both journals. Running abandoned work remains billed.

Five ordinary classes=105 runs; fault class=21 episodes, each has two attempts.
Methods rotated by repeat/workload, so no always-last CDE. All sources identical
within a workload/repeat, no future outputs/fault labels supplied to controller.
No other experiment runs concurrently. Source/weights/manifest/owned exits
verified at boundaries; unexpected occupancy stops without killing another task.

Before the independent fault class, a two-method development recovery probe
(Fine/CDE, old sources) must pass receipt, actual Consumer and input-debt checks.
Failure stops the fault class for diagnosis; it never erases previous raw work.

## Primary metrics and falsifiable gates

Reconstruct every offered fine frontier from immutable native audio and original
arrival schedule. Missing/rejected/unfinished frontiers have infinite latency,
zero dual credit; cannot disappear from P99 or quality denominators. Primary
Goodput is audio seconds with actual legal visible application<=2s and actual
certified view<=8s, divided by original elapsed arrival+drain (including fault
and model reload). Report all-offered coverage, actual A-C/R-C peaks, rejected
audio, input debt and late input receipts; mode alone is not a metric benefit.

Report unauthorized Canonical admission, stale-as-fresh, root-incompatible views,
CCE false-certified views, certified/offered coverage, legal provisional coverage,
Display/Commit P50/P95/P99 and whole-run dual-P99 pass, WER and English CER,
rollback/retraction, all physical GPU batches/rows, energy/offered and certified
audio, CPU/IPC/input-fsync/Canonical-WAL cost and accepted/reserved backlog. CPU
power unmeasured. Outer power includes actual killed work; serving and reload
clocks separate. Ledger replay ms is not service recovery time.

Safety gate:zero recorded invalid admissions/false coverage and all ACKed input
survives or is explicitly resolved; conditional on trusted owner/Authority,
immutable available audio, successful sync and intact storage. No unconditional
liveness or power-loss claim. Standard matching RevTrace is a positive control.

CDE algorithm promotion needs independent replicated reliable-service or
same-quality cost benefit over the strongest applicable safe ordinary control,
and a distinguishable effect from age-only/ordinary expiry. Pair by whole run,
report all three differences and uncertainty; do not bootstrap windows as runs.
If Standard+CDE matches, semantics/policy are portable, not DGFT-exclusive.
If no net advantage, preserve engineering correctness but mark new performance
contribution NO-GO. No post-hoc workload/parameter removal or unmeasured SLO claim.

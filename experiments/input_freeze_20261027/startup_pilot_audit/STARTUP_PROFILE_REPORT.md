# Measured trusted recovery startup opportunity

Six completed NORMAL cold-start development cells, source `fdb1b1e30b06ee781046621376f458431f3ecb9f`, one policy repeat each. All reuse the first processor. These are not crash trials and do not measure an RTO speedup.

| Parent phase | Min s | Median s | Max s |
|---|---:|---:|---:|
| trusted-render-library-imports | 11.452121 | 11.507222 | 11.595437 |
| first-render-processor-load | 0.954970 | 0.957940 | 0.964378 |
| render-assets-and-implementation-identity | 0.005892 | 0.005938 | 0.006246 |
| trusted-render-processor | 0.000085 | 0.000090 | 0.000092 |
| trusted-render-construction | 0.006011 | 0.006102 | 0.006288 |
| audio-assets-load-and-validate | 0.030462 | 0.031971 | 0.076357 |
| canonical-wal-replay | 0.014691 | 0.020560 | 0.035115 |
| input-wal-and-debt-reconstruction | 0.014530 | 0.018012 | 0.037799 |
| scheduler-and-input-debt-restoration | 0.038409 | 0.048367 | 0.067375 |

| Worker lane | Import median s | Model load median s | Warmup median s |
|---|---:|---:|---:|
| proposal_gpu0 | 11.454318 | 3.489631 | 1.037854 |
| authority_gpu1 | 11.354214 | 3.469471 | 0.899871 |

First worker spawn after owner entry: 12.820¨C12.951s. Both ready: 28.987¨C29.419s.
The two worker imports overlap one another, but both begin only after the parent completes its own ~11.5s import wave and ~0.96s processor load. Genesis WAL/input reconstruction is milliseconds. Processor reuse is implemented, but does not remove this serial import dependency.

## Dependency evidence

`qwen_asr/__init__.py` imports Qwen3ASRModel and Qwen3ForcedAligner before exporting parse_asr_output. The model module imports Torch/model/processor registrations and attempts the vLLM backend/ModelRegistry. utils.py imports librosa/numpy/soundfile even though the selected parser body needs only its language normalization, repetition fixer, two string constants, and typing annotations.
The actual tokenizer configuration declares Qwen2Tokenizer; Qwen3ASRProcessor wraps Qwen2TokenizerFast. The full processor source hash and exact native parser function source hash were checked against the measured render_contract. This observation supports a pinned tokenizer/parser extraction candidate, but no extracted renderer has yet been equivalence-tested or timed.

## Preferred first concrete patch: prevalidated descriptor + workers-first startup

1. Before the run, freeze a renderer identity descriptor from the trusted environment, including the exact existing render_contract, asset inventory, package versions, complete parser utility file, processor source and package initializer/entry module hashes. The attached QWEN_RENDER_DESCRIPTOR.json is a measured proposal input; its SHA must enter the run freeze and initialization provenance.
2. Before heavy imports, validate the descriptor hash, every declared asset/file/package version with the stdlib helper prefrozen_render_contract.py. This establishes identity only and grants no publication or state permission.
3. Construct identical semantic runtime/config dictionaries from the validated descriptor; initialize owned worker handles and spawn both cold workers now. Parent then performs its unchanged native qwen_asr imports and AutoProcessor load while workers independently load.
4. Recompute the actually loaded render_contract using native parser/processor objects; require exact equality with the descriptor. Any failure closes only the newly owned workers and fails closed.
5. Build the unchanged TrustedQwenRender, then recover canonical WAL, re-render each text, recover original input debt and apply through the real Consumer. Early mode may publish old facts when this complete trusted path is ready. New dispatch waits for actual ready receipts; original origin, epoch, obligations and WAL semantics stay intact.
6. Compare serial/reuse versus workers-first/reuse on both complete Standard and RevTrace, same source/descriptor/initial state, actual same fault point, full process-group cold restart, same cache condition. Give both methods the same optimization. Keep old fact, first new fact and precrash accepted-debt clocks separate.

This candidate can overlap the two measured import waves; it does not predict an exact RTO saving. Concurrent imports may contend for CPU/storage, and old-fact recovery still requires the parent renderer. Measure both paired outcomes. If old-fact latency remains dominated by parent import, only then implement a pinned minimal renderer with actual archived-token/WAL equivalence tests; never substitute cached rendered text/checksums.

## Minimal integration anchors

In run_tc_live_qwen.py, replace early native renderer construction around the original178¨C186 block with verify_prefrozen_renderer for the workers-first branch. Move native imports/first processor construction into a callable that returns the actual render contract and TrustedQwenRender. Place the existing worker spawn loop before invoking this callable for workers-first; serial invokes it first. Keep the comparison switch and descriptor hash in initialization.json/provenance, outside semantic contract fields, so startup ordering alone is the intervention. Wrap both paths in the existing owned-component cleanup try/finally.
The helper itself does not import qwen_asr or transformers. Any change to semantic render fields requires a newly frozen contract rather than a hidden loader-mode exemption.

Descriptor SHA256: `6098d9b6bade3d2f9784d0c0b9328b66accbb30e9f92d659884f351cacfdcdfa`. Actual profiles and hashes: STARTUP_PROFILE_AUDIT.json and raw/.

# Algorithm origin and differences (research notes, no manuscript edits)

1. Leviathan, Kalman and Matias. **Fast Inference from Transformers via Speculative
   Decoding**, ICML2023, PMLR202:19274–19286. Official published proceedings:
   https://proceedings.mlr.press/v202/leviathan23a.html
   Relevant idea: target verification of cheap proposals and continuation from
   accepted prefix. LP1 uses greedy current-input checking, not their general
   stochastic acceptance proof. This is standard algorithmic substrate, not a
   new RevTrace decoding contribution. Exact arithmetic reasoning does not prove
   all finite-precision execution layouts bit-identical.

2. Bernstein and Goodman. **Multiversion Concurrency Control—Theory and
   Algorithms**, ACM TODS8(4):465–483,1983. DOI10.1145/319996.319998.
   Publisher: https://dl.acm.org/doi/10.1145/319996.319998
   Author-paper copy: https://www.cs.cmu.edu/~15712/papers/bernstein83.pdf
   Prior multiversion storage/indexing is not our invention. The bounded new
   behavior tested here is querying already-computed provisional histories for
   current-root legal progress through the actual admission/view contract. An
   ordinary strong per-root index achieving the same result defeats a claim of
   exclusive new indexing/retention efficiency; it does not erase the native
   latest-only selector counterexample.

3. **VoiceAgent implementation inspection**, not a formally published result
   establishing exclusive novelty. Repository https://github.com/DingdongD/VoiceAgent
   commit8b5a0f9cc2f0cdaed692c876b4c682d54635dc0c. Native
   `transcribe_with_draft` recomputes full current audio, verifies a draft, crops
   new KV at first mismatch, appends target bonus and decodes residual. The
   execution host lacks its mandatory FlashAttention path. Our independent
   HF/eager adaptation is explicitly credited; no unchanged-engine reproduction
   or native performance comparison is claimed. No root license was observed;
   inspected upstream code is NOT redistributed in the evidence package.

4. Actual installed Transformers4.57.6 **implementation/contract**, not a paper:
   DynamicCache.crop, generation cache-position/masks, Qwen ASR prepare-inputs and
   effective logits processors were inspected on the execution environment.
   Official explanations: https://huggingface.co/docs/transformers/v4.57.0/kv_cache
   and https://huggingface.co/docs/transformers/v4.57.0/en/cache_explanation .
   An HTTP read of internal generation docs failed; the source-level audit and
   actual configured processor, not a guessed documentation statement, determine
   M v2 verification. Preserve installed source/API identities.

Search note: primary proceedings/publisher and exact code inspection were used;
academic MCP unavailable, OpenAlex/GitHub API rate limits were not bypassed.
Preprints were not treated as vetoes; unsupported exclusive claims were rejected
by our own strong controls. No paper bibliography has been modified.

# StreamCorrect full-text verification

Review date: 2026-10-28. This note reports the paper's mechanisms and published results, followed by our comparison interpretation. It includes no new inference, reproduction, or service measurement.

## Acquisition and identity

- Official lawful OA source: [ACL publisher PDF](https://aclanthology.org/2026.emnlp-industry.142.pdf), linked by the [publisher record](https://aclanthology.org/2026.emnlp-industry.142/).
- Local file: `Vu_2026_EMNLP_StreamCorrect.pdf`, 3,284,475 bytes, 13 pages; `%PDF` header, nonzero page count, title, authors, and venue verified. SHA-256: `db5f0153ec0718a424a51d17c4a7c8c75c6e0ba33bb383a78f5f58c9008a7cae`.
- Two extracted text files and hashes are recorded in `MANIFEST.json`. The `reading_order` file preserves the paper's column order more usefully than coordinate-sorted text. `page03_mechanism.png` was rendered and visually inspected for Fig. 1 and §3.1.
- Initial ordinary shell network access failed with Windows socket error 10013. A normal local-network escalation then returned HTTP 200 `application/pdf` from the same ACL URL. No login, entitlement change, mirror, CAPTCHA, or access-control bypass was involved. Both attempts are retained.
- Camera-ready identity: Tung D. Vu, Zeying Xie, Weiwei Zhao, Victor Junqiu Wei, Di Jiang, Yi R. Fung; *StreamCorrect: Self-Supervised Error Correction for Real-Time ASR with Offline Recognizers*, EMNLP 2026 Industry Track, pp. 2391–2403. Page 2391 explicitly links `vu-duy-tung/StreamCorrect`. This establishes repository association, not a frozen execution-commit identity.

## Mechanism actually defined in the paper

Fig. 1 and §3.1 (PDF p. 3 / printed p. 2393) define one sequential selected-prefix loop. In our compact notation:

`candidates_c = ASR(confirmed_prefix_before_c, observed_audio_through_c)`

`selected_c = corrector(confirmed_prefix_before_c, candidates_c, observed_audio_through_c)`

`confirmed_prefix_after_c = confirmed_prefix_before_c + selected_c`

The updated prefix conditions subsequent chunks. §3.2's inference paragraph (PDF p. 5 / p. 2395) places correction immediately after ASR. Appendix A (PDF p. 11 / p. 2401) asks the model for the continuation to append after the confirmed transcript. This explicitly establishes feedback selection and coordination; it should be credited as such.

PRA (§3.2, PDF p. 4 / p. 2394) aligns the previously confirmed prefix to an utterance-level reference to create chunk-level training targets. It minimizes edit distance over possible reference endpoints and resolves tied endpoints conservatively. The reference is training supervision. Determinism of this alignment procedure does not certify a live model's output, KV state, or equivalence to an independent authoritative execution.

## State and lifetime comparison

| Question | What the paper establishes | Consequence for a fair RevTrace comparison |
|---|---|---|
| Provisional display | The specified output is the corrected segment appended to the confirmed prefix. Current top-k alternatives are inputs to selection, not a separately specified consumer authority. | Do not call streaming presentation or choosing among provisional candidates new. Demonstrate the distinct exposed private view and its legal relationship to trusted feedback. |
| Selected feedback | The corrector's selected segment updates the next ASR context. | Same model family plus correction feedback is substantial overlap. Keep the complete selected-feedback stream identical across arms; otherwise accuracy changes can confound scheduling value. |
| Authoritative state | The mathematical state is the cumulative confirmed transcript, with previous emissions treated as committed. | RevTrace's independent Canonical F/Z/P/text-history equality is an additional contract. A learned argmax correction is not automatically its certificate. |
| Cross-root overlap and retention | The defined recurrence goes from a completed selection to the next chunk. It does not specify multiple live private branches admitted against independently installed trusted roots. | The discriminating test is compatible computation **and actual visible progress** surviving a root advance, alongside withdrawal of incompatible progress. This is a concrete composition obligation, not a generic claim that ASR state reuse is novel. |
| Asynchronous late results | Neither the recurrence nor the described evaluation assigns authority to out-of-order old-root completions. Call-level concurrent replicas are described separately in §4.5. | Test stale arrivals with an explicit ownership/authority contract. Do not infer an old-root reconciliation scheme merely from multiworker concurrency or an `_async` filename. |
| Execution retirement | §4.5 caps correction at 8 new tokens per 500ms step; replicas process different calls. | A preset generation bound is a legitimate strong baseline, but it does not establish installed-coverage-triggered cancellation, safe-point acknowledgement, batch drain, or physical lease reuse. Show those events and useful successor progress. |
| Input and recovery obligations | The reviewed problem, methods, and evaluation do not define accepted-input WAL durability or replay after worker failure. | A service claiming these properties must separately account for accepted audio and restoration. Their absence from this paper's scope does not negate its recognition contribution. |

These distinctions describe the reviewed paper's specified/evaluated system. They do not prove that every implementation or deployment lacks additional facilities.

## Positive results and evaluation limits

The following are **author-reported external results**, not RevTrace measurements. At 500ms chunks and beam size 4 (Table 2, PDF p. 6 / p. 2396):

| Dataset | SimulStreaming CER | StreamCorrect CER |
|---|---:|---:|
| AIShell-1 Mandarin | 16.3% | 9.8% |
| Industrial Mandarin | 27.8% | 20.7% |
| WSYue Cantonese | 15.6% | 10.2% |

The AIShell-1 row reports FTL 158→219ms and LTL 213→295ms. §4.1 defines FTL from audio reception to first emission and LTL from audio-stream end to finalization, with H20 hardware. These are useful recognition and endpoint-latency results. They are not a measurement of our unchanged-Canonical service objective.

Evaluation interpretation:

- Appendix C and Table 4 (PDF pp. 11–12 / pp. 2401–2402) describe five repeated runs on one H20 without other sharing processes; Table 4 explicitly labels its results **computationally unaware**. The paper's stable repeated latencies therefore do not establish robustness to interference or online resource-lifetime benefits. Keep this timing mode visible when citing its numbers; do not silently treat it as an end-to-end concurrent-service benchmark.
- §4.5 describes industrial deployment across GPUs and estimates model-weight storage per replica. It does not report a controlled throughput, queueing-delay, co-tenant stall, cancellation-latency, or physical-lease experiment. Credit the described integration without inventing such performance evidence.
- Fig. 4 / §4.4 (PDF p. 7 / p. 2397) measures error propagation, excluding utterances shorter than four seconds. Appendix B / Table 9 provide a qualitative sequence showing prefix-induced downstream differences. This supports why feedback matters; it is not evidence of compatibility between branches with different full feedback states.
- Appendix G / Table 8 (PDF p. 12 / p. 2402) compares Qwen3-ASR configurations that delay first decoding differently. It is a comparison against Qwen3-ASR streaming, not proof that the separate public Qwen3ASR correction repository is the exact measured camera-ready implementation. Do not merge those identities.

## Revised opportunity assessment

The full text strengthens StreamCorrect as a positive neighbor. Its application of modular correction to offline-based streaming recognizers, and its training/inference integration, are meaningful even though correction, top-k selection, and prefix conditioning have antecedents. The same standard should be applied to RevTrace's application/composition contribution.

The competitive question is whether RevTrace can preserve that selected-feedback service exactly while allowing private computation and the Consumer to advance independently. A particularly informative adaptation would treat the complete corrected feedback selections as fixed Canonical events in every arm, then compare retain/drop × one-lane/two-lane and full Standard with identical resources and input obligations. A compatible branch should deliver useful visible work after a root advance; an incompatible branch should be withdrawn; a provably covered target should stop and free the actual executor. This is an experiment proposal, not evidence that the proposed adaptation already succeeds.

Equal behavior from full author-built Standard is a constructive positive result for the complete composition. Equal retirement benefit from watchdog/parent cancellation should also remain in the results. The research claim can rest on the supported contract, coordination difficulty, non-additive visible-progress interaction, and measured service opportunity without claiming unique superiority of every control predicate.

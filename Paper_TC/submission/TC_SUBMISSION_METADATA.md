# IEEE Transactions on Computers submission metadata

This file mirrors the current `Paper_TC/main.tex`. Update both places together
if the title, abstract, author order, or keywords change.

## Article type

Regular Paper

## Title

RevTrace: A Transactional Runtime for Feedback-State Integrity in
Revision-Generative ASR Serving

## Abstract (182 words)

Revision-generative automatic speech recognition (ASR) pipelines feed model
outputs back into later execution state. Under batched accelerator execution,
a local numerical difference can therefore become persistent state
contamination. We formalize this failure mode and introduce Dual-Granularity
Feedback Transactions (DGFT), a runtime protocol that separates low-latency
proposal and display from canonical state-write authority. Each accepted
projection is bound to a certificate, parent version, input frontier, and
runtime configuration; same-granularity certification is the rho=1 case.
RevTrace implements DGFT as a two-plane parallel runtime with independently
replicated proposers and authorities. Across Qwen3-ASR and Whisper on two RTX
3090 GPUs, coarse authority improves matched-workload throughput by
1.39×/1.28× and reaches up to 6.88× wall-clock speedup over per-path
all-singleton references, with no observed installation violation in 800 Qwen
events and 1,048 Whisper commits. A 250,000-attempt protocol fuzzer rejects
every mutation and replay. On eight V100 GPUs, balanced replication sustains
157.8×/111.7× audio real-time throughput at the largest measured concurrency
satisfying the 2-s display service-level objective (SLO). These results
establish state-write authorization as a distinct runtime contract for
feedback-driven ASR serving.

## Index terms / keywords

1. Runtime systems
2. Generative model serving
3. Streaming ASR
4. State certification
5. Transactional consistency

## Authors (publication order)

1. **Bin Zhou** — `2025200800@buct.edu.cn`
2. **Jiyuan Miao** — `2024200822@buct.edu.cn`
3. **Xi Cao** — `caoxi@buct.edu.cn` — corresponding author

## Affiliation

All authors: Beijing University of Chemical Technology, Beijing, China.

## Artifact availability

A reviewer-facing artifact ZIP accompanies the submission and contains source
code, frozen audited result records, validation scripts, raw microbenchmark
samples, and a SHA-256 manifest. The repository currently requires
authentication; the manuscript therefore promises a public archive only upon
acceptance. Third-party benchmark data remain subject to their original
licenses and are not redistributed.

## Acknowledgment and declarations

- Computing support: High Performance Computing Platform of BUCT (Beijing
  University of Chemical Technology).
- Funding: no grant or external funding source is currently declared.
- Competing interests: none currently declared.
- AI assistance: OpenAI ChatGPT was used solely for language polishing and
  writing assistance; all text was reviewed and edited by the authors.

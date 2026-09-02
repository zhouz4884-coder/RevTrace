# TC initial-submission experiment decision

Decision: **no new experiment is required before the first IEEE Transactions
on Computers submission**.

The existing frozen evidence already closes the claims that the TC manuscript
is allowed to make:

| Claim | Existing evidence | Boundary |
|---|---|---|
| Feedback turns a local execution difference into persistent state divergence | 21 legal paired interventions; 8 propagate with feedback, 0 without; measured tail RAF 153 | Causal characterization in the evaluated ASR feedback loop |
| DGFT enforces state-write integrity | 800 Qwen events, 1,048 Whisper commits, and a 250,000-attempt protocol fuzzer | Accepted-history integrity under the declared trust and binding assumptions |
| Coarse authority can outperform same-granularity authority | Matched c16 ladder: 1.39x/1.28x throughput improvement | Frozen Qwen contracts; not a universal precision claim |
| The runtime has useful production operating points | Up to 6.88x wall-clock speedup; all 16 Whisper cells pass their contracts | Per-family contracts; quality estimands are not pooled |
| The two-plane design scales on accelerators | Independent 8xV100 replica experiment; c64 capacity and c128 failed boundary | Single-node replica scaling, not multi-node or datacenter deployment |

New experiments should be opened only if the TC rewrite exposes a claim not
covered above. In particular, the paper must not add claims of non-ASR model
generality, multi-node scalability, new accelerator architecture, or kernel
innovation without new evidence.

Standard-data evidence is already present: deterministic 64-utterance
LibriSpeech test-clean and AISHELL-1 holdouts report WER/CER and terminal
exactness. The TC manuscript should name these datasets explicitly rather than
imply a full-corpus evaluation.

# Native Whisper capacity failure and conventional control

The unchanged v8 paid probe failed after eight completed calls. Its ninth
invocation had 196 initial decoder tokens plus a fixed 256-token generation
budget, exceeding the checkpoint's 448 positions. This is a real invocation
failure, not an admission rejection or a reproduction of the old FP16/margin
R7 anomaly. Earlier exact GPU cells did not cover this long conditioning path.

`get_prompt_ids` in the pinned Transformers 4.57.6 tokenizer does not truncate
this prompt. In this short-form generate path, the external prompt is appended
without the internal long-form `cut_off_length` guard. The early capacity check
raises before the later adjustment branch can run.

The opt-in `reserve-generation-tail-v1` control keeps the previous-text marker
and the most recent 189 history tokens, reserving 256 new positions and two
checked English/no-timestamps initial tokens. Canonical history is not shortened;
only the deterministic model conditioning view is bounded. The policy, capacity,
prefix IDs, implementation/source and model assets are part of the frozen
execution contract. Changing the policy requires a new contract and run.

This is a conventional bounded-context engineering repair, already within the
R8 class of alternatives; it is not claimed as new VACC, R9, or a recovery
algorithm. It is shared with Standard. Full actual decoder input, complete Z,
EOS/budget, P, trusted text and full prefix-acquisition costs remain audited.
No measured success is asserted until same-input repeated GPU calls and an
independent audit complete. The unbounded failure remains retained.

# Fixed encoder component probe

The actual execution source is this clean generator commit plus the separately
verified and imported bdfa3b1307d267a5a4caf6484e1ad465c39a592e native runtime.
The runtime stays byte-identical. It is instrumented by this generator's temporary
encoder forwarding hook, whose source and identity are independently recorded.
Keeping the underlying runtime's feedback contract tag is not labelling this
generator as that old runtime commit.

Exactly four fixed source0 wrong-start/fallback pairs are tested. Each pair has
one original infer stopped immediately after synchronized original E completion,
one correct-input original full infer, and one correct-input original full infer
whose encoder returns the protected received E only after actual mel/static
identity validation. One fixed original-full EOS repeat completes thirteen calls.
Wrong-branch E-only calls produce no D/C/U result or Canonical state.

Both full model workers use the original FP32 code, old source0 fixed1.5->2s
learned-C warmup, discarded output and reset. Current inputs use complete frozen
cuts. The original current-input D/C/U and cleanup are unchanged. Actual mel/E
bits, entire selected C, returned IDs and closed cut are compared; no decoder KV
or incorrect feedback is transferred. Execution provenance, owned worker/job,
original birth and real parent receipt are recorded independently of key hashes.

E return is explicitly CUDA-synchronized: Python forward return is not GPU
completion. Every real copy, binary pack/hash, Queue hop, complete receipt,
decode/verify and H2D completion is timed. Mel/feature hash instrumentation costs
are separate. Production economics nevertheless charges the full pre-E guard
and full post-E tail through sent timestamp, including wire SHA, finite checks
and E-only cleanup, not merely the narrower clone/pack sub-timers. Consumption
charges actual full mel guard plus decode/import/finite checks and second hop.

The received E SHA is a verified-wire digest; no independent receiving GPU E
readback is performed. Actual wrong/baseline original GPU features are both read
back and hashed. Received semantics use the entire real C/IDs/closed-cut oracle.

This is a component/oracle probe, not a deployed cache/service run.
It does not measure natural encoder-ready prevalence. Reusing a feature in this
probe cannot establish arbitrary-input cross-GPU bitwise equality.

The fixed observed4/14 use rate comes from all14 speculative source0 dispatches,
not only the four invalid ones. Four measured payload routes estimate fourteen
potential eager captures/exports; four actual imports are counted. This expected
resource calculation is explicitly a component model. Positive margin of >=100ms
and exact oracles only permit root review of a possible implementation; negative
margin or fidelity failure selects the already-tested complete-call method.

No live cache is implemented. Any future E-boundary cancellation permission must
also be granted to the no-reuse fullspec control, and all original offered/EOS,
Canonical and Consumer definitions must remain equal.

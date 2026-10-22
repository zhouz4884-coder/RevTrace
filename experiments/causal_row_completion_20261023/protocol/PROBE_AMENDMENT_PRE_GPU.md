# P1 measurement amendment before any GPU probe outcome

Keep the12 operations already frozen in p0_v1/GPU_PROBE_PLAN.json. Each receives
two reference/probe/reference cycles (72 invocations), plus one reference/probe
pair with actual post-cast GPU input hashing (24 identity-control invocations).
The total maximum is96 diagnostic batch invocations, not96 serving cells.
The extra identity-copy calls are explicitly excluded from overhead estimates;
their outputs and moved-tensor identities must agree. Timed ABA invocations keep
the original input capture only and compare all original processor identities.

The observer uses the installed GenerationMixin stream callback; it never changes
input rows, masks, features, budget, logits, stop tokens or selected outputs.
It does perform CPU copies/complete rendering and therefore can perturb execution.
That work is billed by the measured invocations, not assumed free. Whole-batch
results still return through the original worker; no Row-complete installation
or earlier service result is claimed at P1. Every complete-row timestamp records
its actual CPU rendering, not just EOS. Verified-success rows are rendered during
their actual gate check before peer fallback; this is extra probe work, not a
retroactive historical clock.

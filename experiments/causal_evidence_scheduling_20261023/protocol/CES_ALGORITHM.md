# CES: choose the evidence work, never the accepted-state predicate

The execution target is a released session/frontier transition under its actual
current Canonical Parent and fixed input/runtime contract. A completed private
candidate is optional. G computes independent complete FP32 output. V computes
strict full-token/stop/budget FP32 correct-context evidence, followed by actual
paid FP32 generation when it fails. A batch contains only one operation. Row
completion and full physical drain are different events in planning and billing.

## Bounded receding-horizon rule

At an idle GPU1 lease, consider at most16 currently legal transitions, ordered
by declared commit deadline. Rank actual ready candidates by historical
rejection estimate, then deadline and session ID. Enumerate each ranked-prefix
verification set, its complementary generation set, and both execution orders.
There are at most32 nonempty orderings, not an exponential search or an optimum
claim. Issue only the first homogeneous batch, observe real results, then plan
again after physical drain. A bounded wait may use only an already dispatched
candidate; cumulative waiting per target cannot exceed0.15s or waive a deadline.

Physical occupancy prices verification and a possible separate fallback. The
probability-of-any-rejection estimate is a heuristic, not independence guaranteed
by the system. Accepted rows' expected delivery is at the verification boundary;
failed rows include fallback. Independent generation also gets the measured
row-completion fraction, rather than being unfairly modeled as batch-final only.

The score combines expected physical work,4×commit tardiness beyond8s, visible
tardiness beyond2s, and0.25×potential descendant waste. Coefficients are fixed
before validation, not fitted to produce a desired Goodput result. Potential
descendant survival uses a deterministic target render of an *already generated*
candidate only as a conditional compatibility prediction. No CPU reconstruction
is represented as new-parent generation. Acceptance is never sufficient for
Exact-P equality; both G and V may select the same or different legal histories.

## Calibration and controls

Historical development sources only: 72+120 histories supply5,868 strict-row
rejection samples; the120 row-runtime histories supply synchronized physical
phase costs. Independent30 validation histories are excluded from parameter
fitting. Repeated state contexts are not independent prevalence samples.

Costs condition on row count, released audio extent, new interval length and
declared parent length; V may additionally use known candidate length. Future
generation length and fault labels are forbidden inputs. Fixed robust-ridge
fits and training-only prediction bounds reduce the row-count/audio-length
confounding found in pooled curves. Held-cell errors are reported, not hidden.
Cost-only receives the same contextual costs and row executor as CES.

- Fine and complete Standard Safe Async issue direct work without running the
  CES predictor; they are not burdened with unused rendering/planning loops.
- Always Strict waits for real candidates and pays every failed fallback.
- Readiness/Birth uses simple observed same-birth gating.
- Cost-gate preserves the simple global expected-cost threshold.
- Cost-only uses the identical joint batch/order/deadline planner with global
  rejection and no causal preservation risk; it is not deliberately myopic.
- Causal-only retains the same full score on one target, including causal
  render, deadlines and bounded wait, then groups homogeneous rowwise choices;
  it removes cross-request joint optimization, not all advanced features.
- Full CES jointly plans batch/order, deadlines and causal descendant risk.
- Readiness-only verifies any ready candidate under the correct target; it
  supplements the stricter birth gate so the latter is not a strawman.

All predictions may be wrong. Every actual result still passes original D1,
Parent/Frontier/Contract/A/B/C/D and WAL. Every physical phase is charged.
Full CES must beat the strong simple rules on independent actual loads before
the joint causal scheduling rule can be called an independent C2 contribution.

# Fixed final independent analysis, no model/runtime imports

This source reuses the old four-source development confirmation's independent
primary/mechanism driver (4088f34f...) and its sixteen-cell text wrapper
(57803f3b...). The per-cell analyze_pilot_content.py, native_content_endpoint.py
and test_pilot_content.py remain byte-identical to c12803e3ab411ad7898a34a2e257fdee313df81c.
Their pilot CLI is not called; only the frozen analyze/whole-text definitions.

The final data are four different acoustic sources/speakers, with two fresh
process repeats per method, eight within-source/timing pairs and sixteen cells.
All68 original reference steps and272 timed Canonical steps must be present.
Same bdfa original-full reference and service require whole start/end state,
including stage_execution, to match exactly. No old99 tag projection is allowed.
Full original C/IDs, complete source objects, input/Consumer hashes, EOS, missing
observations and original linear P99 definitions remain in the independent audit.

Primary credit is computed in integer offered samples first. The pre-NN
appraisal is directional only: total sample difference>0 and at least3/4 speakers
have positive two-repeat sums. Neither eight pairs nor repeated frontiers become
eight independent acoustic samples. All paired gains/losses/ties and whole-run
failures are reported. Per-source quality is independently recalculated using
Unicode whitespace only; acoustic text quality is also reported once per source.

Content is a separate retrospective whole-text match at the actual first-view
frontierG; G>F is never truncated or replaced with offeredF reference text.
Raw/whitespace supported, mismatching and unknown observations/credits remain
distinct. Original D2/C8 is never replaced with text support or energy.
The original per-cell functions require eventual actual visibility/coverage;
primary audit independently retains infinity/missing cases. A content assertion
failure is preserved as analysis failure and cannot remove that source/point
from the primary population.

No new model calls, network, remote operations, source selection or source edits
are performed by this analysis. Configs may only bind actual complete sixteen-cell
collection hashes and the already-frozen reference/metadata/method/appraisal.
The template is deliberately non-executable before those inputs exist. The global
CURRENT launch pointer belongs to root's neural scheduler and is not changed.

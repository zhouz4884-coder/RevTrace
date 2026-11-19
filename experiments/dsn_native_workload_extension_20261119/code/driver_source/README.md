# Original MAGICDATA68 workload extension driver

Code preparation only. No new reference, service run or manuscript change is
implied by this source. Immediate parent is the frozen 22-file campaign driver
1bd3b01265a57d844c192e88573dc2a13860f64f; that package and the completed
80-cell experiment remain unchanged. Git retains inherited legacy helpers and
controls; the new workload uses the entry points below.

Actual neural runtime remains original complete FP32 two-worker source
11453433c154aeffbff703c4c8dc9697421430e1 (67 files). Production support remains
a13fa0a335529dc188f7e738877a3acd027ce4a7; independent Consumer audit remains
0571d51d85542e1eaf000be8082585a66e5978be. A fresh original continuous/restore
reference is required for every selected original MD68 audio file. No old
AISHELL reference, derived PCM, stage forecast or simulator supplies that gate.

corpus_contract.py verifies the official complete test archive hash, full
header census, frozen metadata-only IDs, selected official TRANS rows and
member hashes, exact extracted original WAV and PCM hashes, and headers.
The choice is the first four eligible speakers in lexicographic order, each
speaker's complete 12--20-s utterance nearest 16 s, breaking ties by original
ID. Transcript values are accessed only after the ID-freeze hash is bound.
Actual eligible shortfalls remain N; zero is NO-GO. No trimming, concatenation,
resampling, outcome-based selection, or bypass of corpus membership is supported.

Ordered Root workflow after source identity, byte and environment verification:

1. Obtain a terminal receipt from the separately frozen metadata preparer.
2. Run make_reference_plan.py, then existing make_prelaunch.py and
   run_reference.py. Preparation and execution recheck the new corpus contract.
   Original warmup, backend, FP32, seed, continuous original path and two
   restored controls per edge are retained. Reference generation is separate
   paid work, not service evidence.
3. After reference PASS, run make_workload_plan.py with explicit driver,
   runtime, support and view-audit manifests, template, environment, selection
   and reference receipts, 8TB config/raw locations and output plan.
4. Bind that plan with make_prelaunch.py using actual CURRENT/runtime and
   explicit driver preflight receipts and Root's exclusive GPU-window identity.
5. Root runs run_workload_campaign.py for exactly 6*N fresh cells: serial
   conservative_s1, r1s0, and r1s1, each twice per source. Each source's seeded
   policy order is reversed on repeat 1 and primary GPU rotates 0 to 1.

The service runner retains the parent controller's original-task/reference,
actual FP32 READY workers, sampled owned-power window, physical cleanup,
disjoint job/worker-time accounting and independent actual-Consumer checks.
It retains 500-ms inputs, partial EOS, D2=2 s, C8=8 s and 2-s ahead bound.
Original warmup and full test source objects are checked in every config.
All offered input, SLO misses, zero opportunities, ties and reversed effects
remain in the planned denominator; technical failures preserve the attempted
prefix rather than trigger a favorable rerun.

Aggregation reports only observed three-policy comparisons. There are no R0
cells, missing-arm imputation or factorial interaction. Total high-water gap
and classified same-root gap remain distinct, with necessary/unknown loss and
right-censored/boundary-truncated windows retained. S does not need to improve
first credit for its supported-view continuity effect to be meaningful.

CPU controls: from this clean checkout, add the explicit frozen NN1145 runtime
test path and run python -B -m unittest discover. The cross-source command
python -B workload_interop_controls.py --prep-source ... --prep-manifest ...
also verifies actual preparer identity and runs a complete synthetic
archive/census/IDs/selected-labels-WAV/strict-corpus/reference-source/config
chain, with an actual three-speaker shortfall and an unselected invalid-UTF8
value that must never be decoded. These are CPU fixtures, not corpus service
measurements. Preparer version used by that control:
dc43456e52568f3b2b5fa6a669a67586c3c91d92.

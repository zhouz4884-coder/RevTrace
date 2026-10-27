# Native neural lifecycle: actual consumption is not task success

All 60 offered cycles in 20 clean cells are retained. Two task families:
ordered dependency/runbook repair and capacity-constrained resource selection.
Fixed LangGraph1.0.3/checkpoint-sqlite3.0.0, independent durable store,
checkpoint/resume in new processes, actual neural requests and later writes.
`NATIVE_INPUT_GENERATION_WRITEBACK.csv` and full JSON under
`records_v2/native_v2/` expose every prior value, actual input digest, generated
value, complete Stop, independent task score, receipt and subsequent consumption.

|Study / model|Offered cycles|Writes|Unfulfilled|Actual later-input edges|Unauthorized prior consumed|Objective successes|
|---|---:|---:|---:|---:|---:|---:|
|Original Qwen2.5-1.5B, FP16P / FP32A|30|24|6|16|0|0|
|Stronger Qwen3-4B, BF16P / FP32A|30|30|0|20|4|0|

Each study contains Candidate-only, Standard Direct, RevTrace Direct,
Standard Strict and RevTrace Strict in both families, three offered cycles per
cell. For protected arms each model study has24writes and16actual later-input
edges. Candidate-only original requests are unfulfilled: a budget/non-EOS
output must not be invented as an earlier installed value. Stronger-model
candidate-only has6unauthorized writes and4later inputs, all explicitly charged
to the negative control rather than to the protected contract.

## Concrete recorded values and future input

In the stronger-model runbook negative control, cycle0 writes
`{"completed": [], "last_action": "probe"}`. Cycle1 actually reads that value
in the model request and returns `{"completed": ["probe"], "last_action": "probe"}`;
cycle2 actually consumes the latter value. Both prior histories fail the
declared dependency/task consistency judgment. These are real model/store
edges, not CPU substitutions, a natural fault-frequency estimate, or an attack.

In the stronger resource negative control, cycle0 writes
`{"reserved": ["gamma"], "remaining": 9}`; cycle1 actually reads it and writes
`{"reserved": ["gamma", "delta"], "remaining": 1}`. Cycle2 reads that value
and returns `{"reserved": ["beta"], "remaining": 9}`. Frozen sources and
requests, rather than a plausible-sounding narrative, determine the capacity
and local-objective failures. Valid provenance would not certify these truths.

## What survives a strong reference

Present-output validity is0/3 for all runbook arms in the stronger study,0/3
for its resource Candidate-only, and1/3 for each protected resource arm.
Every study/arm has0/3 locally objective-optimal steps in each family.
The full Standard reference is not handicapped and the RevTrace protected
counterparts match it. Four incorrect prior consumptions are observed in the
negative control, but **no successful Standard task trajectory is lost by that
control**, because none of these references succeeds. Consequently this study
does not establish a task-quality protection gain or an irreversible harm.

Of36actual later-input edges across both model studies,32consume task-invalid
prior memory, including authorized base-model errors. This is the concrete
boundary between provenance and semantic truth, not an excuse to drop failed
requests or silently repair the task schema. Logical request/source matching
does not hold precision and verification layout fixed across every method;
arm differences cannot be assigned solely to feedback.

The retained precision diagnosis found four FP16first-forward all-NaN vectors
and eight FP32/BF16finite vectors in12paid rows. The stronger model repairs
execution feasibility, not objective task performance. A separate eight-call
first-step schema-clarity operator helps runbook but not resource; it has no
installation or multi-cycle claim. The larger task-harm matrix therefore
remains NO-GO. This package does not reopen it or present clean failures as
measured protection.

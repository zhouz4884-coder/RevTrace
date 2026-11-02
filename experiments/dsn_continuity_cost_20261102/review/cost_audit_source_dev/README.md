# Independent current-cost audit — NOT RUN

Prepared locally while the NN campaign is exclusive. No source in this folder
has been run by its author. Root must copy/freeze a complete clean checkout,
create the full source manifest, run the 17 controls, then register and execute
the audit after the exclusive window closes. Set TMPDIR to an owned 8 TB scratch
for controls and CUDA_VISIBLE_DEVICES='' for all audit execution.

Only Python standard library and the sibling `cost_forest.py` are imported.
Neither the primary summarize_spans nor the campaign driver/runtime/model is
imported. Frozen roles: observer C3cf7cd10..., driver Db1648198..., original
NN4f4c3ca... . Original source, observer and driver roles remain distinct from
this independently frozen analysis commit.

```
CUDA_VISIBLE_DEVICES='' python -B cost_recount.py --phase both \
  --plan <frozen cost/plan_v1/PLAN.json> \
  --cpu-campaign <original completed CPU12 driver output> \
  --nn-campaign <original completed NN16 driver output> \
  --source-commit <new full independent commit> \
  --source-manifest <new complete independent manifest> \
  --out <fresh 8TB independent audit directory>
```

`--phase cpu` or `--phase nn` permits separately completed phases; an incomplete
or live selected campaign fails. `--path-map OLD NEW` maps a complete bounded
mirror while retaining original input identities. It never opens model weights
or changes old raw, CLOCK, fact or observer files.

The audit independently:

* validates the span forest by role/PID/thread/ID, parent containment, no cycles,
  disjoint siblings, and recalculated exclusive wall/thread CPU;
* preserves signed wall-minus-CPU and CPU>wall counts caused by asymmetric
  clock brackets; these are not illegal negative blocking or lock estimates;
* uses strict whole-span containment for original SERVICE_END, actual Consumer
  certified EOS, and external confirmed physical model drain windows; boundary
  CPU is not prorated; parallel role wall is not added;
* checks Owner/Supervisor export scope, raw family counts, genesis versus new
  durable facts, actual publications/Consumer counts and actual fsync evidence;
* parses original RVN1 bytes/checksum/chain itself; binds complete selected
  input/output/C/IDs to the original reference with only the declared static
  source-marker mapping; recomputes final whitespace-only CER;
* recomputes all-offered 500ms and partial-EOS D2/C8, both original common
  energy endpoints from raw two-board power, and 8 unique off/on pairs.

CPU trace objects, independent full-input/binding probes and actual NN spans
remain separate. The result is an operation footprint and total observation
effect, not a counterfactual protocol-removal or pure safety tax. Null-timer
calibration belongs to its separately frozen experiment and is not subtracted
from spans. Full original-call/whole-view c4 trace checking remains a separate
Root responsibility; this audit does not claim Python/CUDA refinement.

If frozen, stop editing this folder; use a new source_v2 for any change.

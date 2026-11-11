# Prepared offline analysis source; no execution yet

Prepared 2026-11-11. This source was authored after the evidence-first review.
No tests, metadata recounter, source freeze, formal CPU run, or GPU launch were
performed by its author. Root must independently review, freeze and record the
actual execution commit, full manifest/config/environment, designated8TB raw
path, summary and gate before any formal execution.

`content_edit.py` is a pure Unicode code-point minimum-edit/lifetime reader.
`run_content_edit.py` is a formal gated entry. It reads existing actual Consumer
logs with `observed`, `source_id`, `text`, optional `kind`; NN4f native, old14 and
core logs share this schema. No runtime instrumentation or callback is needed.
It records raw and Unicode-whitespace-stripped views separately. It starts each
source from empty text and includes the first actual snapshot. Survivors are
right-censored at the last actual same-source observation.

Three independent identity conventions are emitted:

- Minimum edit, priority MATCH/SUBSTITUTE/DELETE/INSERT.
- Minimum edit sensitivity, priority DELETE/INSERT/MATCH/SUBSTITUTE, propagated
  through the complete history, not restarted from the primary identities.
- LCP suffix identity, separately named and counted. It can close an unchanged
  shifted suffix and must never be called a true edit deletion.

Each minimum-edit event also reports exact all-optimal additive I/D/S,
retraction and age-threshold bounds, conditional on that convention's previous
identity history. Those local bounds do not cover every globally possible
identity history. The two complete histories are sensitivity analyses, not
statistical confidence intervals or semantic character identity. Every event
keeps literal before/after text and edit operations; every retracted unit keeps
its birth/closing row and actual observed lifetime. Surviving units also appear
in the lifetime ledger. Support invalidation without textual change requires a
separate full-state support ledger; this reader does not infer it from text.

Mandatory invariants: `I-D == final_visible_code_points` and
`I+D+S == total_minimum_edit_distance`. This catches the external pasted
Sequential179-vs-official184 mismatch if both claim the same complete raw scope.
Do not use old14 numbers to numerically replace the unrelated H3 headline569.

`test_content_edit.py` contains12 prepared controls, unexecuted: inserted middle
character closes no real edit identity; actual substitution closes the old
unit; Unicode supplementary code points; ambiguous repeated-character bounds;
first snapshot inclusion; last-observation censoring; source-local clocks;
backward time; inclusive2s; raw/whitespace separation; LCP-age versus edit-age;
and961 short-string pairs checked against an independent rolling-row distance.
`test_pair_statistics.py` adds4 exact-sign/eight-speaker controls. The formal
entry runs all16 after its full prelaunch record and before reading raw data.
Run only after freezing, using `python -B -m unittest -v test_content_edit`.

The root creates a new config, not a relabelled old run. Schema:

```json
{
  "experiment_id": "NEW-EXPERIMENT-ID",
  "designated_experiment_disk_prefix": "/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9",
  "age_threshold_seconds": 2.0,
  "expected_controls": 16,
  "cells": [{
    "cell_id": "original-actual-cell-ID",
    "bank": "native_old14",
    "schema": "native",
    "stage": "formal",
    "arm": "original-arm",
    "cohort": "A",
    "repeat": 0,
    "consumer_path": "/media/user/.../consumer.jsonl",
    "consumer_sha256": "ACTUAL-FROZEN-SHA256"
  }],
  "metadata_inputs": {"h3_runs":{"path":"/media/user/...","sha256":"FROZEN"},
    "h3_sources":{"path":"/media/user/...","sha256":"FROZEN"},
    "h3_opportunities":{"path":"/media/user/...","sha256":"FROZEN"},
    "old14_lcp_runs":{"path":"/media/user/...","sha256":"FROZEN"},
    "new8_report":{"path":"/media/user/...","sha256":"FROZEN"}}
}
```

For old14 derive actual paths/hashes and original `stage`/`arm`/`cohort`/`repeat`
from `experiments/dsn_native_content_20261029/CONFIG_v1.json`. Its14 cells are
2witness and12formal; retain all14 and never pool these stages. Original official
raw LCP controls: formal Sequential184/0/184, Drop206/22/184, Joint241/57/184;
two Joint witnesses121/29/92, all in introduced/closed/final order. Check them
before interpreting any new edit totals. Native final8/old4 and all110 use their
own frozen raw-index bytes/hashes and independent cell scope. No source ID,
audio/time denominator or previously failed trial may be filtered by effect.

Formal entry:

```
python -B run_content_edit.py --config NEW_CONFIG.json --source-manifest MANIFEST.json --environment ENVIRONMENT.json --prelaunch PRELAUNCH.json --out /media/user/.../NEW_RAW
```

Manifest uses `code_commit` and complete `files[{path,bytes,sha256}]`.
Prelaunch requires `experiment_id`, `code_commit`, `frozen_config_sha256`,
`source_manifest_sha256`, `environment_sha256`, `root_preflight_path`,
`root_preflight_sha256`, `raw_result_location` (resolved actual output path).
The no-argument root preflight must be run and bound separately; a source-only
receipt is not environment/GPU validation. The entry requires clean standalone
source, checks every input SHA before and after, and retains a failure gate and
partial output. Raw text/lifetime/event files stay on8TB. Only bounded audited
summaries and necessary literal examples should be brought into Git.

`historical_pairs.py` is a separate pure-function metadata recounter for root's
frozen wrapper. Call `audit_metadata(runs, opportunities, source_metrics)` on
the three frozen H3 files under `H3_RESULTS_v2/{aggregate,opportunities}`. It
checks110/22/24 and60+20+30 scope, uses only consumer_apply opportunity rows,
returns every220 five-arm paired run contrast,22 factorials, source differences
and exact two-sided sign diagnostics within each distinct phase/model/rho/arrival.
These sign diagnostics assume independent exchangeable signs, which co-served
speakers do not establish; the function explicitly labels them conditional.
They are not a way to manufacture independent windows or deployment significance.
Use original cohort/run contrasts as the physical scheduling evidence. No IO
entry is supplied for this module: root must wrap it in the same frozen identity,
config/environment/input-before-after/gate contract as the formal content reader.
The updated formal entry already calls it from the frozen `metadata_inputs`.
It also calls `speaker_sensitivity.py`: all256 paired label swaps of the8speaker
credit gains, exact two-sided tail, and all37 zero/one/two-speaker leave-out
subsets. Two repeats stay inside each speaker. The smallest possible exact
two-sided p is2/256; leave-out ranges are sensitivity, not confidence intervals.

H3 core-schema adaptation is explicit: `observed_perf` and `visible_text`, with
a frozen `session_source_map`, replace native `observed` and `text`. No sorting
or synthetic service clock is used. Each cell must reproduce original LCP
closure totals (and old14 introduced/final totals) before its new metrics pass.

# H1: original-clock registered-view completeness

This is a standard-library-only CPU analysis. It imports no model, tokenizer,
Torch, NumPy, or service runtime. The original producer/dispatch/neural/WAL
history is fixed. Reported areas are offline opportunity ceilings, not deployed
service gains and not newly earned first-display credit.

`reference_view.py` contains verbatim extracted CPU view definitions;
`reference_kernel.py` is a verbatim original pure protocol kernel. Their original
paths and hashes are in `REFERENCE_PROVENANCE.json`. `history_analysis.py`
independently implements selection/support and crosschecks those references.

## Frozen input and source roles

External inputs: `../BANK_MANIFEST.json` (all 151 N5 and 136 CK5 attempts),
`../CONFIG.json`, and original 8 TB files referenced by each trace identity.
`prepare_inputs.py` prepares those inputs from the historical S0 summaries;
it is not a serving/raw analysis and must not be executed inside a frozen
source checkout. Preparation writes the source extracts and is performed only
before source commit/freeze. Keep results, records, and temporary files outside
this source directory.

Requirements: Python >=3.10 (record actual version), Git CLI, immutable raw
access, and a complete source Git checkout plus its manifest. Every invocation
must use `python -B` so bytecode does not dirty the frozen source.

Root performs commit, full source manifest, bundle/import, CURRENT/no-argument
preflight, external experiment RUN_RECORD and resource/clock gates before any
formal execution. `history_analysis.py` additionally verifies actual source
HEAD/clean tracked tree/full manifest bytes, rather than trusting argv commit.

## Formal CPU controls

Set `TMPDIR`/`TEMP` to a newly allocated directory on the designated 8 TB result
disk, then from this source directory run:

```
python -B -m unittest -v test_history_analysis
```

All tests are declared scripted CPU fixtures, including their original clocks.
They are not neural trajectories or measured service latencies.

## Formal analysis CLI

Replace paths/commit with those in the actual root launch record. All outputs
must be previously nonexistent and outside the source. Pilot positive3 and
full287 have different output/run records even when using the same source.

```
python -B history_analysis.py \
  --manifest /path/to/frozen/BANK_MANIFEST.json \
  --config /path/to/frozen/CONFIG.json \
  --source-commit FULL_ACTUAL_EXECUTION_COMMIT \
  --source-manifest /path/to/HISTORY_V1_SOURCE.json \
  --selection positive3 \
  --output /8TB/results/revtrace/dsn_continuity_cost_20261102/history/H1_POSITIVE3_v1
```

Then use `--selection all` and a new `H1_ALL287_v1` output only after pilot gates
are interpreted. `--remap OLD_PREFIX NEW_PREFIX` is solely for a byte-matched
copy; each original bytes/SHA is still mandatory. Raw paths already refer to
the authorized original experiment disk and need no remap in the normal run.

## Meaning of outputs

- Original FIFO row order, root/frontier/text and present identity/mode fields
  must reproduce exactly. Absent historical optional identity fields are
  counted explicitly. Missing required clocks/bindings or corrupt complete
  raw data fail; incomplete original attempt sets remain censored.
- Tips come only from original Consumer registrations. Host-only results may
  contribute to the stricter generic all-parent support test, never become
  candidate tips. Original Owner generation retirements, modes, epochs and
  individual revocations are enforced. The whole original job/text is selected.
- Support is checked at original `observed_perf` (apply), not the earlier
  receive time. Complete host arrivals and Owner retirement between adjacent
  Consumer applications split the opportunity window; they may only remove
  registered support.
- `joint_gap_area_within_session_observation` and corresponding wall seconds
  are the conservative primary metrics. `joint_gap_area_global_prefix_extension`
  is a separate held-state/right-censored sensitivity after a session's final
  actual application. `joint_gap_area_audio_seconds_x_wall_seconds` includes
  both, and must never be presented without the decomposition.
- Distinct deficient audio is an interval union, not a sum of repeated point
  frontiers. Gaps have original start/end, selected original job/root, trigger,
  restoration/newly-legal category, and right-censoring metadata.
- `selected_erased_characters_at_original_apply_cuts` describes the fixed
  apply-cut selection sequence, not a continuously simulated deployed UI.
  Equal-max-frontier different-text ties are explicitly counted; the primary
  rank reproduces the historical deterministic F/publication/job rule.
- Every actual application gets a deadline snapshot, including same-timestamp
  and final zero-following-duration EOS applications. First-D2/C8 includes
  every fractional tail and is separate from continuity area. Its registered
  view values assume zero extra application delay, not observed online gain.
- Analysis CPU is separately recorded; milliseconds are never subtracted from
  audio-seconds x wall-seconds. A later measured-application-delay sensitivity
  requires a new frozen configuration and time-axis replay.
- `SUMMARY.json` retains every planned attempt and failure, with per-attempt
  input before/after hashes. `GATE.json` is an execution/completeness gate;
  the independent scientific decision belongs to root, not a green counter.

No current 110/48-bank claim is included in this V1. The same semantic contract
can be applied there only after its raw manifests/configuration are frozen.

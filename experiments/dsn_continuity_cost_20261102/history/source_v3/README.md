# H1/H3: original-clock registered-view completeness (V3)

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

## V3 additions and current-bank execution

V1's failed controls and V2's corrected original-bank runs are preserved under
their own actual commits. V3 retains the query/reference state separation and
contains 22 named scripted CPU controls (17 prior plus 5 additional controls).
It adds exact latecore reference definitions, per-original execution-commit
validation, and a strict empty-registration distinction for missing Worker
records. A missing Worker file yields a legitimate zero only after the entire
original FIFO prefix proves no private tip was registered; otherwise it stays
`CENSORED_REGISTERED_PRIVATE_WITHOUT_FULL_WORKER_BINDING`.

`prepare_current_inputs.py` prepares metadata and verbatim latecore reference
extracts before freeze. Do not execute a preparation helper in a frozen source.
The external `CURRENT_BANK_MANIFEST.json` binds 158 current cells (110+36+12),
each with original raw bytes/SHA. `--selection current_s_on` selects exactly
90 actual two-lane S-on cells (66+18+6). R1_S1, R0_S1 and full joint positive
controls retain separate arm/R identities. The 68 S-off snapshot controls are
not part of a claim about residual opportunity after current S.

After the frozen 22 controls pass, use the same analysis CLI with external
`CURRENT_BANK_MANIFEST.json`, `CURRENT_CONFIG.json`, the actual V3 source
commit/manifest, `--selection current_s_on`, and a new original-disk output.
The current-bank raw provenance is the accepted aggregate `COVERAGE.path`
plus `attempt0`, never the historical plan's stale output alias. Current
Canonical/Private tasks remain those of the original f0 execution source.

V3 records the original erased-character count alongside the hypothetical
selected count at original apply cuts when the original field is present.
Neither count covers intermediate eligibility-boundary text switches; that
scope remains explicit. No new timing-delay sensitivity or online display is
implied. The first-D2/C8 outputs remain separate zero-application-delay
opportunity ceilings including fractional EOS, not an assertion of deployed
timely recovery windows.

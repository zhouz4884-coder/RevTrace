# Closed-loop execution profile schema

Producer: `fit_execution_profiles.py`. It runs on CPU and reads all 48 actual
prior V5 online cells only after the original completion and independent audit
summaries pass. The original calibration/evidence is not overwritten.

A complete `TOKEN_LIMIT_BOUNDARY` run is included alongside
`PASS_PROTOCOL_COMPLETENESS`; both must have `fine_window_accounting_complete`
true. Capped rows, their generated lengths and every physical lease remain in
the profiles. `CELL_STATUS.csv` records per-cell status and cap counts. The
pre-repair script is retained as `fit_execution_profiles_v1.py` and must not
be used for fitting, because its status check would incorrectly stop at the
complete negative-boundary run.

Invocation:

```
python fit_execution_profiles.py --base8tb B --old-results O_old48 --old-calibration P_old/CALIBRATION.json --output new_unique_dir
```

All data/output arguments must resolve underneath B. No SSH or model is
invoked by the script. `worker_records.jsonl`, `events.jsonl`, physical batch
accounting, configuration, provenance and result files are all hashed.

## Proposal profile

- `cal.cost_seconds.proposal[str(n)]`: median full physical Worker lease for
  actually executed FP16 proposal batches of n rows. Lease ends at Batch-drained.
- `cal.contextual_cost_models.proposal`: fixed 15-step Huber IRLS ridge in the
  exact seven raw coordinates consumed by `ces_policy.cost`; the seventh
  coordinate is zero. Features use declared input prefix length, interval,
  prompt length and physical n. Actual generated length and F2/context-override
  labels do not enter the feature vector. Full raw costs/outliers are retained.
- `cal.closed_loop_profiles.proposal.row_fraction_by_n`: keys `global` and
  `str(n)`, with `{support, physical_batches, fractions}`. Each fraction is
  `(Token/Stop terminal - Worker start) / actual complete physical lease`.
- `row_fraction_by_n_audio[str(n)][bin]`: the same schema, with `global` n
  available. Bins are `0-8` = [0,8], `8-16` = (8,16], `16+` = (16,infinity)
  seconds of the declared waveform prefix. Use n/audio then n then global
  fallback; inspect both row support and physical-batch support. The recommended
  minimums are eight rows and eight distinct physical batches.
- `median_generated_tokens_by_audio_bin[bin]`: `{support, median_generated_tokens}`.
  Generated length is a historical training target for future symbolic costs,
  never a known current/future output feature.

Fractions are not clipped if invalid: an actual clock outside the recorded
lease stops calibration and preserves the failed output. The profile is an
exchangeable row forecast and does not infer current per-row EOS identity.
The held-cell diagnostic is not held-source or independent GPU validation.

## Root compatibility profile

`cal.closed_loop_profiles.compatibility[direct|fallback][same|mismatch]`
contains `{support,matches,probability,lower,upper,unique_cells,unique_source_frontiers}`.

The denominator contains only the latest same-Session/same-frontier Private
node actually available to the Owner before the Authority enqueue. It must
already have been received and accepted into the Private result map, witnessed
by the corresponding display event. Obsolete completions, future completions
and future publication cannot be used. No-node cases are separately counted
and never counted as incompatible.

Birth `same` means actual declared Parent and full prompt Token sequence both
equal those of the Authority target. Matching means the actually selected
Canonical P equals that pre-existing Private node's P. Accepted Verify cases
are excluded from the Direct/Fallback rate fit. A fallback row's recorded
candidate origin is checked against the available node.

For n>=8, prediction is the Beta(0.5,0.5) mean `(matches+.5)/(n+1)`. For n<8,
prediction is null, not zero. Bounds are the Wilson interval with
z=1.959963984540054 on raw counts, with [0,1] at n=0. These are descriptive
repeated-observation intervals, not independent/clustered confidence guarantees.
Unchosen operation outcomes are never filled in.

This estimates conditional **root projection equality**, not retention of a
complete private chain, actual future Consumer display, or transcript quality.
Runtime `eligible_chain` and actual pending/publication conditions must still
hold. This phase reuses prior validation audio as training/diagnostic material.

## Outputs and evidence scope

- `PROPOSAL_ROWS.csv`: every actual proposal row with timing/CDF data.
- `PROPOSAL_BATCHES.csv`: paid physical leases and observable fit coordinates.
- `ROOT_COMPATIBILITY.csv`: all actual Direct/Fallback selections, including
  excluded no-node cases and the specific matched Private job when available.
- `CELL_STATUS.csv`: all 48 statuses, completeness and proposal/authority caps.
- `CALIBRATION.json`, `INPUT_MANIFEST.json`, `SUMMARY.json`: augmented profile,
  complete input hashes, counts/rules and output hashes.

Local unit fixtures exercise extraction and denominator discipline only.
The real 48-cell extraction is executed and independently rechecked by root;
this schema document does not claim it has run merely because the script exists.

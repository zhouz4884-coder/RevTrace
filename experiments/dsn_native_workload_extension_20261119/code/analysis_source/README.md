# Natural workload extension: independent three-policy recount

Pure standard-library analysis of a fully closed `3 conditions x 2 repeats x
declared actual N` bank. No runtime/controller/auditor or neural modules are
imported. `base_recount.py` is a byte-exact copy of the prior frozen 720V2
analysis; only its per-cell identity, original endpoint, physical-window and
total helpers are used. Its old eight-source loader, CLI and factorial
functions are not called. `DERIVATION.json` records the copy identity.

The new outer loader requires the complete dynamic one-to-four-source
reference bank and all three policies: Conservative/S1, Fullcall/S0,
Fullcall/S1. It never estimates a complete R x S interaction.

## Input layout

- `gpu_results/SERVICE_LONG_NATURAL_V1/{CONFIG,SUMMARY,GATE,RUN_RECORD}.json`
- Full bounded per-cell mirrors under `cells/<cell_id>`.
- Frozen configs under `plans/configs/SERVICE_LONG_NATURAL_V1`.
- `gpu_results/REFERENCE_LONG_V1/{REFERENCE_RECEIPT,REFERENCE_DETAILS,GENESIS,SUMMARY,GATE}.json`
- Each cell additionally includes the original `consumer.jsonl`, bounded to
  2 MiB and byte-matched to its original independent view-audit input list.

## Formal invocation after Root freezes this source

```text
python -B final_recount.py --source-manifest SOURCE.json --evidence-root EVIDENCE_ROOT --campaign EVIDENCE_ROOT/gpu_results/SERVICE_LONG_NATURAL_V1 --plan FROZEN_PLAN.json --reference EVIDENCE_ROOT/gpu_results/REFERENCE_LONG_V1 --selection FROZEN_SELECTION.json --expected-sources N --out NEW_RECOUNT_DIRECTORY
```

The script checks its own clean complete source manifest, writes run/config/
environment identities, refuses incomplete banks before final point estimates,
and preserves derived-analysis failures separately from GPU-trial status.

`python -B -m unittest test_readpoints` exercises synthetic CPU arithmetic.
Development runs are not formal frozen experiment gates.

## D2 read point

For each original interval that already passes first-display D2 and original
certification C8, read the actual Consumer state at `offer + 2`. The event-
sourced state is right-continuous and persists through the explicit complete
FIFO `SERVICE_END`, including after its last state-change row. Reads later
than END or lacking an initial state witness are censored/NA, never zero.

Output separates actual missing audio, missing-frontier weights, and the union
of support-classified same-root loss segments intersecting that interval.
Partial EOS audio uses its real sample range. Multiple windows cannot double
count one read point. A root-boundary-truncated legal window cannot authorize
a later-root classification. Full high-watermark area and classified same-root
areas remain separate, with restoration duration and censor counts retained.

All zeros, reverse effects, source denominators and SLO misses are kept.
The S-at-R1 missing-audio difference uses each policy's observed first-credit
population and is labeled as such. Any censored observation propagates to an
NA point and an interval difference; it is never replaced by zero. Recorded
restoration durations exclude censored/truncated windows, whose observed
exposures and counts are reported separately.

`quality_recount.py` independently verifies the existing runtime's whitespace-
only final-task CER against each original official transcript. Its `normalize`
expression is identical to NN1145 `content_endpoints.normalize`; punctuation,
case and Unicode forms are unchanged. Every final transcript is byte-for-byte
text-equal to that source's measured original complete-state final transcript.
`QUALITY.json` reports per-source quality, distinct-source pooled CER and all
execution outputs by policy, with timing-repeat denominators explicit.

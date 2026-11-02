# New8 / complete32 CPU report: pre-result source ready

`report_source_dev/` was written without reading new service results. No controls, model, raw trace re-execution or CURRENT action was run. Root freezes this independent complete source plus STATISTICAL_CONTRACT before any result analysis, runs eight formal controls, then invokes it only on the complete32queue.

Source files: report_common.py, make_report_config.py, report_confirmation.py, test_report_controls.py, README.md, STATISTICAL_CONTRACT.json. Pure stdlib. ActualNN4f and original servicedriverd865 identities remain separate.

## Fixed estimands and algorithm

N=8speakers, one new utterance/source each,32trials,2policies×2fresh. Combine both repeats **inside speaker**. Primary coverage is all audio-duration-weighted credit/offer. Always output:

- mean of eight paired source percentage-point gains;
- ratio-of-resampled-sumcredits/sumoffered paired percentage-point gain (the primary coverage effect).

Exactly `random.Random(20261102)`,20,000draws×8indices with replacement using randrange(8); source order sorted speaker_id/source_id. Two repeats and policies stay together.95%percentile interval uses linear interpolation at `(n-1)*p`,p=.025/.975. Negative gains are retained; no seed/estimator/source selection. All20,000draws+indices remain8TB, bounded PAPER_DATA carries both point/CIs. Old four-source sensitivity is excluded.

## Input/output

After service completion, `make_report_config.py --service-plan ... --campaign ... --out ... --raw-out ... [--c4-summary ... --c4-gate ...]` hashes full original PLAN/SUMMARY/GATE and all32 original a13audit/config/task files. No partial queue/subset accepted.

Formal `report_confirmation.py --config ... --manifest ... --prelaunch ...` requires configSHA and Root CURRENT/noarg path/SHA. It writes actual environment/runrecord before reporting. Original task/state/C/IDs audits, per-source repeated quality equality, original offered/EOS and32cell IDs are hard gates; performance direction is not.

Per-policy alloffer/credit/%, run-level D99/C99median+range, originalD2C8passes, miss/EOS/missing counts and common model-drain boardJ are reported. Null/unboundedP99 remains explicit. Unique quality references/edits are counted once per speaker; repeated trials do not multiply the acoustic GT sample.

C4schema matches the independently agreed32closure interface: complete/pass32,8sources, actualchecker c4dde+NN4f, all case IDs unchanged, inputSHAstable, original35controls/checkerPASS percase, selected step denominator fromframes. If C4is pending, output status is PERFORMANCE_COMPLETE_C4_PENDING and no illegal-install count is invented; final PASSrequires terminal closure. Both C4terminal files are frozen inputs when provided.

Reference generation and its GPU expenditure remain separate, never counted as serving trials or success. No reports or data from this source have yet been generated.

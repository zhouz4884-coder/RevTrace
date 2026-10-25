# Analysis corrections retained with the evidence

These are post-processing corrections, not changes to the frozen GPU runtime,
outputs, source, workload, deadlines, selected actions or performance metrics.
No extra GPU execution was used to correct them.

1. The inherited safety audit's JSON summary contained a literal
   `actual_model_calls=0`. Its PHYSICAL_COSTS.csv already held actual costs.
   A second audit replaces only that metadata field with1713 online serving
   model calls. All four metric CSVs are byte-identical. The original audit,
   corrected audit and AUDIT_METADATA_CORRECTION.json are retained separately.

2. The supplementary local selected-row diagnostic initially zipped CDF times
   with a cumulative array containing an initial zero. Its unit-mass assertion
   failed before any result file was written. That script is preserved as
   `tools/audit_selected_rows_failed_v1.py` (SHA256
   41244c17918f416e6844510cdc2b620fa843a39a487f55feb5a8ba325300e0e1).
   The corrected reader uses `cumulative[1:]`, validates each outcome's unit
   mass, and completes2430 actual selected-row checks. It does not modify the
   runtime CDF, forecasts, input tensors, raw evidence or primary audit.

3. Fine and Standard omit target-feature telemetry. The diagnosis's zero
   *observed* successor-opportunity count in those arms is not evidence of zero
   real opportunity. OPPORTUNITY_COVERAGE.csv marks these cells as
   NOT_OBSERVED_NO_FEATURE_TELEMETRY. Cross-policy opportunity prevalence must
   not be inferred from these zeros. Critical-path and endpoint metrics are
   still recomputable for all48 cells from their actual jobs and events.

# Post-processing v2 directory enumeration repair

All A/C GPU and primary safety audits completed. Corrected B also completed18
original-layout paid Oracle runs. The CPU continuation then stopped because
analyze_C.py treated the `C/journals` directory as if it were a serving cell.
The initial POST_ABC.log, NEXT_STAGES_STOP.json and empty failed analysis
directory remain unchanged. No D GPU had started; no A/B/C GPU rerun is needed.

Version2 analyzers iterate the exact frozen completed-cell manifest, rather
than all directories or a permissive exists-filter. This both excludes the
journal store and still fails on any missing planned cell. The same latent
enumeration problem is removed from the anchor-policy checker and the local
actionability/opportunity analyzers before they run. No measurement, runtime,
gate threshold or source manifest is changed by this repair. Version2 D
controllers bind the repaired checker hashes in their new frozen plan.

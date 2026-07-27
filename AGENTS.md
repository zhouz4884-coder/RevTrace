# RevTrace research execution contract

1. Finish the complete requested experiment scope before reporting.
2. Every run must have an experiment ID, frozen config, code commit, environment
   record, raw-result location, aggregate summary, and gate decision.
3. Keep models, datasets, environments, caches, raw logs, and large results on
   the designated 8 TB experiment disk. Commit only bounded, audited evidence.
4. Do not present proxy, oracle, operator, offline, or idealized numbers as
   deployed serving results.
5. When a gate fails, separate semantic-hypothesis failure, code defects, and
   finite-precision/model-mechanism causes. Run same-input, repeated-run, and
   legal-oracle controls before proposing a repair.
6. A repair must retain a strong end-to-end performance opportunity. Otherwise,
   freeze an evidenced NO-GO.
7. Natural-trace prevalence, stress-test coverage, and deterministic guarantees
   are distinct evidence tiers and must never be merged.
8. In exact mode, deadline pressure must never authorize an uncertified state
   commit.

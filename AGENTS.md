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

## Local source-identity launch gate

- Preserve the legacy dirty checkout; do not treat its HEAD as the source of a
  different frozen experiment. Do not pull/reset it to make provenance appear
  current. The local checkout map and verified source refs are recorded in
  `experiments/repository_identity_20261027/SETUP.json`.
- The initial SETUP is historical. The current machine-local source pointer is
  `experiments/repository_identity_20261027/CURRENT.json`; no-argument preflight
  validates that pointer and its manifest hash. It does not relabel old runs.
- Distinguish the GitHub evidence-archive commit from each actual execution
  source commit. Archived bundles must be verified and imported so that the
  full execution commit resolves locally; an archive's HEAD is not a substitute.
- Before any new run, require a clean source checkout, a byte-matched complete
  source manifest, and the full resolvable source commit. Run
  `python experiments/repository_identity_20261027/preflight.py` from this root
  for the current frozen source. A changed source must be committed and frozen
  again, not relabelled with the old commit or manifest.
- Rule 2 remains mandatory. Before launch, record the experiment ID, frozen
  config and environment hashes, actual source commit, designated raw-result
  path, and intended summary/decision paths. After completion, fill those paths
  with real results and a gate decision. Passing source identity alone is not
  a completed experiment, an environment validation, or GPU evidence.

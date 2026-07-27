# Provenance

RevTrace was extracted as a standalone research project from:

- source workspace: `D:\StreamTxn`
- source Git commit: `dc8887dd538cc3d9916f441b38ebd909e92db97e`
- extraction date: 2026-07-27

Only the RevBatch → RevGuard → RevTrace lineage was migrated. The source
workspace also contains unrelated problem explorations, agent postcondition
work, DistriCast, and killed serving ideas; those were intentionally excluded.

Frozen artifacts retain their original internal names and hashes. The standalone
project maps them into phase-scoped directories without rewriting raw evidence:

| Original lineage | Standalone phase |
|---|---|
| RevBatch gate | Phase 0 |
| RevGuard mechanism and state-contract gates | Phase 0 |
| RevTrace deployed two-GPU system | Phase 1 |

The original workspace remains intact as an archival source. Future work must
run from the standalone RevTrace repository and use the phase-scoped remote
paths documented in the root README.

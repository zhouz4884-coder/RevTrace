# P2 — Fault taxonomy and guarantee boundaries

This table separates injected content selection faults, ordinary asynchronous
completion, implementation defects and storage failure. It is not a natural
failure-rate estimate. The checked current source is N1 f0e5864 plus its
132-file manifest; historical measured identities remain campaign-specific.

|Fault / injection site|What a weaker method misses|Property / actual protection|Evidence tier and observable consequence|Boundary / recovery|
|---|---|---|---|---|
|Expired epoch or stale parent at result/admission|Blind trust in a delayed result|Current epoch, owner, parent, contract and frontier checks; conventional fencing succeeds here|CPU historical fuzzer and actual `dgft.py` predicates; stale-epoch E1 checks are CPU replay of GPU records|Not a neural fault or natural prevalence. Exact retry returning an old receipt is not a new old-epoch admission|
|Wrong actual execution context before model call (F2)|Consistent fields, owner/version and checks made under the same wrong context|Independent correct-context selection evidence; either trusted generation or complete correct-context verification plus paid fallback|E1:24 constructed contexts/12 sources, actual consumed prompt replaced; fixed-future output changes24/24, error counts worsen15, equal8, improve1. Online72 has actual paid serving alternatives|Instrumentation digest is not hardware attestation. Trusted Authority context corruption F5 is admitted: excluded by trust assumption, not magically detected|
|Consistent candidate Z/P/text replacement after generation|Self-consistency or re-rendering certifies internal derivation, not which output a trusted execution selected|Binding to trusted selection evidence as well as metadata; conventional full-composition control is valid|Historical result-mutation CPU fixtures are distinct from E1/online actual context GPU injection|If trusted owner signs arbitrary substituted output, this is outside the non-Byzantine caller assumption. Do not call a content hash an execution attestation|
|Selected P correct but `worker.text` altered before installation|Core state predicate may remain true while displayed text is false|D1 owner-side render of frozen job + complete Z, exact P/text binding, persisted render inputs and replay validation|PhaseD R0 four CPU text-only counterexamples; D1 regressions. GPU serving uses trusted render but this is not four GPU SDC trials|Certifies derivation/provenance, not ASR truth or completeness. Capped output may still be legally admitted|
|Late completed Proposal, target already covered or private generation retired|Receive path can publish an obsolete result after a valid canonical commit|Owner receive freshness plus finite reconciliation; Consumer version/frontier fence can also successfully reject|E0 deterministic CPU witness. N1 real GPU post-compute ordering underway; no new counts until independent audit|Stale server publication is not automatically actual visible harm, false SLO credit or canonical contamination|
|Ahead Proposal incompatible with updated canonical root|Current-version stamp and target>F are not proof of actual state ancestry|Exact same-boundary projection chain; retain only complete compatible provisional view. New birth Parent ID alone is not required|PhaseD fixed-content timing study and exact-chain controls; N1 compares existing snapshot vs full two_lane actual Consumer|Necessary recognition correction must not be renamed avoidable certification rollback. Never concatenate unproved token/string suffix|
|Partial WAL final frame / process kill during write|Volatile admission loses history or naive parser accepts a torn record|Length/checksum framing, complete valid prefix, synchronous successful write before ACK/install|CPU torn-tail offsets; real owned-process SIGKILL campaigns separately indexed|Discard only incomplete final frame. No disk-corruption repair, arbitrary power-loss test or global group atomicity is claimed|
|Complete WAL frame corruption|Treating every bad suffix as a harmless torn write can erase acknowledged history|Fail-closed complete-frame checksum / semantic validation|Actual CPU corruption fixtures in `test_durable_journal.py`; not GPU bit-flip evidence|Checksum detects covered corruption; no availability guarantee on corrupt storage|
|Crash after durable install but before publication / duplicated client retry|Commit durability alone does not make the fact visible to a restarted Consumer; lost IDs allow second admission|Durable request identity and receipt; reconstruct committed facts; new FIFO stream/epoch; replay D1 and republish canonical view|PhaseD3 true group-process kills measured restart→actual certified Consumer~31s; Row recovery has distinct~36s clock. CPU exact retry preserves one transition|Ledger-only ms, model-init seconds and actual Consumer seconds are different clocks. Internal install marker is not automatically external client ACK|

## Fault sources and checks that must not be conflated

* Immutable Worker job fields do not prove actual processed inputs. Audit recorded
  cast tensors/decoder IDs and trust the declared Worker boundary; no TEE claim.
* Correct-context verification is a legitimate alternative, not a weak baseline.
  Full token/stop/budget/P validation is stricter than a single margin threshold.
  Its actual fallback, physical batch cost and candidate waiting are paid.
* Natural batch-realization differences, synthetic output mutations, real GPU
  F2 context replacement, IPC reordering and CPU protocol fixtures are five
  distinct evidence classes; none estimates the others' prevalence.
* Full Standard Safe Async may implement every check and has equivalent safety
  in existing controls. The contribution is the application contract and tested
  coordination obligations, not a claim that OCC/WAL cannot express predicates.

## Authoritative anchors

E0: `baseline/E0_invariant_audit_20261015.md` and `P0_IDENTITY_AUDIT.json`.
E1/E2: `historical_20261020/INTAKE_AND_CASE_RECOUNT.json`, original source/archive
identities, complete report and independent raw/score/quality audit.
PhaseN: `source_archive_v3/experiments/phase_n_20261021/EVIDENCE_INDEX.json`;
T1 is e73115c, not the calibration runtime copied into that historical folder.
PhaseD: `source_archive_v3/experiments/phase_d_20261021/FINAL_RESEARCH_REPORT.zh.md`
and `EVIDENCE_INDEX.json`. Row150 and online72 retain their own source manifests.
N1: `N1_DESIGN_FREEZE.md`, `N1_SOURCE_MANIFEST.json`, CPU_N1_v1.xml and remote
CPU_N1_LINUX_v1.xml. Now completed54 formal+2 pilot GPU runs, exact assets and
actual Consumer audited; see N1_REPORT.zh.md and N1_LOCAL_SUMMARY_v3.json.
There are34 stale server publications in owner-freshness ablation and1 actual
root-incompatible view in the incomplete snapshot Consumer. Full two_lane
RevTrace/Standard remain protected; the actual-view witness precedes the chosen
later IPC hold and is not attributed causally to that later intervention.
All54 normalized canonical histories match. New CDE/conditional-attack rows will
be added only after actual live implementation and frozen GPU evidence.

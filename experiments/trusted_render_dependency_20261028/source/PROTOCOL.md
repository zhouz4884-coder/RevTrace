# Trusted-render dependency completion, not a new scheduler

## Scope and current evidence

This work completes original goal section5. The previous goal turn made real
progress but did not prove the whole objective achieved. Its context and
waiting-algorithm NO-GO decisions remain unchanged. The new work is not VACC,
R9, V2, DAG grafting, a new model or a renamed scheduling result. No paper edit.

Baseline archive41b8e2769e67ea48184ba122556b3130bc878c95; actual runtime
ffaa7ab41dd8d6099efd0eb9abe2334951dc5932. The four real cold episodes
show11.44–12.15s in trusted-render library imports, about1s in initial processor
load, and about0.02s in WAL replay. Worker overlap improved first-new-fact RTO
but did not remove this old-fact dependency. Those measurements are not rerun
or relabelled by this protocol.

## CPU gate before any new GPU trial

1. Inspect the exact native tokenizer/backend, parser and their dependencies.
2. Prepare a frozen native tokenizer-program snapshot and exact AST dependency
   slice from the installed, byte-pinned package. This is executable vocabulary
   and parser code, NOT cached transcript/selected output. A trusted preparation
   imports the real AutoProcessor and records implementation/version/asset hashes.
3. Use the same pinned Rust tokenizer engine, fixed encode/decode options, all
   actual special-token flags and a normalized no-padding/no-truncation backend.
   Require semantic backend-serialization identity, not only sample agreement.
4. Re-render every observed old-campaign row and durable text binding using each
   record's own P/Z/language/chunk. Do not move stored Z to another parent and
   call it new neural generation. Add all-vocabulary decode, Unicode fragment,
   repeated-pattern, language/tag and EOS/budget controls.
5. In a fresh light process check that torch/transformers/qwen_asr/librosa were
   not imported. Check wrong assets, parser/helpers, tokenizer program, package
   version and unsupported options fail closed before replay/publication.
6. Keep actual native reference imports/processor as the legal oracle and retain
   all mismatches and failed gates. CPU/startup operator cost is not serving RTO.

The equivalence argument is conditional: identical tokenizer program/engine and
fixed wrapper operations, plus the same parser AST/global bindings. It is not
a new TLAPS whole-program/Rust/compiler proof or a model-accuracy guarantee.

## Serving gate, only if CPU conformance passes

A changed implementation must not masquerade under the old v7 WAL contract.
Freeze a new full source and an explicit allowed-renderer/semantic descriptor,
including native and light implementation identities. Both baseline and optimized
arms must declare that same allowlist before their precrash histories are made.
Actual backend choice is observed startup metadata, not an unrecorded contract
substitution. Native GPU workers still execute the original full model path.

Preserve replay_bound_text, every P/Z/text digest, parent/frontier, owner/epoch,
accepted-input obligations, actual Consumer and the original clock. Compare
RevTrace and full Standard with identical resources/fault points. Never replace
re-rendering by trusting a stored text+checksum or mark old facts as new progress.

If equivalent loading cannot be established, stop this port and retain NO-GO.
If it can, first a small real cold-recovery feasibility test, then a frozen
four-arm comparison only when there is a measured critical-path opportunity.
Report all-old visibility, first-new fact, precrash debt clearing, entire-run
SLO/cost and regressions separately. No guaranteed RTO or exclusive algorithm
benefit is assumed. All attempts must be synchronized to the original GitHub.

## Completion audit of the wider active goal

| Requirement | Current authoritative evidence | Remaining or conditional work |
|---|---|---|
|Identity/old negatives|Clean runtime/analysis manifests, imported bundles,41b8e27current pointer|Historical UNKNOWN bindings stay unknown; never substitute archiveHEAD|
|Implemented pre-freeze finite waits/strong controls|Three bounded six-policy stages, real inputs/WAL/Consumer, paid two-case operators|No larger independent performance matrix after scientific NO-GO|
|Context recovery|14sources/512paid calls, ordinary checkpoint/full rebuild/known reanchor;11case matrix|No new recovery algorithm established; holdout48sources remains unused|
|Minimal trustworthy restore dependencies|Profiling and overlap controls passed; full renderer still imports heavy stack|This protocol completes the unexhausted implementation/conformance question|
|Native two-family actual lifecycle|Two model smoke studies, real read/write,8call schema diagnosis|Objective harm/quality benefit not established; no misleading large quality matrix|
|Formal and independent checking|21TLC outcomes,20TLAPS obligations; independent scoped review; corrected CPU audits|No full deployed refinement or deadlines theorem claimed|
|Seven evidence deliverables|Published research integration and full raw indices|Update with this work's real result before a final completion decision|

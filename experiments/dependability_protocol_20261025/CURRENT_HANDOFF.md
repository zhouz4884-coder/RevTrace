# Active combined goal — continue, do not mark complete

## NEW 2026-10-26 authoritative checkpoint (older sections below are history)

N5 v1 runtime49557578,4realGPU pilot independently audited. v2 runtime21d15cb,
12realGPU development cells now complete and ALL input/view/cost/WAL/asset gates
PASS;24ownedworkers exited. Rawarchivec272a653...6969b, n5_development_collected_v2.
N5_DEVELOPMENT_REPORT_v1.zh.md contains all measured tradeoffs, not a win claim.

v3 runtime408d75624104e7e11af3f0f2832263c632b10ed8 (141files) adds only optional
paid SIGKILL trace;238Windows+238Linux tests,3+3supervisor ownership tests pass.
Archivec020498...390dc. Two old-pool actual process-group cold recovery probes
completed; all ACKed input debts and recorded certified views survive, actual
Consumer restore~31s vs17–20mscanonicalledger, bothwholeSLOmiss. Authoritative
N5_RECOVERY_INDEPENDENT_AUDIT_v3.json and WAL replay; tokenizer/processorCPU
replay still pending and must not contend with GPU service. v2audit included
rich-logteardown inprimary; v3alignsnormalactualConsumer/model-drainclock and
retainsfullresourcelifecycle. Oldcertificate lacksserializedepoch: actualjob/
rowregistry+restartWALfence, no inventedfield. See recovery report.

Oldsupervisor3994806/start470315262 failed after SIGKILL due instantaneousdriver
occupancyquery; allfailedraw/powerretained n5_v3/recovery_development. New v2
supervisor waits<=30s onlyforverifiedownedPIDsdriverrelease, neverkillsothers.
Recoverydevelopment3996665/start470336337exited; successful rawarchive
ddceb778...fb6a7,101files verified plusoldfailedcontrol included.

CURRENT GPU: frozen105independentnormal cells running controllerPID4001824/
start470376525. DO NOT duplicate/restart. Remoteprojects/n5_v3 and results
/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v3_supervisor_v2.
Use status_n5_supervisor_v2.sh. Codecontroller11fdc252...fa436. Protocol
N5_VALIDATION_PROTOCOL_v1.md:7methods x5normalworkloads x3repeats.32native
sources/32historical-disjoint speakers frozenmanifestc58574c1...870dba6.
Sixthfaultclass21episodes NOTstarted; requiresrecoveryCPUassets+independent
GO_SAFETY_ONLYaftercurrentGPUqueuecloses. Formalnormal has NOauthority to
autostartfaultorotherexperiments. FailedcellSTOPnotautomaticretry.

CDE formalv2 PythonBFS/JSDFS20configs114487summedstatevisits711406edges same
hashes; old-rootobservationcounterexampleadded, correctderivedreservation
positivecontrolkept. formal/ENVELOPE_OBLIGATIONS.md maps assumptions/code.
Base63configmodelremainsseparate, notfullCartesianproductrefinementproof.
CPUrole-limitedattackprobe GOprivatefeedbackonly, NOclientYroute, realGPU
payload STILLNOTRUN. No newmanuscript/figures/GitHubcheckpointcreatedyet.
FullP0–P5+ADDENDUMstillrequired. Do notmarkcomplete ontheabovepartialgates.

Read PROTOCOL.md **and GOAL_ADDENDUM_USER_20261025.md**, ACTIVE_STATE.json first.
The latest user explicitly ADDED N5/CDE, conditional feedback attack and unified
cost/causal figures to original P0–P5. Original active goal text was not replaced.
No v7/v8, new KV fallback, Elastic tuning, DAG grafting, or scope shrink.

## New verified checkpoint

N1 f0e5864 real two3090 run finished:2 pilot+54 formal; formal controller3891093/
start469022337 has exited;108 owned Workers exited, no GPU process at release.
Remote8TB projects/revtrace_dependability_20261025 and
results/revtrace/dependability_20261025. CPU asset checker3940062/start469391379
also exited with PASS54/3102rows/1185batches. Do NOT restart or duplicate them.
Recheck resources before any future new experiment.

N1 raw archive c5ee313...65f6913,909files, local formal_collected/, all bytes
verified. Local event/quality/cost audit formal_independent_audit_v2, final
N1_LOCAL_SUMMARY_v3, groups/target CSVv3, second independent forward witness
and CPU policy replay. N1_REPORT.zh.md and N1_DECISION.json are authoritative.

Important: one actual root-incompatible view exists in standard+snapshot ablation
(`standard-snapshot-ahead-authority_first-0`, source1995-1836-0010, private window4
birthParent0/currentParent1, target8s/currentCanonical6s,23vs22inputtoken). It
precedes the chosen later12/14s IPC hold: reachability, not that intervention's
causal effect. Snapshot is NOT full Standard; both complete two_lane controls
safe. Independent forward graph and backward check agree; unchanged GPU trace
two_lane CPU replay rejects. Raw first display0.884s vs legal3.813s gives exactly
one2saudio false credit; no certifiedF inflation or Canonical pollution. WER
all54=9/226, full17transition histories equal. Do not claim ASRquality harm.
Owner freshness omission34 stale publications; Consumer successfully fences
covered targets.9event-only-P99 false passes vs complete-frontier metric.
192/192target logical/output matches, only180/192fullBatchlayoutmatches.
v2summary scope prose incorrectly said zero illegal views; v3 fixes text while
all metrics/raw remain unchanged. Do not cite v2's stale scope sentence.

## P0/P2/P3/P4 work

main4.pdf frozen SHAad444183...,12physicalpages,11body+refs; old PDF unchanged.
Publicmain d800..., localv6 measured source/report/decision match it. Historical
E0 and10/20E1/E2 manifests/reports copied with SHA verification; E1case recount
24contexts/12sources, future worse15/equal8/better1. OldE1 has source-archive
identity, do not invent an originally recorded Gitcommit.
Published tables recovered by Gitblob:38CSV/0.73MB. PERFORMANCE_RECOUNT_v1
reproduces repairedT1pairs and20R4/50Rowgroups; no spliced1.403x headline.
Base formal PythonBFS/JSDFS complete63configs/73770summedstatevisits/290192edges,
same reachable-state hashes; seven full-guard cuts no violations. Bounds only
one canonical interval/two frontiers/private depth2/one restart. Conditional
induction/code mapping in formal/INDUCTIVE_OBLIGATIONS; not a full refinement
proof or CDE model. Generation-retirement action is a protocol invalidation
test, not evidence natural decoupled single-flight execution always retires
in-flight generations. New CDE modeling/correspondence is still due.
CPU base focused152Win+same152Linux; expanded206Win, overlapping sets.

## Added N5/CDE current state and next required work

degradation/ has independent Git branch codex/cde-prototype-20261025, latest
2f9700cf4f321951aca3fcbbef9ab8b134e405f7; prior09a375c retains v0.25current CPU
tests pass: credit/policy13,input fsyncjournal8, receipt bridge4. These are CPU
fixtures; no live CDE Runtime or GPU result. Source byte identity/env in
CDE_CPU_SOURCE_IDENTITY_v1.json. Do not call acceptance intent a durable ACK.

Read DESIGN_v0, ALGORITHM_HYPOTHESIS and especially INTEGRATION_OBLIGATIONS.
The design distinguishes offered O/accepted A/certified C/actuallegalV, reserves
whole authority intervals to avoid partial-credit deadlock, accounts accepted
debt, and uses NORMAL/DEGRADED/CERTIFIED-ONLY/BACKPRESSURE/RECOVERY. Actual input
journal sync must precede accepted/dispatch eligibility; bridge now tests that.
Not done: persistent rejection/termination semantics; exact reservation/EOF
recovery; actualConsumerACK/current-root wiring; queue/lease/visibility features
actually changing decisions; original deadlines across restart; live integration
in a NEW runtime/branch outside N1 freeze. Do not log unused features and call it
feedback-aware. Minimal candidate action: retire only unissued expired private
targets while retaining input/canonical obligations and all missing-frontier
denominators. Ordinary expiry/queue/credit baselines get exactly same action.

Freeze development/NEW independent workload, SLO/coverage/cost, strong Fine+fair
limiter, originalDGFT, fullStandard+equal limiter, ordinarybackpressure and CDE
ablations. ThenCPU gate, boundedGPU pilot, preregister formal. All safe controls
keepC1/C2/C3/A/B/C/D/D1/WAL. No newGPU before that.

## Conditional attack

adversarial/DATAFLOW_AUDIT_v0.md: client-only display has no server prompt route;
Proposer result P feeds future PRIVATE jobs, but independent Authority uses only
canonical P. Row transport is a trusted-role channel, not a MAC/TEE; sameUID
workers do not prove OS compromise isolation. Check a role-restricted capability
first. If feasible, freeze benign entity payload and actualGPU future-consumption
study with Metadata/Renderer/Strict/RevTrace, distinguish carried prefix vs newZ
and provisional vs canonical harm. Do not turn this into a new Coarse selector
or claim defense against trustedAuthority compromise. No payload/GPU attack run.

## P5 and publication

No new PDF/source candidate created yet. Old body/title/abstract untouched.
MANUSCRIPT_PLAN and CLAIM_EVIDENCE_PLAN are plans, not a finished paper. Final
11technical-page DSN candidate now waits on added research, not just N1. Official
CFP abstract<=150, refs excluded, mandatory substantiveAI disclosure. Skills
read: latex-paper-en(main/compile/sectionwriting guides), pdf, nature-writing
(manifest+allselectedfragments+method deep guide), academic-search. No academic
MCP; official proceedings/Crossref used. LLM42 formalSOSP2026DOI3830418.3843901,
four publishedauthors; formal metadata raw in literature/crossref_v1. Loose
MillWheel query returned unrelatedrecords: excluded; use formalPVLDBPDF.

No new GitHub checkpoint pushed yet; publicmain remains observed d800. Existing
delivery clone experiments/online_admission_20261022/git_delivery_stage_v1 has
intentional missing old files (unstaged D); never reset/stage those. Publish
only additive bounded experiment prefix after audit, preserve all old blobs,
verify remoteSHA/raw bytes; do not claim anonymousmirror updated.

SSH uses alreadyauthorized nonsecret helper only, no passwords in arguments/logs.
Managed sandbox needs require_escalated for CredentialManager/network; ordinary
authorized reuse succeeded. No repeated manual auth question. EightTB assets;
no credentials/weights/audio in deliveries. Do not mutate memories unless asked.

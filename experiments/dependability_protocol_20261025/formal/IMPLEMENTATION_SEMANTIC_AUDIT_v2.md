# Final writing guard: guarantees follow actual fields and transitions

Re-read measured408d756 live_qwen.py, dgft.py, certified_display.py,
certified_envelope.py and continuity_proof.py; no edits to their frozen source.
Historical PhaseN PROPERTIES_ABC/V0_ALIGNMENT/V1_VERIFICATION_AND_COST and
V2_STAGE_DECISION retain originalscope. This is a semantic mapping, not newGPU.

## Do not silently enlarge the certificate schema

DualAxisCommitCertificate serializes session, contract/policy/transaction,
Parent, interval, prompt/audio/Z/P/runtime digests. It does NOT serialize a
standalone restart-epoch field, actual padded-input tensor, a GPU signature,
or a separate EOS/Stop flag. CanonicalSegmentJob validates contract_epoch
against state; fresh owner transport/registry and recovered WAL fence restart.
Complete Z plus declared contract's EOS/budget is checked by trusted render
and actual selection/verification. Actual model-input hashes are separate
observations under a trusted Worker. Do not call them hardware attestation.

TrustedQwenRender derives rollback5 prefix from the frozen input, appends the
complete selected Z, re-encodes P and parses Y. It rejects internal/extra EOS,
overbudget and non-EOS short output. It deliberately accepts no-EOS length256;
that can be incomplete recognition with valid provenance. Renderer consistency
does not show an untrusted Z was selected by trusted inference.

## Three coordination checks, three different statements

1. `_make_job` only rebases a proposal onto a committed Parent when the Parent
   audio frontier strictly precedes its target. Audio availability is checked
   against a real release clock. Private input and chunk are frozen at dispatch.
2. `_accept_result` separately rejects target<=currentC or retired generation
   at receive/publication. An old Parent number alone is NOT automatically a
   failure; receive freshness also does NOT prove compatible causal ancestry.
3. `eligible_chain` and Consumer `_compatible` require exact P at the same
   canonical audio boundary plus complete generation-ordered edges. Every
   canonical update/newprovisionaldelivery rechecks actual view. They preserve
   a whole private hypothesis as provisional, never a certified string suffix.

These checks establish distinct facts. A numeric version-only conservative
fence can be safe by rejecting all old-root work; it does not by itself specify
when that work is reusable. Conversely, snapshot display is not a complete
Standard Safe Async control. FullStandard is allowed allapplication checks.

Exact P equality establishes an actual causal path, not that reexecuting a
different physical batch would produce the same Z/P. PhaseN found deterministic
batch-dependent input preprocessing; no counterfactual GPU result is inferred
from a CPU reinterpretation. AuditA0/148 remains local, not a no-reuse theorem.

## Owner C and applied certified view are different clocks

Use C for the installed/persisted Owner frontier, C_view for the last certified
fact actually applied by the FIFO Consumer, and V for its legal visible view.
Do NOT add the unimplemented invariant C<=V: while publication is queued, C can
be ahead of both C_view and V. Provisional chain compatibility is checked against
the Consumer's applied certified root/version; messages do not claim a newer
version they have not applied. Owner-side receive freshness is a separate check
at publication. Controller observations require the actual current Owner/root/
epoch; stale ACKs cannot supply fresh progress telemetry or selection evidence.

Consequently this is versioned causal visibility and honest typed coverage,
not instantaneous latest-owner display or distributed linearizability. The
first legal visible and first certified-view latency metrics use actual
Consumer timestamps; owner commit/fsync timestamps are distinct. Recovery to
the previous certified frontier waits for actual C_view, not only loaded C.

## Selection alternative and its bounded evidence

Correct-context verification is legitimate if its complete Z/Stop/budget/Phi
decision realizes the declared trusted selection contract. Finite-precision
teacher-forcing and native generation may use different physical tensors;
there is no blanket theorem of numerical identity between them. PhaseN V1
independently checked actual selectedZ/P against matching FP32greedyoracles in
its16/4/1layouts:288records/180accepts,0accepted mismatches. That remains a
bounded result, not288independent acoustic samples. Newroleoperators also use
two real same-target FP32references percase and retain all paid work.

The PhaseN selector NO-GO concerned ready/legalcoverage and inclusivecost/tail
gates; it did NOT prove that fullverification is impossible. Candidate birth
Parent mismatch is a prediction feature, not an automatic correctness verdict
for new correct-context checking. No newKVreusefallback orV2producer introduced.

## Recovery and accepted input

WAL validation builds an immutable proposed next state, syncs complete selected
frames, then installs/publishes. A group fsync does not make multiple independent
sessions a globally atomic transaction. A complete valid unacknowledged frame
can recover; an acknowledged transition cannot disappear under intact-sync
assumptions. Partial final frame may be discarded; full corrupt frame fails.

Input book clones/checks a fullinterval reservation before synchronization.
Only after successful checkpoint is A dispatch-eligible. In CERTIFIED-ONLY,
new reservations pause but existing R can fill as released O arrives; this is
why a partially accepted interval is not stranded by the mode. Recovery
reconciles oldC<=actualrestoredC<=A, verifies immutable audio prefix/EOF/contract,
keeps original time/debt/rejection and re-applies typed certified facts. Same
semantics can use correct conventional derived reservation reconstruction.

Normal105 and recovery21 are now independently complete (older pending prose
in earlier formal notes is historical). Zero observed unauthorized/freshness/
accepted-loss events and finalcoverage1 do not prove universal safety or cap-free
recognition.21faults are process-group coldrestores;16.485–29.285msledger vs
30.306–31.271sactualcertifiedview, allwhole-runSLOmisses. No bound on network
display, arbitrary failures, infinite histories or unconditional progress.

## Additional input/view envelope is not a performance theorem

CPU238Windows/238Linux sets overlap; they are not476independenttestdesigns.
Finite63base and20envelope configurations are separate abstractions. Their
summed reachable-state counts cannot be combined into a production-proof
state space. CDEextra feedback performance isNO-GO againstfullStandard, while
the explicit protocol retains its conditional safety/observability value.

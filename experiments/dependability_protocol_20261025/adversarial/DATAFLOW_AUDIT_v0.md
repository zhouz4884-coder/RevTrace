# Conditional feedback attack reachability — preliminary source audit

No payload, malicious result hook or new GPU attack has been run. This is not a
claim of an exploitable network/OS vulnerability or natural fault incidence.

## Two different capabilities

1. **Client-only displayed text Y.** `LiveQwenScheduler._publish_display` emits a
   serialized snapshot. `RealtimeConsumer` applies an immutable copied event;
   its visible text is not assigned back to scheduler branch_tokens/state P.
   No current route from an external edit to this client text into future server
   prompts is visible in this source. Under this capability, NO-GO: do not invent
   a server feedback attack.
2. **Role-restricted Proposer result/IPC control.** `_accept_result` validates
   D1 then assigns actual result state_tokens to private branch_tokens;
   `_make_job` later freezes those private tokens as a future proposal input.
   The channel therefore reaches future **private** neural computation.
   Independent Authority still freezes canonical state.prompt_tokens, not that
   private tip. A coherent forged Z/P/text can be internally renderer-consistent;
   D1 is not evidence that trusted Authority selected it. Real end-to-end attack
   tests require validating this route, complete stop/budget and actual future
   processed IDs; a CPU string rewrite is not neural propagation evidence.

## Trust and IPC conditions that must be resolved first

RowComplete payload digest is an unkeyed integrity check for a trusted Worker
channel, not an authentication proof against a compromised Proposer that can
recompute its own row. RowInbox binds worker/incarnation/batch/job/session/role/
parent/contract/audio/input identity and must remain enabled. An arbitrary stale
or cross-bound result should fail before the causal attack question arises.
The two workers currently share the same host user; a whole-account compromise
would not automatically be restricted to Proposer. A role-limited injection
harness can model the stated capability but cannot prove OS isolation.

Correctly protected RevTrace may still show or reuse an untrusted **private**
hypothesis; that is not a certified state-write guarantee. Separate transient
provisional target appearance, actual future-private consumption, admitted
canonical target appearance and future-authority recognition harm. Claiming
'attack prevented' from only one of those would be misleading.

## Pending gate

Confirm immutable result/candidate and actual input flow at all four controls:
metadata-only, renderer-only, correct-context Strict, independent Authority
RevTrace. Do not create a new Coarse candidate producer or V2 selector. If a
fixed-fine controlled candidate comparison is feasible, payloads must be frozen
before output inspection, benign target entities only, and trusted Authority/
verifier must never receive an execution-context override. If only client text
is writable in the intended deployment, record unreachable rather than broaden
the adversary to force a result.

# Actual full-call structural refinement checker

This separate CPU checker reads RVN1 frames independently, joins actual original
full-call receipts to immutable dispatches, checks each new fact against its
actual prior full cut, and reconstructs actual Consumer whole-view applications.
It distinguishes old durable-fact replay from fresh write authority for old
messages. Owner namespace, session epoch and worker incarnation are separate.

Original C/U is a trusted allowed relation. The checker validates source/interface
binding and actual returned C/IDs, not GPU arithmetic, human text correctness or
fixed reference equality. Synthetic controls are neither natural traces nor
serving measurements. A controls-only PASS does not mean actual data were read.

Actual mode requires a frozen config listing every owner attempt and byte hashes
for actual CONFIG/facts/publications/Consumer/ORIGIN/ingress and each attempt's
dispatch and worker-results logs. All acknowledged final input boundaries and
original clocks must remain. A torn uncommitted tail is optional and reported;
complete-frame corruption always fails and input files are never repaired.

The final actual logger schema is bound explicitly by the analysis config. Legal
progress wrong rejections remain unknown until before/after phase ownership
evidence is sufficient. Runtime/dead-process resource proof and liveness bounds
are additional evidence, not inferred from a checksummed journal alone.

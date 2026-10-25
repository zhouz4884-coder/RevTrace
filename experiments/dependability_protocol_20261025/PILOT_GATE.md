# N1 pilot gate

Both frozen real GPU pilot runs completed; no runtime change after freeze.
The process/worker handles exited and GPU occupancy was empty at completion.
The existing certificate/WAL/time replay passed for 17 commits in each run.
Independent local event/full-P-chain/actual-Consumer audit passed for both runs.
CPU asset replay re-rendered 53+61 complete rows and exactly reconstructed
21+22 physical input batches, including complete tensor hashes and actual layout.
This last check made zero neural/GPU calls; its initial helper-method bug and
repair are retained in AUDIT_REPAIR_LOG and remote operation records.

Covered pilot: all four controlled old proposals were physically completed,
held until the real 6 s admission was durable, then retired before publication.
Ahead pilot: all four 14 s proposals remained exact-compatible with the 12 s
canonical boundary; no incompatible publication or actual illegal view occurred.
This is a valid compatible-old-parent positive control, not an attack success.
No audio/window selection is changed to manufacture a failure.

Pilot source/clock/payload checks permit the preregistered 54-cell comparison.
This is GO for the bounded experiment, not GO for an unobserved end-user harm,
performance superiority, natural prevalence or exclusive new algorithm claim.
All formal cells and failed completions remain in the report denominator.

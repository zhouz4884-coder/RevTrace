# Decisions and their reasons

1. **Do not make a fast Worker a prerequisite for a valid old fact.** The
   original N5 call order made a GPU readiness barrier dominate fact recovery.
   The revised path restores bound facts/input obligations before that barrier
   only on restart. A fresh run still sets its arrival origin after warmup, so
   the change does not manufacture normal-run deadline misses or reset faults.

2. **Separate the two improvements in the experiment.** Legacy/no-kernel,
   early/no-kernel and early/kernel arms are all run for both full methods.
   This prevents attributing an ordinary startup fix to a new protocol kernel.

3. **No field-only proof of successful effects.** Concrete journals checkpoint
   and synchronize before issuing sync events; actual validated executor rows
   precede selection events; a consumer view is privately evaluated and kernel
   checked before replacement, and application is separately recorded. This is
   trusted-host API provenance, not cryptographic GPU attestation.

4. **Canonical owner and actual consumer can differ.** C can lead V; recovery
   and delayed FIFO application must not be written as the false invariant
   C <= V. The applied root is checked against durable history, and provisional
   legality is relative to that applied root, not a text suffix heuristic.

5. **Whisper needs its actual API semantics.** Its convenience generate result
   omits EOS. Treating that as a complete selection was invalid. The repair
   keeps the underlying complete generation result, strips only the observed
   initial decoder input, verifies EOS/budget and compares native text in a
   repeated real GPU oracle. The actual route remains get_prompt_ids. Variable
   prompts are executed as separately charged serial model calls inside a
   lease; no free heterogeneous batch or cross-family throughput claim.

6. **Late-result tests do not change the neural output to obtain compatibility.**
   Hold actual A6 installation until real P8 completes, then deliver that same
   P8 after A6. Compare actual P6 and A6; preserve mismatches. The coherent P6
   corruption has an explicitly synthetic Z and original real worker receipt.
   Only the following P8 can count as a new GPU consumption. Full Standard gets
   the same controlled order and fine grid. No fault-label-aware normal policy.

7. **Checker failures are not GPU failures.** The first asset checker selected
   both Authority and Proposer at window 4. The correction restricts the test to
   the intended actual Proposer successor; it reuses the identical four GPU
   traces, retains the STOP and does not regenerate a better-looking result.

8. **Sufficient conditions, not universal guard minimality.** The composed
   finite search includes legal progress. Concrete omission witnesses and
   indistinguishable-observation pairs show why evidence is needed under a
   declared observation model. Redundant guards or equivalent Standard
   implementations remain legitimate alternatives.

9. **Costs and failure scope remain separate.** Restoring an old fact is not
   generating a new one. Process-group SIGKILL kills both workers; it is not
   warm adoption, host power failure or arbitrary network recovery. All old
   submitted work and cold reload remain charged. Kernel step CPU timers are
   subsets, not total host energy/CPU. Finite source/repeat counts do not prove
   long-run memory bounds, population fault rates or universal P99 guarantees.

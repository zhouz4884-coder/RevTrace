# CPU scope and retained diagnostic outcomes

- Frozen runtime supported regression: 258 Windows tests passed, JUnit
  CPU_win32_v6.xml. This is the same supported 22-file N5 protocol suite plus
  the new composed-kernel file, not every unrelated historical repo script.
- Frozen-runtime external tests: 12 passed, CPU_EXTERNAL_v4.xml. They exercise
  original-clock accepted-input/commit abort recovery, a legal native scheduler
  oracle, epoch/contract/owner fencing, compatible late private visibility and
  real kernel denial of dispatch/prepare/install/application/input ACK effects,
  and a post-selection integration-fault substitution before WAL. The latter
  is not a defense against a compromised Authority or arbitrary hostile host.
- No GPU execution or neural selection claim follows from these fixtures.
- The broad legacy test collection attempt found 19 missing unrelated script
  dependencies already absent from the original 141-file frozen source. It is
  not called a pass; those legacy tests were not silently edited to collect.
- The first extra abort test incorrectly expected every offered session to
  finish after the original-clock restart. Actual durable input showed session
  2 was never accepted and explicitly rejected by the unchanged timeout rule;
  sessions 0/1 retained their accepted obligations. A same-input native
  scheduler oracle produced the same outcome. The corrected assertion permits
  explicit rejection only when pre-abort accepted audio was zero. This was a
  test-premise correction, not a runtime repair or a GPU result.
- The original GPU Whisper EOS-interface failure and the later CPU asset
  selector failure have separate raw logs and STOP files on8TB. Neither is
  erased or counted among successful formal service episodes.

Formal enumeration: FORMAL_PRODUCT_v6_exact.json; 1,154 exact states, 3,429
edges, 216 illegal events rejected, 40 reachable legal-progress states;
BFS/DFS state-set SHA256 matches. One session/one canonical interval/one ahead
private target/two projections/two workers/one process-group restart/two view
revisions. This is not a full Python/GPU/OS refinement or an unbounded liveness
proof. Counterexamples are executable in characterize_information.py.

An additional two-session cut (FORMAL_TWO_SESSION_v6.json) has 308 exact states,
735 edges, 48 rejected illegal events and 6 complete-progress states. It
includes 72 states with one session installed while the shared two-row batch
is still leased. It does not multiply the one-session private-ancestry model
into an unbounded multi-session program proof.

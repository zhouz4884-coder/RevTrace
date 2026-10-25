# N5 implementation / regression record

* CPU_N5_WIRING_v1:11pass/1fail. The CPU renderer fixture used an unpersisted
  `role` field while replay render inputs deliberately contain only projection
  inputs. Fixture changed so Z itself determines P/text, matching D1's principle.
  Not a GPU/runtime selection defect and no GPU data was changed.
* v2/v3:217pass/1fail. CDE's always-ticking recovery loop exposed fully completed
  sessions whose inherited fine cursor remained1. It recomputed them as not done
  and re-accounted old windows. Merely skipping already-done reconciliation was
  insufficient because the loop recomputed done again. The fix explicitly closes
  only sessions whose **actual canonical frontier already equals full input**;
  no input/canonical frontier is advanced. Persistent rejection remains at C0.
* v4:218pass. v5 expanded snapshot/actual Consumer-thread suite:228pass.
  Sets overlap; do not sum. Tests cover all seven safe controller choices,
  input-ACK crash recovery, original clock, EOF/credit/rejection state, exact
  semantic snapshot failure before append and actual applied stream ACK.
* Input acceptance snapshot stores whole reservations and EOF/rejection decisions,
  fixing the prototype's missing recovery metadata. New live source is separate
  from unchanged N1 f0e5864 and pure CPU prototype2f9700c.
* No new CDE GPU measurement exists at this writing. The explicit early GPU pilot
  freezes data/config/source next; no retrospective performance claim is made.

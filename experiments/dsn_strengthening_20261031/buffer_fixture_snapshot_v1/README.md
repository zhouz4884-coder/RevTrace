# Controlled completed-buffer producer-fault fixture

Development source, not yet frozen or launched. This independent checkout must
have its own full commit and complete manifest. Its imported neural execution
source remains NN4f `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47` (59 files,
manifest `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457`).
The shared resident Supervisor is another separate frozen dependency.

`buffer_fixture.timing_owner_entry` keeps the original nine-argument Owner API,
patching only the transport's importable worker-entry target in that process.
`TimingFramedSender` calls the original sender first, with the original event,
then holds the parent ASR callback or completed child callback at the fixed site.
Each barrier binds its first original UID once. Later distinct UIDs at the same
frontiers pass through normally, allowing the mismatch control's necessary
recomputation from the actual corrected input to finish.
It never changes neural outputs, C/U, input eligibility, storage or Consumer.
Terminal resource snapshots stay disabled as in the historical frozen cells;
enabling them is explicitly rejected rather than silently changing payload
fingerprint semantics. This is controlled scheduling, not natural prevalence.

The controller implements the shared resident observer API:
`start()`, `poll()`, `finish()`, `close()`. It reads original logs incrementally.
Only a real Owner full-conditional-node publication, original received events,
dispatch identity, and a nonce/PID/start-ticks/payload-bound child marker permit
SIGKILL. Parent release additionally requires the original OS/CUDA/channel/
worker-loss/fence/replacement chain, with the exact completed UID preserved.
The waiting parent independently checks the referenced original native fence
rows before returning from its callback. Timeouts fail and preserve raw output.
Every release also matches the complete original child job, original started
row and child-marker SHA. The waiting parent derives that expected identity
from original dispatch/results/start rows, rather than trusting release fields.

`build_buffer_plan.py` creates four fixed fresh trials: two matches at parent
frontier 24000 and two mismatches at 32000. Order uses seed 20261031 and reverses
between repeats; primary GPU rotates 0/1. All use fullcall because this is a
buffer interleaving witness, not a strategy-performance comparison. A fixed
second original source can be attached to the positive trials only, using the
resident Supervisor's closed-loop actual-EOS request contract. No repeated
source alias or synthetic concatenation is introduced.

`run_buffer_fixture.py` verifies complete clean source identities for all three
checkouts, invokes the shared resident Supervisor, then runs
`audit_buffer_witness.audit`. The original resident GATE/SUMMARY remain distinct
from TIMING_FIXTURE_CONTROL_GATE and BUFFER_WITNESS_GATE. Before Owner launch,
BUFFER_FIXTURE_RUN_RECORD records the fixture commit, imported NN4f, environment,
config, raw path and final buffer gate path. A resident task/reference success
alone cannot pass the fixture. The final checker binds original job/birth/inc,
whole states, original full record, durable chain and actual certified Consumer
application; a child's own prediction need not equal its final output.

Development CPU gate (0 neural calls, 0 NN worker signals; one self-created
synthetic sleeping CPU process is deliberately terminated by the watchdog test):

```text
python run_development_cpu.py --base-source <unchanged-NN4f-checkout> --out <new-development-gate.json>
```

The CPU suite includes real Python spawn of the timing entry with a clearly
synthetic worker, original frame byte equality, partial JSONL handling, forged
markers, full-state/context mismatches, sealed-channel negatives, native closure
requirements, controller ordering, immutable markers, and four-trial plan
rotation. Temporary test files stay in a declared scratch root; no model or
dataset is loaded. CPU success is not a neural/OS/CUDA completed-buffer witness.

Both plan construction and runtime reject traversal/aliases. Runtime resolves
the exact frozen cell path below the verified experiment disk and refuses
symlink/junction ancestors or an arbitrary `--out`. The ordinary CLI and public
`run()` launch an independent process watchdog before neural execution. Its
frozen limit is 900 seconds, with a separate 40-second owned cleanup budget and
5-second CUDA-ownership CLI timeout. The original D2/C8 and the template's service
bound stay unchanged (240 seconds in the historical source-A config). The child validates its live watchdog's PID generation
and the config SHA before launching Owner. Cleanup reuses the separately frozen
resident harness's process proof helpers, kills only proved same-run groups,
and never treats a failed CUDA query as verified physical release.

After root freezes dependencies and the complete config/plan, formal invocation:

```text
python run_buffer_fixture.py --config <frozen-cell-CONFIG.json> --out <new-8TB-raw-cell-path>
```

No source activation/CURRENT operation or GPU campaign launch is performed by
the plan builder or development CPU driver. Root owns the formal source window,
source/environment gates and exclusive NN queue. All model/cache/data/raw paths
must remain on the designated 8TB experiment disk.

# Fixed two-client interference opportunity source

Use **[INTERFERENCE_README.md](INTERFERENCE_README.md)** for this new experiment.
The text below is the copied a13 historical documentation. The original bytes
are preserved in `UPSTREAM_README.md`; copied old entry points are support/history,
not the launch path for the new experiment. No NN or formal freeze was performed
during development preparation.

## Historical upstream documentation

# Prospective paired32 and finite resident request controller

This independent repository contains orchestration and independent analysis. It
does not contain or modify either frozen neural source. BDFA and final 4f are
separate full-manifest dependencies and retain their own actual execution commit.
The resident Supervisor is derived orchestration with per-request ingress clocks;
it imports the unchanged 59-file final dependency for Owner, workers, state,
qualifications, durable facts, transport and actual Consumer.

`run_paired_campaign.py` runs each version's true original service entry, not an
old entry substituted for the final implementation. Every cell checks complete
source identity and preserves its original raw energy and endpoint results. An
external NVML-backed nvidia-smi observer supplies two separately defined shared
windows: origin to actual Consumer certified EOS and origin to first external
confirmation that both READY worker PIDs have exited and CUDA ownership is empty.
The physical endpoint is an observation upper bound with the sample bracket in
the output; it is not an instantaneous timestamp. The common observer is a new
condition applied to both versions. No CPU or whole-system energy claim is made.

The prospective queue is all 32 cells: four previously metadata-selected sources,
two versions, two strategies, two fresh-process repeats. S0908's eight cells are
first. The controller does not call one EOS jitter a causal code defect. A hold
preserves the entire prewritten queue and records remaining cells as unrun.
The finite resident queue is four trials, with one two-strategy smoke first and
the second prewritten pair conditional on its fixed service/opportunity gate.
Each request uses its original EOS and its own recorded origin. It is a closed
loop single-outstanding client, not a fixed-arrival capacity experiment.

## Development CPU checks

Run `python -B -m unittest -v test_controls test_supervisor_cleanup`. These are CPU counterexamples only.
Set `REVTRACE_CPU_SCRATCH` to an 8TB path for Linux checks. The local default is
an ignored, tiny `.cpu_scratch` folder; it is not a model/result directory.
The checks cover complete manifests, torn facts, immutable source-marker maps,
all-offered EOS, per-request offsets, actual-Consumer release order, missing
obligations, external energy boundaries and the frozen stopping decisions.

## Freezing and root-owned launch

Commit this independent source, generate its complete manifest outside the source
directory with `freeze_source.py`, and create a Git bundle. Root imports that
full commit so that the project preflight can resolve it, selects CURRENT to this
controller and runs the project no-argument preflight. This campaign-plus-
dependencies scheme is intentional: CURRENT identifies the actual outer
controller; every cell independently validates and records its true NN commit.
The archive HEAD is never used as a neural identity.

`freeze_plans.py --root <project root> --out <new bounded output directory>
--manifest <controller manifest> --remote-manifest <8TB remote manifest path>
--remote-source <8TB remote independent source path>` writes 36 frozen configs,
the shared environment, paired32 plan and resident4 plan. It launches no model.
Stage these bounded artifacts and source bundle on the 8TB experiment disk.
Do not move the model, datasets, caches or raw output to the local checkout.

Before actual launch, root supplies a separately hashed PRELAUNCH JSON:

```json
{
  "root_noarg_preflight": "/8TB/path/ROOT_NOARG_PREFLIGHT.json",
  "root_noarg_preflight_sha256": "actual sha256",
  "exclusive_GPU_window_authorized_by_root": true,
  "asset_byte_gate": {
    "path": "/8TB/path/LIVE_ASSET_BYTE_GATE.json",
    "sha256": "actual sha256"
  }
}
```

The live asset gate must have a status starting `PASS`,
`all_asset_bytes_verified: true` and the exact `asset_manifest_sha256`. This is
actual byte validation, not source preflight or the historical asset record.
The controller also checks current interpreter/packages, actual READY model
parameter counts/dtypes, neural warmup, physical board assignment and the actual
initial allocator environment of both worker PIDs. Only the two allocator names
are read from `/proc/PID/environ`; unrelated environment values are not captured.

Actual launch commands, using the frozen environment interpreter:

```text
python -B run_paired_campaign.py --plan PAIRED32_v2_FROZEN.json --manifest SOURCE.json --prelaunch PRELAUNCH.json --out <the exact frozen 8TB output>
python -B run_resident_campaign.py --plan RESIDENT4_v2_FROZEN.json --manifest SOURCE.json --prelaunch PRELAUNCH.json --out <the exact frozen 8TB output>
```

Do not run these concurrently. Root owns the exclusive GPU queue. Both reject
existing output directories. They preserve incomplete or failed raw results and
write a gate; they do not restart, replace sources or tune the contract.

## Timing-fixture integration

API: `resident_supervisor.run_resident(config_path, base_manifest, out,
owner_target=None, observer=None)`. A supplied picklable `owner_target` has the
original nine-argument Owner signature. An observer has `start()`, `poll()`,
`finish()` and optional `close()`; failures must raise. `finish()` runs after
actual Owner completion and before independent resident analysis. The fixture
source/manifest belongs in `config.execution_dependencies` and remains distinct
from `config.harness_source` and the actual final NN dependency.

Config fields: `request_contract` is
`closed_loop_single_outstanding_independent_EOS_v1`; `request_order` lists every
registered source ID once. Source IDs retain the legal original-reference
mapping. This version does not support repeated aliases or dynamic registration.
`request_ledger.jsonl` records `request_admitted` and `request_complete`, including
source ID, request index, origin, actual Consumer EOS observation and previous
completion. `REQUEST_ORIGINS.json` maps source IDs to their immutable origins.
`SUMMARY.integrity.original_reference.status` is
`PASS_COMPLETE_SELECTED_TRACE_REFERENCE`; success GATE/SUMMARY is
`PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE`. Per-request metrics
retain every original offered frontier including EOS. Fixture-control gates and
rare-interleaving witness gates must be additional independent files, never
overwrites of the resident execution gate.

## Decision limits

Semantic equality is complete selected state/C/IDs under the explicitly allowed
source-marker mapping. It does not prove independent CUDA reruns must be bitwise
identical universally. A mismatch requires same-input/repeat/legal-oracle
diagnosis. Timing regression triggers diagnosis, not an assertion of a code bug.
No significance or equivalence is inferred from eight paired observations.
Only actual final eight-of-eight original gate passes establish that outcome.
Resident failure does not authorize new sources, artificial gaps, deadline
changes, protocol weakening or replacement of the old long-stream negative data.

## Revision v2 cleanup contract

Revision v1 remains a prepared historical source/bundle/input set; it was not run
on GPU. Revision v2 fixes a reviewed outer-Supervisor exception path. A registered
Owner group is cleaned even when its leader has already died. Signal authority
requires the launched PID generation plus its PGID/session, or an exact known
same-run worker PID/startticks in the inherited session. Reused IDs and unknown
worker generations are refused. Unregistered failures never authorize signalling
the Supervisor's inherited parent group.

Each CUDA-ownership CLI has a 2-second timeout inside the bounded release deadline.
A failed query, executing survivor or uncertain ownership writes cleanup FAIL and
trial FAIL and raises. There is no leader-only fallback that implies CUDA release.
The final 59-file neural dependency is unchanged, including its historical
internal wait_cuda_release. The outer fresh-process watchdog bounds a stuck
original call and preserves failure; it does not certify that internal wait.

Run the 28 local CPU counterexamples, then on Linux additionally run
`python -B linux_cleanup_control.py`. The latter creates a real short-lived leader
and real sleeping orphan in an independent session and proves the exact group is
terminated after the leader has exited. Its CUDA query is explicitly synthetic;
it is not CUDA-release or service evidence. Actual CUDA release remains a
separate observation in a real launch.

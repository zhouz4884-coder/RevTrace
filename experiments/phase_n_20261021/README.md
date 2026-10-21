# RevTrace DSN Phase N — audited experimental release

This release executes the user-adopted Phase N protocol, starting 2026-10-21.
It is an experimental revision, **not a manuscript update or venue submission**.

Start with [final decisions](FINAL_DECISION.md), then the
[claim/evidence matrix](CLAIM_EVIDENCE_MATRIX.md),
[T1 factorial/blocking](T1_FACTORIAL_AND_BLOCKING.md),
[V0 alignment](V0_ALIGNMENT.md), [V1 certification/cost](V1_VERIFICATION_AND_COST.md),
and [T3 sensitivity](T3_HOLD_SENSITIVITY.md). `EVIDENCE_INDEX.json` maps actual
source identities, measurements, tiers and hashes.

## What ran

- Final T1: 12 factorial cells plus six rich-observer controls; earlier
  observer versions retained as before/after evidence, not pooled.
- V0/V1: actual-input/readiness audit, fixed-state real GPU FP32 full-token/
  stop/Phi controls at batch16/4/1, independent Oracle repeats, EOS-negative
  and legal cap4 controls. These are not deployed-serving results.
- C3: three paid live preparation-only runs sharing the existing proposer;
  no candidate admitted and no online verification enabled.
- T3: nine scouts plus 45 fresh formal cells, including compatible0/6 anchors.
- Full-hook cost: 12 matched enabled/disabled cells, correctness rules retained.
- Complete current-fixture regressions and bounded legal CPU scheduling
  counterfactuals; CPU evidence is not GPU efficacy or acoustic sample count.

V2 is **NO_GO_ONLINE_SELECTOR as tested**. No new KV-reuse fallback is built.
Fresh exact verification can work, but its conditional operator cost is not
an online speedup; legality, candidate units and timely coverage are separate.

## Code and byte identity

`runtime/` is the full frozen calibration SDK, including the corrected A/B/C
carrier and explicit diagnostic switches. `SOURCE_MANIFEST.json` preserves
its exact file identities. `frozen_source/` contains the measured SDK
archives; `source_history/` retains their actual Git objects/commits. An
archive's original source identity is not replaced by the publication commit.

The original project worktree had uncommitted user changes and is preserved.
This Phase N namespace does not overwrite unrelated upstream code or papers.
Legacy modes remain for controlled comparisons. The A/B/C guarantee requires
the declared new contract, e.g. `--proposal-reconciliation lazy
--display-protocol canonical-snapshot-v1 --publish-canonical-display` with
independent canonical generation and a fresh, matching WAL namespace.
Do not enable an untested online selector merely because a historical
`grouped_replay` adaptation flag exists. Its old auditor is not the V1 full
certification proof; use the supplied independent V1 records/checker.

## Verify without a GPU

With Python, NumPy and pytest:

```text
python -B verify_cpu.py
```

This checks all published hashes and the bounded evidence archive, then runs
67 curated standalone CPU tests. The full lab checkout regressions used
complete original historical fixtures (303 baseline, 354–357 in the relevant
revision branches). Those old large fixtures are not all redistributed;
running every legacy test blindly is not a claim of standalone completeness.

The bounded archive contains isolated V1 job/result records, configurations,
audits and derived tables. Full serving trace/power/WAL, prepared audio,
models, environments and caches remain on the designated8TB experiment disk;
their exact paths/hashes are indexed. A fresh GPU rerun requires those
separately acquired assets, idle resources, matching software and exact source.
This repository does not automatically access a lab host or launch a GPU.

## Evidence boundaries

Server publication is not frontend/network rendering. Current visible text
may retract even when ever-covered audio is monotone. Input-digest logging
is observation, not neural-execution attestation. Natural incidence is not
inferred from controlled inputs, delayed delivery, reused sources, CPU
fixtures or repeated model references. Median-of-ratios and ratio-of-medians
are labeled separately. Models/datasets retain their original terms.

This is a PUBLIC append at the user's explicit repository target. It is not
presented as an anonymous artifact; no anonymous mirror was updated/verified.

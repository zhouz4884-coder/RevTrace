# Final 4f existing20 CPU content and visibility audit

This source performs one bounded read-only analysis of completed real-service
logs: 16 final4f matched trials plus 4 resident trials, 32 request instances in
total. It does not launch a model or change any original NN/C/U/runtime/raw file.

`DEPENDENCIES.json` pins the entire bytes and original commits of every consumed
vendored module. The new source has its own commit and complete manifest; it is
never relabelled as the NN commit, controller commit or evidence archive HEAD.

`run_content_recount.py` requires a complete frozen config, own source manifest,
frozen actual CPU environment, and root no-argument CURRENT analysis-source receipt.
The runner validates clean checkout/full commit/complete byte manifest, explicit
8TB paths/device/free space, fixed20 coverage and an exclusive experiment lease.
All 328 allowed raw inputs are hashed before and after. Source/config/env/index,
stdout/stderr, output and gate paths are recorded before data analysis. Existing
outputs/leases are rejected. Controls and fixtures use RAM only. Any failure gets
a preserved FAIL gate. Source identity alone is never reported as a completed
experiment or GPU evidence.
Frozen config, CPU environment, root CURRENT gate receipt and source manifest
also have explicit before/after byte hashes; drift fails the final gate.

The parent freezes Linux `ENVIRONMENT.json` from `current_environment()` with
`CUDA_VISIBLE_DEVICES=''`, `PYTHONDONTWRITEBYTECODE=1`, and the 8TB Python path.
The manifest and config are outside the clean source checkout. Parent launch
redirects stdout/stderr to the config's explicit 8TB files. Formal controls use
`mode=controls`; the complete scan then uses a separate config/ID/output/lease
with `mode=complete20`. Controls never scan actual raw. Complete20 must scan all
20 trials and conserve all 32 original request endpoint denominators.

Execution (only after root freeze/no-argument gate and coordination):

```
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 /8TB/env/bin/python -B \
  /8TB/projects/content_source/run_content_recount.py \
  --config /8TB/projects/CONFIG_FROZEN.json \
  --manifest /8TB/projects/CONTENT_SOURCE_v1.json \
  --out /8TB/results/new_exclusive_output
```

The exact original content function defines code-point occurrence introduction
and retraction, and posterior support compares the whole actual first displayed
text against the selected Canonical at that same row's actual G. It does not
substitute the target F, final text, final CER, or online certificate. Resident
adapters use each sid's original REQUEST_ORIGINS/ledger clock; original 500ms,
EOS, all offered, missing/unknown and deadlines are preserved.

Before continuity analysis the original c4 checker validates every full receipt,
durable fact, publication and actual Consumer snapshot. The new reader then
independently reconstructs full dependency paths. Complete cut equality at the
Canonical boundary decides compatible-ahead preservation; same text alone is
insufficient. It emits verified compatible events, necessary withdrawals,
piecewise observed same-source snapshot intervals, and complete-tip segments
that span compatible updates. A changed legal tip is supersession. Final tips
are censored at the last actual same-source observation. Failures to reconstruct
support fail the analysis instead of fabricating a zero-error result.

The time metric is logical Consumer state continuity under complete application
logs and the implementation's held-state premise. It is not browser/network
availability, human textual correctness, online G certification or a production
availability percentage. The total seconds of tip segments crossing compatible
events are a descriptive residence measure, not new deadline credit.
Internal ahead cuts with empty text have actual visible_frontier=0. Event and
segment outputs explicitly separate those from nonempty actual visible views;
nonempty residence and all-tip residence are distinct denominators.

Development controls:

```
python -B -m unittest discover -s SOURCE -p test_content_reader.py -v
```

They cover actual-G/F separation; unknown/mismatch; character occurrences;
full-state-compatible retention; false actual preservation; same text with a
different complete state; missing dependency path; independent request clocks;
missing EOS; dependency byte pins; and unknown/zero conservation.

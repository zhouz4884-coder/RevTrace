# RevTrace formal study: bounded TLC and parameterized TLAPS

Executed source: `996430d24d110facb242b352ba69c2f42f26e69c`.

The full study matched all **21** declared TLC outcomes: **10 positive checks** and **11 expected, named counterexamples**. TLAPS proved **20 obligations for 10 named conditional theorems**. These results are separate from tool-install smoke and development retries.

Read `formal_results/REPORT.md` and `formal_results/FORMAL_CLAIM_EVIDENCE.json` for the guarantees and limits. The main admission model has 175,980 distinct states; safety and fairness explore that same bounded graph, not two independent populations. Negative configurations deliberately omit rules or demand an unsupported completeness/deadline property. Their violations are not bugs newly measured in the current GPU implementation.

## Files

- `source_v5/`: exact executed TLA modules, 21 CFG files, protocol, failure history and CPU runner.
- `FORMAL_SOURCE_v5.json`: complete byte manifest and full execution commit.
- `FORMAL_SOURCE_v5.bundle`: standalone Git history, including failed development revisions.
- `formal_results/`: full_v5 source/config/log/counterexample records, four retained pilot versions, bounded raw index and independent result recount.
- `FORMAL_INDEPENDENT_SEMANTIC_AUDIT.md`: separate agent's read-only logical review. It did not rerun the prover or independently implement the specification.
- `FORMAL_TOOLING_RECEIPT.json` and `FORMAL_TOOLING_REPORT.md`: actual tools, binary/artifact hashes, installation failures and valid/invalid tool smoke.
- `verify_delivery.py`: portable, read-only package/source/log verification; no SSH or GPU.

Run locally:

```text
python -B verify_delivery.py
```

Reproduction uses the pinned Java/TLC and TLAPS described in the tooling report. Each new check must use a fresh result directory and record its source/config/environment hashes. The original large/internal TLC state databases and prover caches remain on the designated 8 TB disk; the bounded raw index explicitly excludes that engine scratch. All scientific stdout/stderr, frozen modules/configs and concrete negative traces are included.

## Scope that must survive manuscript use

Trusted selected output, immutable dispatched input, a fixed adapter, one Owner, successful persistence/intact storage and an actual ordered local Consumer are premises. No full Python/CUDA/OS refinement, arbitrary-graph completeness, unbounded service liveness, recognition-quality theorem, browser/network exactly-once claim or wall-clock deadline theorem is established.

The parameterized append proof is substantive but conditional on its explicit guard. The selection proof is an incremental maximum scan under fixed eligibility/frontier observations, not a new indexing algorithm. Historical receipt preservation does not grant permission to use that value in a new current input. The model's incomplete-selection negative does not classify every historically budget-capped ASR output as illegal. D1 text-render implementation remains a separate runtime obligation.

This local package adds no GPU measurement and does not alter the manuscript. `PACKAGE_MANIFEST.json` covers every delivered file except itself; successful packaging is distinct from proof scope and from GitHub publication.

# DSN evidence inventory, 2026-11-01

Start with [跨版本证据检索与补强取舍](DSN_EVIDENCE_OPPORTUNITY_REPORT.zh.md).

This directory records a read-only research review. It adds no new inference,
serving result, fault trial, formal run, or result recount. The v9 manuscript,
legacy checkout, historical failures and experiment-source pointer are preserved.

- [Evidence ledger](EVIDENCE_LEDGER.csv): 28 evidence/opportunity cards, with
  execution-contract limits and recommended placement.
- [Coverage](COVERAGE.csv): 36 experiment families plus five major evidence and
  manuscript directories. Coverage means entry-point and targeted evidence
  inspection, not complete raw-data revalidation.
- [Protocol and costs](PROTOCOL_COST_AUDIT.md), including early mechanisms and
  the S14 historical-view opportunity.
- [Feedback, failure and recovery](FEEDBACK_CAUSAL_AUDIT.md).
- [Scaling, resources and modern evidence](SCALING_RESOURCE_AUDIT.md).
- `REPORT_CATALOG.csv`, `REPORT_HEADINGS.json`, `CATALOG_STATS.json`: bounded
  Markdown lexical scan/hash deduplication; automated indexing is distinct from
  close reading.
- `FILE_INVENTORY.json.gz`, `FAMILY_INDEX.json`: initial filename inventory, not
  a claim that all files or mirrored archives were read.
- `PDF_INDEX.json`, `*_TEXT.txt`: identities and text extraction of the three
  author manuscripts; no new PDF visual acceptance claim.

The two helper scripts rebuild the Markdown/coverage indexes only. They do not
launch experiments, access a GPU, fetch remote raw logs, or change paper sources.
The initial filename inventory is retained as an input snapshot.
The directory-local Git attribute preserves audited bytes across Windows Git
line-ending conversion; publication checks committed blobs against local hashes.

Current recommendation: retain the R×S coordination story; strengthen the
separate-witness counterexamples, actual task consequences, accepted-result
lifetime, resource-release-to-service chain, and stratified opportunity ledger.
Investigate historical legal-view selection under a sustained-availability
objective before dismissing it using the old first-delivery-credit gate.
Current full-protocol cost attribution remains a real measurement gap.

Publication of this review does not submit or update a conference manuscript.

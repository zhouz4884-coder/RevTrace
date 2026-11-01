# Selective related-work delta

2026-11-01. Read-only manuscript comparison; no runtime, old TeX, data or result changes. Workflow: `nature-academic-search` citation-verification + reference-management. Academic-search MCP was absent from the available-tool catalog, so verification used the publisher/author primary sources directly. No citation metadata were sent to third-party bibliographic APIs.

## Recommendation

The initial recommendation was three entries in `CANDIDATE_COORDINATION_REFS.bib`. The user's subsequent explicit requirement is30+ references with substantive support and, if readable, a single reference page. The expanded recommendation is now exactly31: the current21, those three inference references, and the seven verified entries in `ADDITIONAL_REFS.bib` below. Keep all existing citation keys. Each addition has a concrete claim rather than serving as an uncited quota item.

The important nuance is **SGLang already performs API speculative execution as well as KV caching**. Its Section5 continues generation beyond a primitive's stop condition and reuses matching additional output for later primitives. The paper must acknowledge this rather than position SGLang as exclusively a cache manager. RevTrace's comparison concerns the complete recursive feedback input, original Correct/Update and actual whole-view application contract, without declaring these systems incapable of implementing it.

## Primary verification and claim anchors

| Entry / status | Primary bibliographic source | Mechanism anchor and allowed use |
|---|---|---|
| `kwon2023pagedattention`, verified title/authors/year/venue/DOI | [Author arXiv v1](https://arxiv.org/html/2309.06180v1), header; [publisher DOI](https://doi.org/10.1145/3600006.3613165) | Sections4.2–4.4: physical KV blocks can be shared; a shared prompt prefix can map to cached blocks. The reuse object is KV state with token-prefix dependencies. Do not claim only within-request reuse. |
| `zheng2024sglang`, verified all exported fields | [NeurIPS publisher page](https://proceedings.neurips.cc/paper_files/paper/2024/hash/724be4472168f31ba1c9ac630f15dec8-Abstract-Conference.html), [official BibTeX](https://proceedings.neurips.cc/paper_files/paper/27480-/bibtex), [official PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/724be4472168f31ba1c9ac630f15dec8-Paper-Conference.pdf) | Section3, PDF pp.4–5: token-sequence-to-KV mapping across calls/instances. Section5, pp.6–7: API speculative execution retains extra generated output for later primitive matching. Both are relevant precedents. |
| `leviathan2023speculative`, verified all exported fields | [PMLR publisher page and supplied BibTeX](https://proceedings.mlr.press/v202/leviathan23a.html), [official PDF](https://proceedings.mlr.press/v202/leviathan23a/leviathan23a.pdf) | Section2.1–2.3, PDF pp.2–3: approximate-model drafts are evaluated by the target model and accepted/resampled to preserve its distribution. This is token-level speculative sampling, rather than a guarantee about actual whole-view retention under recursive feedback installation. |

ACM full-page retrieval returned403. The vLLM author version itself confirms the SOSP2023 venue and DOI. The candidate BibTeX therefore omits an unverified page range; it does not guess one. NeurIPS BibTeX was served as `application/x-bibtex`, unsupported by the web renderer; a direct read of that same official URL supplied volume37, pages62557–62583, DOI and author order. No access restriction was bypassed. No external performance number is recommended or transferred into the RevTrace evaluation.

## Suggested paragraph,99 whitespace-delimited words including citation tokens

```latex
vLLM's PagedAttention shares KV blocks within and across requests, while
SGLang's RadixAttention reuses token-prefix KV state across program calls
\cite{kwon2023pagedattention,zheng2024sglang}. SGLang also speculates beyond
a call's stop condition and matches retained output to later primitives.
Speculative decoding verifies draft tokens against a target model while
preserving its output distribution~\cite{leviathan2023speculative}.
RevTrace studies complete calls in a recursively selected feedback task:
the eventual parent can confirm an already executing call's entire input,
while its original correction and update determine the result. A
separate whole-view witness governs what remains available when that
selected parent installs. These are complementary reuse and service contracts.
```

Suggested location: after the revisable-speech/speculation paragraph and before execution/authorization/recovery, or replace a repetitive distinction sentence there. No new comparison matrix or benchmark is required. The final two sentences are a bounded interpretation of the supplied RevTrace contract, not a claim found in the external papers.

Not selected: a separate SMR citation adds little while the current paper assumes exclusive Owner selection rather than contributing a replication protocol. Existing refinement, concurrency, RPC and write-ahead citations already anchor that machinery. Lease, runahead and SEDA references should be added only if the manuscript introduces a concrete corresponding claim; do not imply a lease-based validity proof or global admission policy that the implementation does not provide.

## Expanded requirement: seven further references, final total31

This section supersedes the earlier narrow recommendation. It supplies concise places for the existing systems foundations without expanding the runtime or evaluation. Orca replaces Silo: original OCC is already credited, whereas iteration-level transformer serving is directly relevant to the core carrier and was already read in `experiments/final_evidence_integration_20261028/RELATED_WORK_AUDIT.md` and present in the legacy `Paper_DSN/refs.bib`. The other six are primary-paper checks performed for this requested expansion, not retrospectively labelled as previously implemented RevTrace machinery.

| Key / primary reading | Concrete manuscript claim and short insertion | Boundary |
|---|---|---|
| `schneider1990statemachine` — [author's published survey PDF](https://www.cs.cornell.edu/info/people/fbs/publications/SMSurvey.pdf), pp.299–303; [author publication list](https://www.cs.cornell.edu/info/people/fbs/fullist.html) confirms CSUR22(4),299–319,1990 | The selected-program subsection can acknowledge ordered state-machine accounts of service execution before introducing its own selected-fact projection. | Single-Owner refinement does not implement Schneider's replicated agreement/order protocols; the original relation here may be nondeterministic. |
| `chandy1985snapshots` — [author-hosted published paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/Determining-Global-States-of-a-Distributed-System.pdf), pp.63–65; title/authors/TOCS3(1)/63–75/1985 printed | Global snapshots define coherent process/channel states; the local complete feedback cut is a different declared object. Add to recovery/state-scope comparison beside Flink. | Do not call the local neural-cut witness or WAL implementation a Chandy–Lamport snapshot protocol. |
| `gray1989leases` — [published paper PDF](https://www.cs.cmu.edu/afs/cs.cmu.edu/academic/class/15712-s12/www/papers/gray89.pdf), pp.202–203; printed interval202–210, authors Cary G.Gray/David R.Cheriton,1989 | Time-based cache leases grant limited-duration rights; our physical-ownership lifetime ends on terminal/drain evidence. A short sentence by physical release resolves the overloaded word lease. | Cary G.Gray is not Jim Gray. This paper is not a fencing-token or deadline-authorized-commit implementation here. |
| `berenson1995isolation` — [author-organization record](https://www.microsoft.com/en-us/research/publication/a-critique-of-ansi-sql-isolation-levels/) and [author PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-95-51.pdf), Section4.2; SIGMOD95 pp.1–10 is printed in the PDF footer | Snapshot-based reading and transaction commit guarantees differ. Extend the existing OCC/MVCC sentence to acknowledge snapshot isolation. | Snapshot isolation is not serializability; no database isolation level proves whole-view continuity. |
| `welsh2001seda` — [official SOSP paper](https://www.sosp.org/2001/papers/welsh.pdf), Sections1/3; [coauthor bibliography](https://people.eecs.berkeley.edu/~culler/papers/index-03.html) confirms SOSP2001,230–243 | Explicit queues and resource controls address overload. Add to discussion separating semantic eligibility from resource admission. | RevTrace does not implement SEDA's stage controllers, adaptive load shedding or a global fairness guarantee. |
| `zaharia2013dstreams` — [author paper](https://people.eecs.berkeley.edu/~matei/papers/2013/sosp_spark_streaming.pdf), Sections1/3/4; printed SOSP2013 DOI10.1145/2517349.2522737; author-paper bibliographies also confirm423–438 | Deterministic batches and lineage enable streaming-state recomputation. Add beside Flink/global-state recovery, then identify our verified selected-prefix replay. | Do not inherit D-Streams' latency, parallel recovery or deterministic-neural-rerun claims. Author copy notes minor related-work clarifications. |
| `yu2022orca` — [USENIX official page/BibTeX](https://www.usenix.org/conference/osdi22/presentation/yu), [official PDF](https://www.usenix.org/system/files/osdi22-yu.pdf), Sections2–3 | Iteration-level scheduling and selective batching address multi-iteration transformer serving. Add at the start of the inference-runtime paragraph. | The static row-complete core is not an author-stack Orca reproduction; no external performance figure is imported. |

All seven Bib entries have verified title, authors, venue, year and page interval. Historical ACM DOI landing pages returned403. For identifiers not independently confirmed in the readable primary version, the Bib entries omit the optional DOI field rather than guess; D-Streams' printed DOI is retained and Orca's official Bib supplies no DOI. No third-party bibliographic API was used and no access check was bypassed. Published paper content and author/publication records supplied the claims. There are no direct quotations in these proposed insertions.

### Compact optional comparison paragraph

```latex
State-machine accounts relate service execution to ordered commands
\cite{schneider1990statemachine}; snapshot isolation distinguishes read
snapshots from transaction guarantees~\cite{berenson1995isolation}.
Distributed snapshots capture process/channel state
\cite{chandy1985snapshots}, while D-Streams recover deterministic streaming
computations through lineage~\cite{zaharia2013dstreams}. RevTrace binds
local feedback inputs and replays verified selected facts, with a separate
witness for provisional views. Its terminal/drain-based physical ownership
differs from time-bounded cache leases~\cite{gray1989leases}.
Orca addresses iteration-level transformer scheduling~\cite{yu2022orca};
SEDA uses queues and resource controls to condition load
\cite{welsh2001seda}. These execution, recovery and admission mechanisms
provide context for the distinct question of which completed or in-flight
work remains eligible after selected feedback changes.
```

Use this as distributed short insertions at the mapped locations if a single paragraph overloads Related Work. One technical-page-friendly option is to attach Berenson to the existing concurrency sentence, Schneider to the selected-program view, Gray to physical ownership, SEDA to admission, and put only the Chandy/D-Streams comparison in Related Work. Retain complete standard publication information; a single-page reference goal should be satisfied through standard formatting and optional URL verbosity, not smaller fonts or shortened titles/author identities.

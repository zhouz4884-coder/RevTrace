# Formal-publication substrate check: overload and duplicate recovery

Workflow:formal-paper discovery plus citation verification; academic MCP absent,
public Crossref T1/API and publisher/conference/author primary sources used.
Default sandbox preflight failed withWinError10013; authorized network preflight
reached3/3endpoints. No preprint result selected. Metadata JSON and hashes are
in crossref_v2/VERIFICATION.json; this is not a claim all full texts were read.

## SEDA (SOSP2001)

Matt Welsh, David Culler, Eric Brewer, “SEDA:An Architecture for Well-Conditioned,
Scalable Internet Services,” SOSP2001,pp230–243. Conference
[DOI10.1145/502034.502057](https://doi.org/10.1145/502034.502057).
The SIGOPS issue manifestation10.1145/502059.502057 is the same article, not an
additional distinct reference. Crossref splits the title as `SEDA` plus subtitle.

What is already provided:explicit stages/queues and resource controllers to
condition overloaded services. Therefore queue observability, load shedding,
staged execution and generic overload response are not RevTrace inventions.
Use SEDA as a credited foundation, not a weak or irrelevant baseline.
Primary confirmation:[ACM record](https://doi.org/10.1145/502059.502057),
[author's publication list](https://people.eecs.berkeley.edu/~brewer/papers/).

## Adaptive Overload Control (USITS2003)

Matt Welsh and David Culler, “Adaptive Overload Control for Busy Internet Servers,”
formal USENIXUSITS2003 paper. [Official full-text HTML](https://www.usenix.org/legacy/event/usits03/tech/full_papers/welsh/welsh_html/usits.html).
Sections2.3/3.2/3.4 explicitly cover per-stage admission, response-time feedback
and application-specific degradation. Thus “we combine admission with degradation”
or “we use observed latency instead of static capacity” alone is not a novelty
argument. The proposed RevTrace difference, if validated, is preserving the
application's certified-state/actual-view/accepted-input obligations across those
actions. Comparison must keep ordinary queue/expiry and equal-limiter controls.
The official account also separates server response effects from network effects;
our local Consumer must not become a browser/network guarantee by wording.

## RIFL (SOSP2015)

Collin Lee, Seo Jin Park, Ankita Kejriwal, Satoshi Matsushita, John Ousterhout,
“Implementing Linearizability at Large Scale and Low Latency,” SOSP2015,pp71–86,
[DOI10.1145/2815400.2815416](https://doi.org/10.1145/2815400.2815416).
Publisher direct-open returned403; Crossref formal metadata and the
[official SIGOPS proceedings PDF](https://sigops.org/s/conferences/sosp/2015/current/2015-Monterey/printable/126-lee.pdf)
confirm identity and abstract-level scope without bypassing authentication.

Reusable exactly-once RPC handling and recoverable completion metadata are
established mechanisms. Our durable request identity must not be claimed as a
new exactly-once primitive. RevTrace specifies what selected model projection,
input frontier and rendered fact may become/recover state, using conventional
persistence/dedup components. It does not inherit RIFL's distributed-linearizability
guarantees, data-migration coverage or metadata-GC design from a citation.

## Writing/claim consequences (not manuscript edits)

1. Do not assert conventional composition cannot express the contract; the
   complete Standard and correct reservation-reconstruction positive controls
   already disprove that blanket claim.
2. Keep the application's two permission domains and the actual causality/view
   obligations central. Each claimed increment needs its own guard witness,
   observed outcome, assumptions and fair control rather than an algorithm name.
3. CDE performance superiority remains unproved while independent105 runs are
   incomplete. State-machine names alone are neither a new algorithm nor value.
4. Exactly-once admission is not exactly-once external display. Successful ledger
   replay is not measured user-service RTO; persistence is not recognition truth.

These are substrate distinctions for the final evidence-backed candidate, not
a rewritten title/abstract/body or an exhaustive prior-art priority claim.

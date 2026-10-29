# RevTrace coordination protocol

Conclusion: certified-state installation, legitimate provisional progress, and
physical executor release are three different transitions. Their coordination
allows useful progress without granting provisional work canonical authority.

Panel a shows actual Authority selection entering the protected WAL/Canonical
path. Installed (F,P) feeds compute-retention R and the independent certified
Consumer lane. Private whole views go directly to the Consumer: S may retain a
compatible whole provisional view independently of whether R retains future
computation. The diagram must not imply that S requires R to be enabled.

Panel b shows the exercised coverage exit condition and request/observation/
terminal/drain/release sequence. RowComplete and RowCancelled are alternative
terminals. RowComplete may be delivered before all rows end; neither terminal
alone releases the physical lease. A cancellation request may race completion.

This diagram describes actual f0 execution-source mechanisms, not the proposed
native candidate handoff or an oracle/new system. Native application adapters
have their own state contract and do not inherit all f0 fault guarantees.

Export: fixed 7.15 inch width, all text at least 8 pt, PDF/SVG/350 dpi PNG,
editable SVG text, embedded TrueType PDF fonts (no Type 3), full-page PDF PNG.
QA checks the full page, all text extents and the containing card extents.

# Current RevTrace DSN manuscript — 2026-10-31 (v2)

- [Complete manuscript PDF](revisions/20261031_dsn2027_release_v2/main.pdf)
- [Main LaTeX source](revisions/20261031_dsn2027_release_v2/main.tex)
- [Audited anonymous source package](revisions/20261031_dsn2027_release_v2/RevTrace_DSN2027_anonymous_source_v2.zip)
- [Research decisions and final results](../experiments/dsn_strengthening_20261031/FINAL_RESEARCH_AND_PAPER_REPORT_20261031.zh.md)
- [Source, PDF, package and all-page QA record](../experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v2.json)

Title: **RevTrace: Preserving Valid Progress across Trusted Feedback Revisions**

11 technical pages plus one references-only page; 131-word abstract; 21 cited references; three figures and three tables.
All twelve pages visually reviewed. All23 fonts embedded, no Type3, no undefined references or overfull boxes.
The package contains exactly the reachable manuscript sources, figures, selected bibliography, provenance and PDF; build logs, local QA files, audio and models are excluded.

Matched normal regression:32actual trials/544original transitions; final4f Full-call6/8 whole-run passes versus0/8 conservative, credit65.821625 versus30.0 of66.33975audio seconds. Earlier BDFA8/8 retains its own source.
Resident models:4trials/16 independent EOS requests/272original transitions, Full-call7/8 versus0/8; credit64.118875 versus31.0. Single-outstanding closed-loop, not continuous-recording or capacity validation.
Controlled complete-buffer death:2matching cases reuse original UID/birth/inc after physical producer exit,2wrong-input cases reject; positivecases complete a next request. Original audit/CLI failures remain failed; separately frozen zero-NN reconstruction verifies unchanged raw mechanisms.
Actual-dispatch audit and a bounded two-client opportunity probe retain all negative boundaries. The extra probe is NO-GO; no new admission controller was introduced. Old no-reset long quality and cold-recovery deadline failures remain explicit.

Old20261008/20261029/20261030 revisions are preserved. Actual NN, controllers, fixtures, checkers and evidence-archive commits are separately recorded.
This is a complete research manuscript release; conference submission has not been performed.

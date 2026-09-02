# TC pre-submission checklist

Official references:

- TC scope: https://www.computer.org/digital-library/journals/tc/call-for-papers-general-submissions
- IEEE Computer Society author guidance:
  https://www.computer.org/publications/author-resources
- IEEE AI-use policy:
  https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/

## Scope and article type

- [x] Target: *IEEE Transactions on Computers*.
- [x] Article type: Regular Paper.
- [x] Current IEEE Computer Society guidance states that TC does not offer a
  double-anonymous-review option; author names and affiliations therefore
  remain in the manuscript and portal metadata.
- [x] Scope framing: runtime systems, parallel accelerator execution, and
  computer-system performance/reliability.
- [x] Empirical boundary: revision-generative ASR on Qwen3-ASR and Whisper;
  there is no claim of a new accelerator, GPU kernel, datacenter deployment, or
  multi-node system.

## Page and format gate

- [x] Final compiled manuscript is **at most 12 formatted pages**, including
  references and author biographies.
- [x] Abstract remains between **100 and 200 words**; current metadata abstract
  is 182 words.
- [x] IEEE journal template is used and the paper compiles without blocking
  warnings, undefined references, or missing figures.
- [x] Figure captions are below figures; table captions are above tables.
- [x] Figures remain legible at final single- or double-column size and have no
  internal experiment-phase or gate labels.
- [x] References use IEEE numeric style and every retained reference supports a
  claim in the compressed manuscript.
- [x] Final PDF, source, cover letter, metadata, artifact README, and figures
  use one frozen set of metrics: 1.39×/1.28× matched-workload throughput;
  up to 6.88× wall-clock speedup; 800 Qwen events; 1,048 Whisper commits;
  250,000 fuzzer attempts; and 157.8×/111.7× V100 audio real-time throughput.

## AI-use declaration

- [x] The manuscript identifies OpenAI ChatGPT and limits its role to language
  polishing and writing assistance.
- [ ] Authors confirm the final disclosure wording and its placement in the
  Acknowledgment section.
- [ ] If the portal asks a separate AI-use question, answer consistently with
  the manuscript; do not broaden or minimize the stated use.

Recommended wording:

> OpenAI ChatGPT was used solely for language polishing and writing assistance
> throughout the manuscript. The authors reviewed and edited all outputs and
> take full responsibility for the article.

IEEE generally treats editing and grammar enhancement as outside mandatory
AI-content disclosure, while recommending disclosure; generated manuscript
content requires disclosure. Keeping this statement is the conservative and
internally consistent choice for the declared use.

## Data and code availability

- [x] A whitelisted reviewer artifact contains source code, frozen selected raw
  results, audit scripts, and a SHA-256 manifest.
- [x] The manuscript does not falsely describe the authenticated repository as
  publicly accessible.
- [x] The manuscript promises a public archive upon acceptance.
- [x] Third-party benchmark datasets remain governed by their original licenses
  and are not redistributed in the reviewer artifact.

## Funding and acknowledgment

- [ ] All authors confirm that there is no grant or external funding source to
  report.
- [x] Acknowledge the High Performance Computing Platform of BUCT as computing
  support, not as an invented grant or external funder.

## Final portal checks

- [ ] Update the date on `TC_COVER_LETTER.md` if submission occurs after
  3 September 2026.
- [ ] Upload the editable LaTeX source and a matching PDF as required by the
  active portal.
- [ ] Enter the exact title, abstract, index terms, author order, and affiliation
  from `TC_SUBMISSION_METADATA.md`.
- [ ] Complete the ORCID actions in `TC_AUTHOR_ACTION_CHECKLIST.md`.
- [ ] Select traditional or open-access publication deliberately; do not assume
  an APC is required for a traditional submission.
- [ ] Download and inspect the portal-generated PDF before final approval.
- [ ] Verify equations, figures, tables, references, Unicode symbols, and author
  metadata in the generated PDF.

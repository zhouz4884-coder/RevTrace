# Changes from v25 to v26

- Replace Figure 4 with the current eighty-trial native workload used by Table V.
  The plot now compares Serial, Ready-only and RevTrace under the same whole-view
  policy, eight speakers and two fresh-process repeats each.
- Plot sourcewise dual-deadline audio coverage and both-board service energy per
  offered audio-second. Filled points pool repeats; open points and short ranges
  show both observed repetitions. Shapes distinguish policies in grayscale.
- Place the native comparison on page 9 beside its main results and table.
- Use a shared speaker order and descriptive labels instead of the old pilot/
  confirmation markers. Include the non-speculative Serial anchor so the reader
  can assess both completed-result reuse and in-flight retention.
- Tie the sourcewise energy statement explicitly to Ready-only. Place the older
  repeated-execution result with the AISHELL results, before the second corpus;
  remove the obsolete pilot-bank sentence accompanying the old figure.
- Align the older/current display-miss order (20 versus 19) with the
  older/current credit order in the repeated-execution sentence.
- Preserve the original v25 PDF and source archive. No new GPU experiments.
- Twelve pages: eleven technical plus one references; no overfull boxes or
  unresolved references. The normalized anonymous source recompiles with every
  page text- and raster-identical to the supplied updated PDF.

# Changes from v24 to v25

- Add a second natural corpus, and let the certification deadline bind.
  Four complete MAGICDATA Mandarin test utterances of 14.396--15.232~s
  (lexicon-first four of 29 metadata-qualifying speakers, frozen before
  any transcript is read) run under the same two FP32 workers, task path,
  500-ms inputs, 2-s horizon and $D_2/C_8$, three policies twice per
  speaker: 24 cells over 119.844 audio-s and 244 frontiers per policy.
  Serial execution misses $C_8$ 27 times, at up to 11.508~s; both
  retaining arms miss it zero times, at 6.962 and 6.473~s. All 27 are
  also $D_2$ misses, so the gain is a deadline met rather than new
  $A_{2,8}$ intervals.
- Separate the two retentions where credit cannot. Both retaining arms
  earn 65.29275 audio-s against 38.000 for serial execution, identical to
  the last digit, while computation-only clears five compatible ahead
  views that joint retention keeps and removes 2.500 audio-s of supported
  display. The AISHELL comparison separated the arms by 1~s of credit;
  this one separates them only by availability.
- Price the result on the new corpus. Serving earlier costs 35.3\% more
  worker time and 13.3\% more two-board energy than serial execution, so
  the v24 energy reduction is a property of the AISHELL working point
  rather than of the mechanism.
- Retitle and reposition the native confirmation. The new Section V-D
  states where longer inputs make the deadline bind; Section V-C now
  closes by noting that the 8--9-s bank never does. The old
  cross-campaign reproduction paragraph is compressed to one sentence,
  because the new corpus is the stronger external confirmation. Fig. 5
  moves after the new subsection so the text is not split by the
  two-column float.
- Abstract: the closing sentence reports 27$\to$0 certification misses on
  15-s natural inputs in place of the whole-run pass counts and the
  reference-agreement statement. 145 words, under the 150-word limit.
- Cite MAGICDATA (OpenSLR 68). 35 references, all cited, no unused entry.
- Page budget unchanged: 11 technical pages plus one references page, no
  overfull or underfull box. Space came from compressing the
  cross-campaign, 16-session, UIR and credit-reversal paragraphs, the
  conclusion, and two defensive tails.

# Changes from v23 to v24

- Correct one arithmetic value. The two-board energy reduction against
  completed-result reuse is 23.7%, from $(117825.874-89847.958)/117825.874
  = 0.23745$, not 23.8% (a round-then-subtract slip). Abstract,
  introduction and Section V-C now agree. The 31.8% worker and 7.4%
  serial-energy figures were already correct.
- Withdraw an unreported arm. The setup no longer advertises Whisper
  base.en as a second adapter. That stratum exists (15 primary cells) but
  all four retention arms sit within 0.28 points (426.0--428.0 of
  714.110 audio-s, 0--2 withdrawals) and below the no-retention anchor,
  because the adapter is a hard-cut 2-s streaming retrofit whose outputs
  show repetition degeneration. Reporting it would advertise a second
  recognizer that says nothing about the mechanism. The citation moves to
  Section VI, where it belongs to the recognizer that Whisper-Streaming
  makes incremental; cited count stays 34.
- Report the class rate, not only its duration. Avoidable withdrawal now
  appears as 3.5 per 100 offered frontiers here and 4.6 in the core study
  (17/368), so the native result reads as the same class at a shorter
  interval rather than as a smaller effect: what differs is the loop rate
  the erased interval spans. Section V-B carries the core rate so the
  comparison is traceable.
- Attribute the deadline. No arm misses C8 in any of the 80 native runs,
  so every Table V miss is a display miss; the dual deadline is now a
  measured statement about which bound binds, not an assumed pair.
- Reclaim the four added lines without touching evidence: Section VII
  drops a restatement already made in Section VI, the conclusion merges
  its closing clause and compresses one, and Section V-C drops a
  rhetorical sentence. Pages stay 11 plus references.

# Changes from v22 to v23 (superseded energy figure: 23.7%, see above)

- Repeat both retention switches in the native system. A new campaign ran
  five policies over the same eight AISHELL-1 speakers and two fresh
  repeats each, 80 cells with no cell filtered: Conservative 55.500 s and
  40.26%, $R_0S_0$ 58.000 and 42.07%, $R_0S_1$ 58.500 and 42.43%,
  $R_1S_0$ 130.960 and 94.99%, $R_1S_1$ 129.960 and 94.27%. Table V now
  reports all five arms with worker time and energy, and the section
  answers what each switch contributes instead of whether retention beats
  reuse.
- State the native factorial effect and its limit. At fixed view
  retention the call is worth 71.460 audio-s, at fixed call retention the
  view is worth $-1.000$ audio-s, and the interaction is $-1.500$
  audio-s. Both simple effects on the call are 8 of 8 in sign with a
  paired diagnostic of $2/256=0.0078$; the interaction is not
  established as positive, so the text claims classification rather than
  a credit synergy.
- Measure native continuity in the main experiment. Removing the view
  clears all ten compatible ahead views that retained calls meet, in ten
  windows of 32--134 ms (median 63), removing 5.000 audio-s of supported
  display and leaving 0.379 audio-s times s of avoidable absence. Joint
  retention clears none of them and keeps the two views that later
  feedback refutes, from S0902 in both repeats. All 39 loss windows
  return within the same root, none censored or truncated.
- Separate the resource trade from a dominance claim. Against reuse,
  retention uses 31.8% less worker time and 23.8% less two-board energy;
  against serial execution it spends 12.6% more worker time for 7.4% less
  energy, because it serves the same stream earlier.
- Locate the baseline honestly. Ready-only reuses the one complete result
  that was ready before its deadline (S0907) and sits 3.000 audio-s above
  no speculation at 65% more worker time, so its margin prices readiness
  rather than a fencing rule.
- Correct the reproduction statement. The earlier native campaign
  measured 129.460 audio-s where this one measures 129.960, so "recurs
  exactly" became "recurs within 0.500 audio-s", with 10/16 whole-run
  passes in both and 19 versus 20 D2 misses.
- Disclose where the native view effect comes from: three of the eight
  sources meet compatible ahead views under retention, and five meet
  none.
- Delete redundant text to hold eleven pages: the earlier three-arm
  Conservative pilot paragraph, two sentences in Section V-B already
  implied by Table III and $I$, the duplicated handover count and the
  now-false statement that every native policy keeps the whole-view
  check, and four lines of Related Work and Discussion.

# Changes from v21 to v22

- Put the zero-speculation baseline back into the native comparison. A
  Conservative arm already exists in the campaign that reproduced
  Fullcall's aggregate, on the same eight sources, reference, frontier
  count and credit definition: 56.000 s, 40.62%, 0/16 passes, against
  58.500 s and 129.460 s. Table V now has three rows, and the text draws
  the conclusion the ordering supports: completed-result reuse is worth
  2.500 s (1.81 points) over serial execution while in-flight retention
  is worth 73.460 s (53.28 points), so a fencing rule cannot explain the
  gap. The same campaign metered Conservative at 95.26 kJ against
  Fullcall's 90.28 kJ, which makes the energy reduction hold against
  serial execution as well as against reuse. Conservative's work and
  energy cells are dashes because that arm was not instrumented on the
  same two windows.
- Add a measured continuity column to Table III. Gap is the time integral
  of audio-seconds removed from an already-displayed view and not yet
  restored: 15.458 for snapshot, 0.258 for view-only, 30.258 for
  computation-only, 0.000 for joint. The total/avoidable columns are
  merged into one cell to keep the table height unchanged, and the text
  states that the gap spans both classes, so the 0.26 residue of
  view-only is its single necessary withdrawal.
- Report the withdrawal rate on the natural workload instead of relying
  on one 2.176-s case: 12 withdrawals on 368 offered frontiers (3.3 per
  100) in all three cohorts, removing 10.5 s of displayed audio and
  keeping it unavailable for 15.5 audio-s times s. Figure 1's case is
  stated to be a sample of that distribution.
- Separate the proof from a bit-exactness premise it never needed.
  Proposition 1 requires the appended edge to be the one the original
  program produced on its frozen input, which the contract's
  nondeterministic relation already permits; the runtime supplies that
  premise through per-incarnation identity and a reference comparison on
  all 32 native runs.
- Name what the native comparison prices. Every native policy keeps the
  whole-view check, so that study measures `R` against two non-retaining
  baselines and the factorial supplies `S` at fixed `R`. The abstract and
  introduction now carry the three-point coverage comparison, and the
  abstract states the resource reductions relative to completed-result
  reuse.
- Scope the contract to a closed, serializably comparable call boundary
  in the Discussion, and note that numerical cross-call state such as a
  reused KV cache needs an approximate or prefix-matched witness first.
- Remove three redundant objects to hold the page budget: the
  reuse-mechanism table (duplicated by the three obligations in the
  Discussion), the synchronous-footprint table (its three ranges are
  already in the text), and one positive-control sentence (Table IV
  already gives the per-cohort evidence). Tighten the LA2-CP, pilot,
  16-session and related-work passages and four figure captions.

Body is 11 pages plus one references page; 34 references, no overfull
box, no Type 3 fonts, four vector figures. The abstract is 147 words.
`REVIEW_RESPONSE_v22.zh.md` records the verification behind each decision,
the claims that did not survive checking, and the one native ablation
that still needs GPU time.

# Changes from v20 to v21

- State the factorial result as two withdrawal classes rather than as a
  credit interaction. Necessary withdrawals are absent in both arms that
  retain computation and present in both that do not (six and one);
  avoidable withdrawals are absent in both arms that retain the view and
  present in both that do not (six and seventeen). Only the joint arm is
  empty in both. The interaction in credited audio is kept, but as the
  service-level shadow, with one sentence stating that a credit total
  aggregates a run while a withdrawal is classified at one application.
  The "sign change" framing and the sentence claiming that `S` acts only
  at canonical application are removed, because the two together read as
  a contradiction with the 25.68 s credit difference between the two
  `R_0` arms.
- Add a 24-cell fault matrix to Section IV: zero illegal installs and zero
  accepted mutations across six conditions and two policies; worker
  faults recover in 1.8--2.3 s and Owner-group faults in 64.6--108.1 s;
  and the one condition where retention is worse (Owner failure after the
  durable install: 101.8--104.4 s and 26.5--27.2 kJ against 83.9--87.1 s
  and 22.4--24.2 kJ). The text states that no fault cell meets its
  deadlines, so the trials establish the absence of an illegal transition
  and a bound on recovery, not continued timeliness.
- Align the abstract and the introduction with the two-class result. The
  opening sentence now reads "deliver text within its display deadline,
  then erase it when a trusted revision confirms the screen", which puts
  the agreement where the paradox is. Eight words are added to the
  abstract and fourteen are cut elsewhere; it remains 139 words, 144 when
  hyphenated compounds are split.
- Drop the 49 before-corrector exits from the six-policy pilot, because
  the 49 and nine counts do not partition the 56 reissues and the pairing
  invited an arithmetic reading. The nine late refusals are kept and
  turned into the mechanism sentence they support.
- Mark the permutation diagnostic as the smallest value attainable with
  eight sources, and say that credit "gives up" rather than "costs" 3.60
  points in the Fig. 3 caption.
- Reword the credit reversal in Section V-F: credit moves with the timing
  of every offered interval, while which class each factor removes does
  not.
- Describe the AI contribution as drafting and revision "including the
  exposition of the refinement argument".

Body is 11 pages plus one references page; 34 references, no overfull
box, no Type 3 fonts, four vector figures. `REVIEW_RESPONSE_v21.zh.md`
records the review, the verification behind each decision, and the three
claims that were checked and deliberately left out.

# Changes from v19 to v20

- Anchor the retention interaction in the withdrawal column, which is
  classified at each Consumer application and is therefore comparable
  across arms: computation retention adds 11 avoidable withdrawals, and
  view retention removes all 17 where that computation exists but only
  six where it does not. Credit is now stated as the service consequence
  rather than as the mechanism. The sentence claiming that the `S` factor
  "does not gate first publication" is removed, because it contradicted
  the measured 3.60-point coverage difference between the two `R_0` arms.
- Translate completed-result-reuse coverage into service terms: the
  policy leaves 79.4 s of the 137.864 s offered stream without a timely
  certified display.
- Use "frontier withdrawals" in the abstract, matching the column and
  axis labels used in the evaluation.
- Move the "View only" label in Fig. 3(a) clear of the dotted factor
  arrow. The figure's PDF and SVG were patched directly because
  Matplotlib is unavailable in this environment; `figures/render_v16.py`
  now records the coordinates that were applied, so a later redraw
  reproduces them.
- Compress three evaluation passages that restated a robustness number
  (the alternative optimal alignment, the bootstrap denominator, and the
  undefined "96 trial--rule rows"), and tighten the AI-usage statement,
  to hold the 11-page budget.
- Correct number agreement in the conclusion.

Body is 11 pages plus one references page; the abstract is 139 words
(144 when hyphenated compounds are split); 34 references, no overfull
box, no Type 3 fonts, four vector figures.

# Changes from v17 to v18

- Lead with joint preservation of valid computation and supported views.
  Replace the pooled performance-band claim with the separate factorial
  and native comparisons.
- Restore three-cohort factorial interactions and the descriptive
  sourcewise bootstrap, with their original deadline metric.
- Add the observed ranking reversal: higher first-delivery credit can
  coexist with missing previously credited progress at the read point.
- Use the earlier 20-of-92 original-call observation to explain why
  confirming an input does not select that call's tentative successor.
- Connect the durable-prefix argument to two actual post-sync recovery
  cases, retaining original fact identities and Consumer use.
- Add complete commit, filesystem-sync and Consumer path footprints in
  a small table whose inclusive operations are explicitly non-additive.
- Retain the native paired comparison, resource reductions and actual
  task-reference checks; correct the interpretation of sampled shadow
  predicates, timing reversals and the fixed-lag control.
- Correct the AlignAtt citation to Interspeech 2023. Remove the unused
  end-to-end citation and abbreviate two conference names using their
  standard acronyms. All 34 retained references are cited.
- Move the unchanged mechanism figure to page 3, next to the object and
  protocol explanation. Preserve all four vector figures and their
  measured numeric inputs.
- Replace defensive summaries with the evidence, action or implication
  that advances the argument. Preserve the assumptions defining the
  original program and failure model.

No new GPU experiment or scientific execution was introduced. The v17
release remains a separate frozen snapshot.

## Additional v18 amendment

- Put all four factorial arms in one table with timely audio credit,
  total withdrawals and avoidable withdrawals; report direct cohort
  gains alongside the interaction contrasts.
- Distinguish view retention at canonical application from gating the
  first publication of provisional results.
- Reconcile the ranking-reversal credit ledger and its two withdrawn
  intervals using one-time first-delivery accounting.
- Restore aggregate cross-runtime repeatability with the changed
  interval classifications and their cancelling audio-credit deltas.
- State the selected-transition guarantee directly and distinguish
  recorded shadow predicates from actual model-active handovers.
- Add operating-scope interpretation and label the separate test families.
- Retain only manuscript releases v15 through v18 in active revision
  directories. Scientific evidence and Git history remain separate.

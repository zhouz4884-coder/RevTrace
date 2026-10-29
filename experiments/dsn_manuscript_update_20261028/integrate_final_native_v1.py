"""Integrate the completed independent new-speaker result without mixing evidence scopes."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
I=R/'experiments/dsn_streamcorrect_independent_20261029'
s=json.loads((I/'FINAL_PRIMARY_RESULTS_v2/SUMMARY.json').read_bytes())
assert s['status']=='PASS_COMPLETE_16_CELL_INDEPENDENT_PAIRED_RECOUNT' and s['all_original_full_C_ID_state_quality_preserved']
assert s['aggregates']['two_full_spec_early']['credit_samples']==1061436
assert s['paired_credit_wins']==8 and s['aggregates']['two_full_spec_early']['whole_run_D2_C8_pass']==8
target=R/'Paper_DSN/revisions/20261028_dsn2027_progress/sections/05_native_retention.tex'
target.write_text(r"""% Complete service evidence; component, development and independent scopes stay separate.
\subsection{Native correction with the original selected task}
\label{subsec:native_retention_eval}
We retain StreamCorrect's published recognizer, learned correction, and
feedback update~\cite{vu2026streamcorrect}, using the fixed 500-ms, no-VAD
adaptation and original FP32 execution. Both compared policies have two
protected full workers, the same ASR early-view Consumer, and identical
neural warmup. Conservative execution waits for selected parent feedback
before starting the next call; full-call retention confirms conditional
calls as in Section~\ref{subsec:native_full_calls}.

\paragraph{Development and frozen confirmation}
Component controls cover all 69 steps of four AISHELL-1 utterances used
for implementation development~\cite{bu2017aishell}: 65 complete ASR
packets reproduce original $C/U$, with four buffer-only steps using the
original path. Thirteen identity-projected ends differ from selection
without invalidating that candidate input. Comparison with the earlier
implementation removes only its added implementation-contract tag;
complete task state, corrections, and returned IDs remain equal.

A three-arm source-0 pilot gives conservative execution, already-ready
ASR handoff, and conditional full calls 3.0, 6.5, and 8.0~s of original
credit over 8.068~s offered. Full calls can retain work still executing
when its input is confirmed; ready-only handoff requires a complete
received packet. We select our full-call implementation and confirm it
with 16 runs on all four development sources. These are development
measurements, including two 0.068-s EOS misses, rather than independent
acoustic evidence.

We then freeze that method before selecting four previously unused
AISHELL-1 speakers using archive metadata and an 8--9-s duration band.
All four initial selections remain; no model output selects a source.
The final experiment has four separate chains, two fresh-process repeats,
and two policies: 16 runs. Paired arm order reverses on the second repeat,
GPU roles swap, and pair blocks are randomized. The independent acoustic
unit is a speaker, not a repeat or offered frontier. All original
500-ms frontiers and partial EOS intervals stay in the denominator.

\paragraph{Task fidelity and timely service}
Offline original full calls supply 68 reference transitions, separately
from service timing. All 272 transitions in the new experiment reproduce
their complete original start and end states, $C$, and returned IDs,
including the implementation tag. Both arms have five character edits
over 81 unique reference characters, or 6.17\% CER; across repeated flows
the equivalent count is 10/162. This measures the adaptation, not the
published author's benchmark CER. Development runs separately preserve
all 276 transitions and have 16/182 repeated-character edits.

\begin{table}[t]
\centering
\caption{Native service: eight runs per arm in each panel. Offered audio
per arm is 66.430~s for development and 66.340~s for independent sources.
Credit and energy are totals; C50 is the median of per-run C50 values.
Text support compares the first actual whole view at $G$ with later
complete Canonical text at exactly $G$. Values are rounded.}
\label{tab:native_full_confirm}
\small
\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{@{}lrrrrr@{}}
\toprule
Policy & \shortstack{Credit\\(s)} & \shortstack{Text\\support (s)} &
\shortstack{C50\\(s)} & \shortstack{Energy\\(kJ)} & Pass\\
\midrule
\multicolumn{6}{@{}l}{Development: four existing sources}\\
Conservative & 37.500 & 33.500 & 1.905 & 36.942 & 0/8\\
Full-call & 66.294 & 56.288 & 1.035 & 32.050 & 6/8\\
\midrule
\multicolumn{6}{@{}l}{Independent: four new speakers}\\
Conservative & 37.000 & 29.000 & 2.115 & 35.801 & 0/8\\
Full-call & 66.340 & 51.518 & 1.203 & 31.815 & 8/8\\
\bottomrule
\end{tabular}
\end{table}

Table~\ref{tab:native_full_confirm} keeps development and independent
results separate. On new speakers, credit increases in all eight pairs,
from 37.0 to all 66.33975~s offered per arm. All four speakers have a
positive two-repeat sum, satisfying the frozen directional rule; this is
not an eight-independent-sample significance test. Full-call retention
passes whole-run D2/C8 in 8/8 runs, versus 0/8. Its D99 ranges from 0.837
to 1.663~s and C99 from 1.090 to 1.929~s. It has no D2 or C8 miss;
conservative execution has 62 D2 misses, including eight EOS intervals,
and no C8 miss. The median per-run C50 falls from 2.115 to 1.203~s.
Both-board serving energy, excluding loading and fixed neural warmup,
falls 11.13\%; credit, C50, and energy improve in every pair.

\paragraph{Retained work and visible content}
Ninety-two promoted calls are actually computing before their selected
parent finishes, and their model intervals overlap the parent's. Twenty
have their own identity-predicted end differ from original correction.
Twenty-four known-invalid inputs stop after ASR and before $C/U$; two
already-completed conditional full results are discarded. None changes
the original selected history. These observations distinguish input
confirmation from requiring each future prediction to be correct.

The new runs also contain a concrete whole-view witness: one Canonical
application advances from 4.0 to 4.5~s while retaining a supported 5.0-s
Private view and its original executing call. Two other applications,
on one speaker's two repeats, withdraw 6.0 to 5.5~s because the call's
complete predicted input disagrees with the actual selected state;
the two complete conditional results are not installed. These natural
events illustrate compatible retention and necessary withdrawal, not
another factorial estimate of the $R\times S$ interaction.

Posterior whole-text support remains separate from original credit.
Supported credited audio increases from 29.0 to 51.518125~s in all eight
pairs; raw and whitespace-only comparisons agree and unknown coverage
is zero. The remaining 14.821625~s of full-call credit does not have this
support. Six of eight first EOS texts differ from later Canonical text
in each arm. These are selected-model comparisons, not human correctness
certificates. Both arms introduce 180 LCP-versioned codepoint occurrences,
retract 14, and end with 166 across eight flows. Unchanged-text rows first
cover 10.0 versus 17.0 credited audio seconds; processing-frontier credit
does not count newly transcribed characters.

An earlier two-source capacity experiment retains its negative result:
retention earns 17.0~s versus 18.5~s for independent full replicas, using
47.991 versus 25.949~kJ. Its warmup and Consumer differ. The present
single-chain comparison establishes a service opportunity in this scope;
it neither supplies a causal before/after comparison nor establishes
superior saturated multi-source capacity.
""",encoding='utf8')
print('Integrated new4 strict task fidelity and original service/content endpoints.')


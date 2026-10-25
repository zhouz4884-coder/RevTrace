# V6: bounded Fine-anchored evidence choice, not a new safety contract

## Independent design judgment

V5's failed GPU benefit does not contradict its CPU protocol tests. Those tests
establish causal legality on fixtures; they do not establish accurate service
forecasts, cheap planning, or a beneficial closed-loop physical schedule.
V6 therefore changes the optimization boundary before adding more weights:

1. Measure the planner itself; cache only decision-equivalent expressions.
2. Keep Fine's immediately executable complete ready cut as the default action.
3. Price a tiny number of complete-cut alternatives, not a speculative tree.
4. Deviate only with support and conservative cost/credit evidence. Quantiles
   are empirical forecast bounds, not a theorem of Fine-relative performance.
5. Add future-GPU0 cost only after a separate randomized intervention supports
   it. Parent mismatch alone neither proves contamination nor authorizes a
   rejection, a cancellation, or an invented saved-work term.

## Objective and physical accounting

At observed Owner time t let R be the legal, released ready target cut. Each
target has current Parent, input frontier, actual Consumer first-visibility
ACK, deadline and candidate availability. Its residual audio credit is

    b_i(a) = audio_i * Pr(commit_i(a)<=deadlineC_i and
                         [display_already_met_i or
                          legal_display_i(a)<=deadlineD_i]).

Expired display credit is zero; already displayed audio gets no second display
reward, but still requires timely commit. Prediction confers no write right.

The feasible default a0 is independent FP32 Generate(R). V6 considers at most
two alternatives: Verify(R) when every candidate is ready; and a prefix of up
to four ready candidates followed by Generate(the remaining cut). Both calls
are real sequential homogeneous GPU1 invocations. Every target appears exactly
once in each priced plan. Nothing running on GPU0 or GPU1 is reclaimed.

For Verify, K is the number of rejected rows. Use empirical whole-physical-batch
samples to retain correlated K and its paired verify/fallback lease, instead of
substituting C_fallback(ceil(E[K])). Within a fixed K, input-conditional row odds
w_i=p_i/(1-p_i) give a transparent approximation:

    Pr(S failures | |S|=K) = product(i in S,w_i)/e_K(w)
    Pr(i fails | K) = w_i*e_(K-1)(w without i)/e_K(w).

Prefix/suffix elementary-symmetric dynamic programming computes these marginals
in O(n*K), and their sum is exactly K. This is a conditional model, not proof
that its statistical assumptions match an unseen stream. Inputs are available
audio/prompt/candidate sizes, birth relation and observed recent reject; labels
are past K, phase/lease times and row completion fractions. No future length,
fault assignment, donor identity, or oracle output is used online.

Row completion distributions retain early verified rows before fallback ends;
physical occupancy uses the complete paid Batch lease. A plan's second call
starts only after the first call's empirical upper lease. Let B-/B+ bound
observed-scenario audio credit, E[W] be modeled paid work and L+ its upper wall.
A deviation needs supported exact-n samples, no larger modeled late-audio risk,
and inclusion of any twice-deferred target in the next actual dispatch. It must
also have either conservative credit gain without substantially longer upper
wall, or no conservative credit loss with material expected work saving.
Utility breaks eligible choices using predicted residual credit minus observed
credit-rate times wall, and a causal future-work term only if C permits it.

This intentionally restrictive gate can return Fine on every decision. That is
a legitimate negative result, not evidence of a superior algorithm. It tests
whether a practical, low-overhead deviation opportunity survives honest costs.

## Time and replanning obligations

Charge past measured planning P90 plus a dispatch allowance before evaluating
deadlines. If a selected deviation overruns that allowance before issue, use
the complete Fine cut rather than pretending the decision occurred earlier.
Actual-dispatch deferrals are bound to session/epoch/Parent/window/contract;
observing a new snapshot cannot erase them. A later replanning may change the
second hypothetical call; it cannot retroactively authorize already-issued
work. Finite service and continued eligibility are needed for progress.

## Safety preservation conditions

Assume the original trusted Worker/renderer boundary, single Owner, actual
audio release, immutable job identity and durable storage/sync assumptions.
The selector changes which evidence computation is requested, not admission:

* Generate uses the exact declared FP32 target input and complete stop/budget.
* Verify binds the actual correct Parent, audio and execution contract; failure
  pays a fresh FP32 fallback. Birth compatibility is only a forecast feature.
* Both routes undergo unchanged A/B/C/D, D1, frontier and WAL predicates.
* Immutable row receipts may arrive early; Batch-drained still owns reuse.
* Duplicate, stale or wrong-contract rows fail existing checks. A predicted
  deadline benefit cannot install them. Restart recovers the same WAL identity.

Induction: if the admitted prefix satisfies the old invariant, an action merely
produces a candidate evidence record; installation appends only after the old
predicate succeeds. Consequently the new prefix satisfies the same invariant.
This is conditional safety preservation, not equivalence of histories, tokens,
recognition quality or latency across different numerical Batch schedules.

## B and C are gates, not hidden advantages

Changed padding is evaluated as a paid numerical realization with original
full-target row order, complete Z/stop/P/text and repeat/oracle checks. If it
passes, the same operator must be offered to Fine and Standard. Short first
mismatch prefixes do not justify inventing a KV reuse implementation.

An installation hold is not a semantic state corruption. C separates existing
in-flight tail from actually unissued future work and counts physical batches
once. Even a positive randomized cost effect needs a supported online-observable
stratum before a learned risk term is valid. Otherwise the risk arm is NO-GO.

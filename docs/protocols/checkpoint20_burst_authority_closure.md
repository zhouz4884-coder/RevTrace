# Checkpoint-20 burst-authority closure

This protocol repairs the only repeated-seed tail-latency failure observed in
the ordinary-proposer checkpoint-20 service. The failing round contained two
serial singleton canonical checks. It does not relax the 1.9 second SLO.

The selected contract is:

- ordinary FP16 fixed-batch proposer on GPU 0;
- batch-invariant FP16 canonical authority on GPU 1;
- B=1 for an isolated nonterminal check;
- fixed B=2 for a nonterminal verification burst of at least two jobs;
- fixed B=12 for checkpoint and terminal authority;
- full terminal state projection as the checkpoint/rebase payload.

Fixed B=2 is admitted only after 720 same-input B=1/B=2 comparisons show zero
token, text, state-token, and state-text mismatches under the frozen runtime
hash. This is an observed compatibility contract, not a universal theorem.

The risk threshold remains data-adaptive. The 0.03125 counterexample from the
same proposer/canonical contract is adaptation evidence; a later held-out stage
freezes the resulting threshold. Formal risk uses a separate randomized
fixed-probability audit and a time-uniform mixture e-process. Dependent replay
is diagnostic only and is not interpreted with an iid binomial interval.

The contract passes only if all five frozen-threshold seeds have P99 at most
1.9 seconds, zero deadline misses, zero selected-authority violations, and the
formal 95% risk upper bound is at most 0.5%.

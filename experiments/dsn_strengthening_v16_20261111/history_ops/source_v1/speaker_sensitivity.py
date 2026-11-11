"""Exact eight-speaker paired label-swap and deterministic leave-out sensitivity."""
from fractions import Fraction
from itertools import combinations, product


def recount_new8(report):
    rows = report['source_pairs']
    if len(rows) != 8 or len({r['speaker_id'] for r in rows}) != 8:
        raise ValueError('exactly eight paired speakers required')
    if report['timing_repeats_per_policy'] != 2 or any(r['timing_repeats'] != 2 for r in rows):
        raise ValueError('both repeats must remain inside speaker')
    values = []
    for r in sorted(rows, key=lambda x:x['speaker_id']):
        offer = Fraction(str(r['offered_audio_s']))
        control = Fraction(str(r['conservative_credit_audio_s']))
        full = Fraction(str(r['fullcall_credit_audio_s']))
        if not 0 <= control <= offer or not 0 <= full <= offer:
            raise ValueError('credit/outcome denominator mismatch')
        gain = full-control
        if abs(float(gain)-r['paired_gain_audio_s']) > 1e-8:
            raise ValueError('frozen paired gain does not conserve credits')
        values.append(dict(speaker=r['speaker_id'],source_id=r['source_id'],
            offer=offer, gain=gain, control=control, full=full))
    observed = sum(x['gain'] for x in values)
    distribution = [sum(sign*x['gain'] for sign,x in zip(signs,values))
                    for signs in product((-1,1),repeat=8)]
    extreme = sum(abs(x) >= abs(observed) for x in distribution)
    if extreme < 2: raise ValueError('two-sided eight-pair p cannot be less than2/256')
    subsets=[]
    for leave in (0,1,2):
        for excluded in combinations(range(8),leave):
            kept=[x for i,x in enumerate(values) if i not in excluded]
            offered=sum(x['offer'] for x in kept)
            gain=sum(x['gain'] for x in kept)
            subsets.append(dict(excluded_speakers=[values[i]['speaker'] for i in excluded],
                kept_speakers=len(kept), coverage_gain_pp=float(100*gain/offered),
                equal_speaker_mean_gain_pp=float(sum(100*x['gain']/x['offer'] for x in kept)/len(kept)),
                gain_audio_s=float(gain),offered_audio_s=float(offered)))
    return dict(acoustic_speakers=8,timing_repeats_kept_inside_speaker=True,
        observed_coverage_gain_pp=subsets[0]['coverage_gain_pp'],
        exact_two_sided_p=extreme/256,exact_extreme_assignments=extreme,total_label_swaps=256,
        smallest_possible_two_sided_p=2/256,
        permutation_assumption='independent speaker-level paired policy-label exchangeability under null; not an additional GPU trial or population guarantee',
        all_leave_zero_one_two_out=subsets,
        leave_out_ranges=[dict(leave_out=k,
            minimum_pp=min(r['coverage_gain_pp'] for r in subsets if len(r['excluded_speakers'])==k),
            maximum_pp=max(r['coverage_gain_pp'] for r in subsets if len(r['excluded_speakers'])==k)) for k in (0,1,2)])

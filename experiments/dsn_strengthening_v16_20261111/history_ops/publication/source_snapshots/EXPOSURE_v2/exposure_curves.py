"""Prepared v2 pure functions. Not frozen or executed in a formal experiment.

Exposure is an observed code-point residence proxy, not validated human burden.
The stable prefix is retrospective and censored at last same-source observation.
"""
from collections import defaultdict


def common_prefix(a,b):
    i=0
    while i<min(len(a),len(b)) and a[i]==b[i]:i+=1
    return a[:i]


def stable_prefix_curve(rows):
    """One source/mode, actual sequence, no sorting or synthetic extension."""
    if not rows:raise ValueError('empty observation window')
    if any(rows[i]['observed']>rows[i+1]['observed'] for i in range(len(rows)-1)):
        raise ValueError('Consumer clock decreases')
    suffix=rows[-1]['text'];prefixes=[None]*len(rows)
    for i in range(len(rows)-1,-1,-1):
        suffix=common_prefix(rows[i]['text'],suffix);prefixes[i]=suffix
    first,horizon=rows[0]['observed'],rows[-1]['observed']
    curve=[];visible_auc=stable_auc=volatile_auc=0.0
    for i,(row,prefix) in enumerate(zip(rows,prefixes)):
        duration=(rows[i+1]['observed']-row['observed']) if i+1<len(rows) else 0.0
        visible=len(row['text']);stable=len(prefix);volatile=visible-stable
        visible_auc+=duration*visible;stable_auc+=duration*stable;volatile_auc+=duration*volatile
        curve.append(dict(row_index=row.get('row_index',i),observed=row['observed'],
            seconds_since_first_actual_observation=row['observed']-first,
            remaining_observed_horizon_seconds=horizon-row['observed'],visible_code_points=visible,
            retrospective_stable_prefix_code_points=stable,volatile_suffix_code_points=volatile,
            step_duration_seconds=duration,terminal_zero_duration=i==len(rows)-1))
    assert all(curve[i]['retrospective_stable_prefix_code_points']<=curve[i+1]['retrospective_stable_prefix_code_points'] for i in range(len(curve)-1))
    assert abs(visible_auc-stable_auc-volatile_auc)<1e-6
    return dict(first_actual_observation=first,last_actual_same_source_observation=horizon,
        observed_horizon_seconds=horizon-first,visible_code_point_seconds=visible_auc,
        retrospective_stable_prefix_code_point_seconds=stable_auc,volatile_suffix_code_point_seconds=volatile_auc,
        curves=curve,retrospective=True,future_after_horizon_unknown=True,
        terminal_full_length_is_vacuous_at_frozen_horizon=True)


def exposure_from_spans(spans,curve_summary,metric_family):
    """Keep D/S edit identities and LCP identities in different output groups."""
    if metric_family not in ('minimum_edit','lcp_suffix_identity'):
        raise ValueError('unknown identity family')
    closed=[s for s in spans if s['retracted']]
    survived=[s for s in spans if not s['retracted']]
    expected_operations={'D','S'} if metric_family=='minimum_edit' else {'LCP_SUFFIX_CLOSE'}
    if any(s['retraction_operation'] not in expected_operations for s in closed):
        raise ValueError('identity conventions were mixed')
    modified=sum(s['lifetime_seconds'] for s in closed)
    censored=sum(s['observed_lifetime_seconds'] for s in survived)
    # One span per Unicode code point in the existing v1 ledger.
    if any(len(s['char'])!=1 for s in spans):raise ValueError('expected unit code-point spans')
    if abs(modified+censored-curve_summary['visible_code_point_seconds'])>1e-5:
        raise ValueError('residence-area conservation failed')
    return dict(metric_family=metric_family,modified_identity_code_points=len(closed),
        exposed_then_modified_code_point_seconds=modified,
        right_censored_surviving_code_points=len(survived),
        right_censored_survivor_observed_code_point_seconds=censored,
        total_observed_code_point_seconds=modified+censored,
        observation_start=curve_summary['first_actual_observation'],
        observation_horizon=curve_summary['last_actual_same_source_observation'],
        interpretation='Measured actual-Consumer code-point residence proxy; alignment dependent, not validated reading time or human experience')

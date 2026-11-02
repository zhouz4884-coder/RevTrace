"""All offered 500ms/EOS endpoints with explicit per-request origins."""
from __future__ import annotations
import math, statistics
from common import need

def quantile(values, q):
    values = sorted(values)
    if not values: return math.inf
    pos = (len(values)-1)*q; i = int(pos); j = min(i+1, len(values)-1)
    return math.inf if math.isinf(values[j]) else values[i]+(values[j]-values[i])*(pos-i)
def finite(x): return x if math.isfinite(x) else None
def recount(rows, sources, origins):
    need(set(origins) == set(sources), 'request clock set differs from sources')
    frontiers = []
    for sid, source in sources.items():
        observed = [r for r in rows if r['source_id'] == sid]; n = source['frames']; previous = 0
        need(observed, 'source has no actual Consumer rows')
        need(all(b['observed'] >= a['observed'] for a,b in zip(observed, observed[1:])), 'Consumer clock order')
        for frontier in list(range(8000, n, 8000)) + [n]:
            offer = origins[sid] + frontier / 16000
            d = next((r['observed']-offer for r in observed if r['observed'] >= offer and r['visible_frontier'] >= frontier), math.inf)
            c = next((r['observed']-offer for r in observed if r['observed'] >= offer and r['certified_frontier'] >= frontier), math.inf)
            frontiers.append(dict(source_id=sid, frontier=frontier, is_EOS=frontier==n, offer=offer, audio_seconds=(frontier-previous)/16000, D=finite(d), C=finite(c), D2=d<=2, C8=c<=8)); previous=frontier
    ds=[r['D'] if r['D'] is not None else math.inf for r in frontiers];cs=[r['C'] if r['C'] is not None else math.inf for r in frontiers]
    d99=quantile(ds,.99);c99=quantile(cs,.99)
    return dict(offered_frontiers=len(frontiers),offered_audio_seconds=sum(r['audio_seconds'] for r in frontiers),primary_linear_all_offered_D99=finite(d99),primary_linear_all_offered_C99=finite(c99),original_quantile_test_pass=d99<=2 and c99<=8,complete_coverage_and_original_quantile_pass=all(x is not None for r in frontiers for x in (r['D'],r['C'])) and d99<=2 and c99<=8,dual_deadline_audio_credit_seconds=sum(r['audio_seconds'] for r in frontiers if r['D2'] and r['C8']),D2_misses_all_offered=sum(not r['D2'] for r in frontiers),C8_misses_all_offered=sum(not r['C8'] for r in frontiers),EOS_D2_misses=sum(r['is_EOS'] and not r['D2'] for r in frontiers),missing_D_frontiers=sum(x is None for r in frontiers for x in [r['D']]),missing_C_frontiers=sum(x is None for r in frontiers for x in [r['C']]),frontiers=frontiers)

def smoke_decision(results):
    """Timing evidence triggers diagnosis, never a causal code-defect verdict."""
    need(len(results)==8, 'smoke requires exactly eight frozen cells')
    by={(r['version'],r['strategy'],r['repeat']):r for r in results}
    need(len(by)==8 and all(r['semantic']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE' for r in results), 'smoke missing semantic evidence')
    repeated=[]; opportunities=[]
    for rep in (0,1):
        old=by[('bdfa','fullcall',rep)]['primary'];new=by[('final','fullcall',rep)]['primary'];control=by[('final','conservative',rep)]['primary']
        d0=old['primary_linear_all_offered_D99'];d1=new['primary_linear_all_offered_D99'];dc=control['primary_linear_all_offered_D99']
        repeated.append(old['complete_coverage_and_original_quantile_pass'] and not new['complete_coverage_and_original_quantile_pass'] and d0 is not None and d1 is not None and d1-d0>=.25 and d1>=1.15*d0)
        opportunities.append(new['dual_deadline_audio_credit_seconds']-control['dual_deadline_audio_credit_seconds']>=1. or (d1 is not None and dc is not None and dc>0 and d1<=.75*dc))
    status='HOLD_REPEATED_PAIRED_TIMING_REGRESSION_REQUIRES_DIAGNOSIS' if all(repeated) else ('HOLD_NO_STRONG_FINAL_END_TO_END_OPPORTUNITY' if not all(opportunities) else 'CONTINUE_REMAINING_24_FROZEN_CELLS')
    return dict(status=status,repeated_regression_trigger=repeated,final_e2e_opportunity=opportunities,causal_code_defect_established=False,single_EOS_miss_does_not_trigger_regression=True,scope='Frozen engineering stopping rule, no statistical equivalence/significance claim')

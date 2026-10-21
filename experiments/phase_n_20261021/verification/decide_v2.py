"""Conjunctive preregistered gate, using measured coverage and qualified costs."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();base=a.base
v0=json.loads((base/'v0_v4_formal/V0_LIVE_ALIGNMENT.json').read_text())
v1=json.loads((base/'v1_formal/INDEPENDENT_AUDIT.json').read_text())
root=json.loads((base/'root_readiness_v1/ROOT_READINESS_AUDIT.json').read_text())
triage=json.loads((base/'root_readiness_v1/C3_READINESS_TRIAGE.json').read_text())
coverage=[]
for cell in v0['cells']:
    rows=cell['rows'];native_ready=sum(r['candidate_present'] and r['ready_at_enqueue'] for r in rows)
    exact_ready=sum(r['full_token_equal'] and r['ready_at_enqueue'] for r in rows)
    coverage.append({'cell':cell['cell'],'opportunities':len(rows),'native_ready':native_ready,
        'strict_same_parent_input_and_ready':cell['counts']['aligned_and_ready_at_enqueue'],
        'recorded_oracle_exact_Z_and_ready_upper_bound':exact_ready,'upper_bound_fraction':exact_ready/len(rows),
        'scope':'optimistic reference-assisted bound for complete-candidate exact reuse at the recorded target realization; NOT a deployed selector or independent sample rate'})
root_coverage=[{'repeat':r['repeat'],'opportunities':r['opportunities'],'prepared':r['prepared'],
    'exact_and_timely':r['exact_and_timely'],'fraction':r['exact_and_timely']/r['opportunities']} for r in root['comparisons']]
assert max(r['upper_bound_fraction'] for r in coverage)<.25
assert max(r['fraction'] for r in root_coverage)<.25
decision={'decision':'NO_GO_ONLINE_SELECTOR','strict_bounded_fp32_gate':v1['decision'],
    'minimum_live_candidate_coverage':.25,'coverage_gate':'FAIL_FOR_TESTED_NATIVE_AND_ROOT_PREPARATION_POLICIES',
    'native_coverage':coverage,'root_live_coverage':root_coverage,'minimum_inclusive_advantage':.10,
    'cost_gate':'NOT_ESTABLISHED_END_TO_END; C1 conditional model saving does not imply live gain; C2/C3 fixed-state paid work is higher',
    'fixed_state_costs_not_serving':v1['costs'],
    'maximum_full_selector_commit_p99_risk':.05,'full_online_selector_tail_gate':'UNKNOWN_NOT_EXECUTED',
    'preparation_only_commit_p99_ratios_not_v2':[r['commit_event_p99_over_baseline'] for r in root['comparisons']],
    'root_processed_input_assumption':'REFUTED_AS_UNIVERSAL_EQUALITY_IN_ONE_CONTROLLED_TERMINAL_CASE; CPU batch replay reproduced; no output harm inferred',
    'canonical_integrity_gate':'PASS: protected full histories unchanged',
    'new_kv_reuse_fallback':False,'v2_started':False,
    'scope':'Deterministic decision against frozen engineering gates on this workload, not impossibility of verification or other serving systems',
    'next':'Finish T3 independent-authority sensitivity and documentation; no selector or new cache path'}
(base/'V2_STAGE_DECISION.json').write_text(json.dumps(decision,indent=2)+'\n')
print(json.dumps({'decision':decision['decision'],'best_native_upper_bound':max(r['upper_bound_fraction'] for r in coverage),
    'best_paid_root_coverage':max(r['fraction'] for r in root_coverage)},indent=2))

"""Explicit post-safety freeze; no algorithm, calibration or cell retuning."""
from pathlib import Path
import json,hashlib
from run_closed_stage_v2 import validate_plan
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=W/'PLAN.formal.json'
assert not p.exists()
plan=json.loads((W/'PLAN.smoke.json').read_text())
assert plan['formal_approved_after_smoke'] is False
plan['formal_approved_after_smoke']=True
plan['post_smoke_decision']={
 'decision':'GO_BOUNDED_IMPLEMENTATION_ABLATION_NOT_PERFORMANCE_CLAIM',
 'same_raw_v2_summary_sha256':'bc18eef442d51568ad0fbe00ad0b813408a91a5c9fb9524384a8cb8573dc987d',
 'prior_v1_false_positive_retained':True,
 'audit_only_correction_did_not_rerun_models':True,
 'parameters_cells_source_order_unchanged_from_prior_smoke_plan':True,
 'smoke_performance_not_a_tuning_signal':True,
 'scope':'Reused source diagnosis; no independent confirmatory claim',
}
validate_plan(plan,'formal')
assert len(plan['stages']['formal']['cells'])==72
p.write_text(json.dumps(plan,indent=2,allow_nan=False)+'\n')
names=['run_closed_stage_v2.py','audit_closed_v2.py','audit_closed_helpers_v2.py',
       'smoke_reaudit_gate_v2.py','finalize_smoke_reaudit_v2.py','summarize_closed.py']
r={'plan_sha256':sha(p),'controllers':{n:sha(W/n) for n in names},
   'runtime_commit':plan['runtime_commit'],'formal_cells':72,'GPU_started':False}
(W/'FORMAL_FREEZE_LOCAL.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))

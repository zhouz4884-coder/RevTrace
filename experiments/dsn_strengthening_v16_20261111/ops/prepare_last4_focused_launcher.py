"""Prepare a unique final-four launch; preserve the executed next-two script."""
from pathlib import Path
import ast
E=Path(__file__).resolve().parents[1];v=(E/'ops/launch_focused_new2_v1.py').read_text(encoding='utf8')
pairs=[('CONFIRM_NEW2_FULL_READY_V1','CONFIRM_LAST4_FULL_READY_V1'),('baseline_ops/FOCUSED_CONFIRMATION_PREPARATION_V2','baseline_ops/FOCUSED_LAST4_PREPARATION_V1'),("len(plan['cells'])==8","len(plan['cells'])==16"),('cells_checked=8','cells_checked=16'),('planned_trials=8','planned_trials=16'),('focused_confirmation_v2/root_gates/','focused_confirmation_v2/root_gates_last4/'),('focused_new2_launch_tmp','focused_last4_launch_tmp'),('V16_ROOT_NEXT2_FULL_READY_AFTER_RESOURCE8','V16_ROOT_LAST4_FULL_READY_AFTER_REFERENCE')]
for old,new in pairs:
 assert old in v,old
 v=v.replace(old,new)
ast.parse(v);p=E/'ops/launch_focused_last4_v1.py';assert not p.exists();p.write_text(v,encoding='utf8')
print('Prepared final-four operator launcher; no GPU/model launched')

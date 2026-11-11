"""Create a separate Root operator launcher; do not edit the used Resource8 one."""
from pathlib import Path
import ast
E=Path(__file__).resolve().parents[1]
raw=(E/'ops/launch_resource8_v1.py').read_text(encoding='utf8')
replacements=[
 ('Root-only eight-cell same-resource two/four-session GPU comparison.','Root-only eight-cell next-two-speaker Fullcall versus Ready-only confirmation.'),
 ("D=E/'launch_ops/RESOURCE8_V1'","D=E/'launch_ops/CONFIRM_NEW2_FULL_READY_V1'"),
 ('baseline_ops/RESOURCE_PREPARATION_V2','baseline_ops/FOCUSED_CONFIRMATION_PREPARATION_V2'),
 ('RESOURCE_PLAN_v1.json','SERVICE_PLAN.json'),
 ("hand['resource_plan_sha256']","hand['plan_sha256']"),
 ('launch_ops/PILOT24_V2/RESOURCE_CLOSURE.json','launch_ops/RESOURCE8_V1/RESOURCE_CLOSURE.json'),
 ('PASS_PILOT24_COMPLETED_AND_OWNED_PHYSICAL_RELEASE','PASS_RESOURCE8_COMPLETE_AND_OWNED_PHYSICAL_RELEASE'),
 ('CPU_RESOURCE_DRIVER_V2','CPU_FOCUSED_CONFIRMATION_V2'),
 ('PASS_GROUPED_RESOURCE_CPU_ONLY','PASS_FOCUSED_CONFIRMATION_CPU_ONLY'),
 ("hand['resource_plan']","hand['plan']"),
 ("hand['driver_source_commit']","hand['source_commit']"),
 ("actual_NN_source_commit=hand['actual_NN']","actual_NN_source_commit=plan['actual_NN']['source_commit']"),
 ("reference_generator_commit=hand['reference_generator_commit']","reference_generator_commit=plan['reference_generator']['source_commit']"),
 ('resource_driver_source_v2','focused_confirmation_source_v2'),
 ('packages/RESOURCE_DRIVER_SOURCE_v2.json','packages/FOCUSED_CONFIRMATION_SOURCE_v2.json'),
 ('ROOT_NOARG_RUNTIME_RESOURCE.json','ROOT_NOARG_RUNTIME_FOCUSED.json'),
 ('RESOURCE_DRIVER_EXPLICIT.json','FOCUSED_DRIVER_EXPLICIT.json'),
 ('resource_driver_v2/root_gates/','focused_confirmation_v2/root_gates/'),
 ('V16_ROOT_RESOURCE8_AFTER_PILOT24','V16_ROOT_NEXT2_FULL_READY_AFTER_RESOURCE8'),
 ("hand['prelaunch_requirements']","hand['prelaunch_required_fields']"),
 ("hand['resource_command']","hand['command']"),
 ("source=hand['remote_source']","source=plan['driver']['source_root']"),
 ('/RESOURCE8_V1.process.log','/CONFIRM_NEW2_FULL_READY_V1.process.log'),
 ('/RESOURCE8_V1.HANDLE.json','/CONFIRM_NEW2_FULL_READY_V1.HANDLE.json'),
 ('resource_launch_tmp','focused_new2_launch_tmp'),
 ('7b83b2151040512776b5bdaa7f7680e7a8f59047','4fb6d05f1cf4ad80e73bae9934afaed04c60edeb')]
for old,new in replacements:
 assert old in raw,old
 raw=raw.replace(old,new)
ast.parse(raw)
target=E/'ops/launch_focused_new2_v1.py';assert not target.exists();target.write_text(raw,encoding='utf8')
print('Prepared independent operator launcher; no model/GPU launch')

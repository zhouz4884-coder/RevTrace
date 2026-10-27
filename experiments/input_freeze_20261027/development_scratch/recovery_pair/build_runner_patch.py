"""Mechanical patch construction only; never modifies the runtime checkout."""
from pathlib import Path
import difflib
import hashlib
import json

root=Path(r'D:\VLA_QWEN\RevTrace\.execution\lp1_runtime')
out=Path(__file__).resolve().parent
path=root/'runtime/scripts/run_tc_live_qwen.py'
before=path.read_bytes().decode('utf8')
eol='\r\n' if '\r\n' in before else '\n'
after=before
edits=[
("from revtrace.recovery_profile import RecoveryProfile,recovery_processor\n",
 "from revtrace.recovery_profile import RecoveryProfile,recovery_processor\nfrom revtrace.recovery_fault import parse_post_sync_target,target_in_synced_group\n"),
("    p.add_argument('--pause-post-sync-at',type=float,default=0.)\n",
 "    p.add_argument('--pause-post-sync-at',type=float,default=0.)\n    p.add_argument('--pause-post-sync-target',help='fault-harness session:sample_frontier, after real WAL sync before owner install')\n"),
("    a=p.parse_args()\n",
 "    a=p.parse_args()\n    logical_fault_target=parse_post_sync_target(a.pause_post_sync_target)\n    if logical_fault_target is not None and a.pause_post_sync_at:\n        raise ValueError('select exactly one logical or time-based post-sync fault')\n    if logical_fault_target is not None and (not a.envelope_config or not a.protocol_kernel):\n        raise ValueError('logical post-sync fault requires the complete kernel/envelope run')\n"),
("            if a.pause_post_sync_at and not early_recovery and scheduler.owner_epoch==1:\n",
 "            if (a.pause_post_sync_at or logical_fault_target is not None) and not early_recovery and scheduler.owner_epoch==1:\n"),
("                    if time.perf_counter()>=scheduler.origin+a.pause_post_sync_at:\n",
 "                    should_pause=(target_in_synced_group(transitions,logical_fault_target) if logical_fault_target is not None\n                        else time.perf_counter()>=scheduler.origin+a.pause_post_sync_at)\n                    if should_pause:\n"),
("                            transactions=[t['transaction_id'] for t in transitions],\n",
 "                            logical_target=a.pause_post_sync_target,\n                            durable_sequences=[int(r[0]) for r in receipts],\n                            transactions=[t['transaction_id'] for t in transitions],\n"),
]
for old,new in edits:
    old=old.replace('\n',eol);new=new.replace('\n',eol)
    if after.count(old)!=1:raise RuntimeError('source context not unique: '+old)
    after=after.replace(old,new,1)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
    fromfile='a/runtime/scripts/run_tc_live_qwen.py',tofile='b/runtime/scripts/run_tc_live_qwen.py'))
for name,text in [('recovery_runner.patch',patch),('run_tc_live_qwen_recovery_preview.py',after)]:
    (out/name).write_text(text,encoding='utf8',newline='\n')
(out/'RUNNER_PATCH_IDENTITY.json').write_text(json.dumps(dict(
    baseline_path=str(path),baseline_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    modified_sha256=hashlib.sha256(after.encode()).hexdigest(),
    note='mechanical temp patch; actual runtime unchanged'),indent=2)+'\n',encoding='utf8')

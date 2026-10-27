from pathlib import Path
import json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028')
c=ssh_client()
try:
 code=r'''from pathlib import Path
import hashlib,json,subprocess,time
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/freeze_boundary_20261027')
names=['recovery_v7_c4_r0','recovery_v7_native_asset_audit_v1','context_holdout_freeze_v1','native_v8_smoke','native_numeric_v9_v1','paid_wait_operator_v8_v1','paid_wait_operator_v9_v1','paid_native_context_v1','paid_native_context_capacity_v2','paid_native_context_capacity_audit_v1','paid_native_context_capacity_audit_v2','native_strong_v10_smoke','native_prompt_clarity_v1','dev_v10_c16_staggered_r0_revtrace_b040_prior']
rows=[]
for name in names:
 h=json.loads((O/(name+'_HANDLE.json')).read_text());p=Path('/proc')/str(h['pid']);same=False;state='missing'
 if p.exists():
  fields=p.joinpath('stat').read_text().rsplit(')',1)[1].split();state=fields[0]
  same=fields[19]==h['linux_start_ticks'] and hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()==h['command_sha256']
 assert not (same and state!='Z'),'owned controller still active:'+name
 D=Path(h['result']);terminal=[n for n in ['SUMMARY.json','SMOKE_SUMMARY.json','RESULT.json','GATE.json','STOP.json'] if (D/n).exists()];assert terminal
 rows.append(dict(stage=name,pid=h['pid'],same_live_process=same and state!='Z',state=state,terminal_records=terminal))
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True)
print(json.dumps(dict(status='ALL_KNOWN_OWNED_CONTROLLERS_TERMINAL',observed_unix=time.time(),rows=rows,GPU_apps_at_observation=gpu,scope='read-only; no other job was terminated; scientific gates prohibit automatic new matrices')),flush=True)
'''
 i,o,e=c.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -',timeout=35);i.write(code);i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(err);assert rc==0
 r=json.loads(out);dest=L/'RESOURCE_CLOSURE.json';assert not dest.exists();dest.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(dict(status=r['status'],stages=len(r['rows']),GPU_apps=r['GPU_apps_at_observation']),indent=2))
finally:c.close()

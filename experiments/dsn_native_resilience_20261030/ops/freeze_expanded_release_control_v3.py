"""Freeze allocator control after release-only95 passed semantics but96 OOM."""
import hashlib,json,pathlib,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030'
cfg=json.loads((F/'long_memory_diagnostic_v3_configs/release_g_r0.json').read_bytes());cfg.update(experiment_id='SC_ORIGINAL_LONG_MEMORY_DIAG_V3_release_g_expanded_r0',allocator_conf='expandable_segments:True');cfg['comparison_inputs'].append(dict(label='release_g_default_r0',kind='continuous_prefix',path=O+'/long_memory_diagnostic_v3/release_g_r0/COMPLETE_ROWS.jsonl',sha256='fe068fab653e2dfb14200ac64b35d07202eca4f9f149c101901a7b4c3ea8c23e'))
cp=F/'long_memory_diagnostic_v3_configs/release_g_expanded_r0.json';assert not cp.exists();cp.write_bytes((json.dumps(cfg,indent=2)+'\n').encode());target=P+'/long_memory_diagnostic_v3_configs/'+cp.name;cell=dict(label='release_g_expanded_r0',config=target,config_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),out=O+'/long_memory_diagnostic_v3/release_g_expanded_r0',log=O+'/long_memory_diagnostic_v3/release_g_expanded_r0.log');xp=F/'LONG_MEMORY_EXPANDED_RELEASE_CELL_v3_FROZEN.json';assert not xp.exists();xp.write_bytes((json.dumps(cell,indent=2)+'\n').encode())
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 with s.open(target,'wx') as stream:stream.write(cp.read_bytes());stream.flush()
 s.close();print(json.dumps(cell))
finally:c.close()

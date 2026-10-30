"""Bind the two fixed same-input calls to the real captured95th failure cut."""
import hashlib,json,pathlib,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030'
remote=O+'/long_memory_diagnostic_v1/default_r0/OOM_FAILURE_INPUT.json';expected='80cebc4aa6b693ae443fa470d63b05e0521a7f1874b8da9d1586729461a3b9e1';local=F/'LONG_MEMORY_FAILED_INPUT_v1.json'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 with s.open(remote,'rb') as stream:data=stream.read(100000)
 assert hashlib.sha256(data).hexdigest()==expected;cut=json.loads(data);assert cut['end']==760000 and cut['start']['frontier']==752000;assert not local.exists();local.write_bytes(data)
 cfg=json.loads((F/'long_memory_diagnostic_v1_configs/default_r0.json').read_bytes());cfg.update(experiment_id='SC_ORIGINAL_LONG_MEMORY_DIAG_V1_same_input_r0',mode='same_input_restore_twice',failure_input=remote,failure_input_sha256=expected,actual_failed_input_end=760000,actual_failed_input_start=752000,same_input_repeats=2)
 cp=F/'long_memory_diagnostic_v1_configs/same_input_r0.json';assert not cp.exists();cp.write_bytes((json.dumps(cfg,indent=2)+'\n').encode());target=P+'/long_memory_diagnostic_v1_configs/same_input_r0.json'
 with s.open(target,'wx') as stream:stream.write(cp.read_bytes());stream.flush()
 s.close();cell=dict(label='same_input_r0',config=target,config_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),out=O+'/long_memory_diagnostic_v1/same_input_r0',log=O+'/long_memory_diagnostic_v1/same_input_r0.log');xp=F/'LONG_MEMORY_SAME_INPUT_CELL_v1_FROZEN.json';assert not xp.exists();xp.write_bytes((json.dumps(cell,indent=2)+'\n').encode());print(json.dumps(cell))
finally:c.close()

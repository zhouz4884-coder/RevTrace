"""Keep compact stdout and exact remote prerequisite bytes as distinct artifacts."""
import hashlib,json,pathlib,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/dsn_native_resilience_20261030';dest=F/'FORMAL_OPERATOR_PREREQUISITE_BYTES_v2.json';assert not dest.exists()
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 s=c.open_sftp()
 with s.open(O+'/FORMAL_OPERATOR_PREREQUISITE_v2.json','rb') as stream:exact=stream.read()
 stdout=(F/'FORMAL_OPERATOR_PREREQUISITE_v2.json').read_bytes();assert json.loads(exact)==json.loads(stdout);dest.write_bytes(exact)
 cpu=F/'formal_operator_cpu_remote_v2';cpu.mkdir();rows=[]
 for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','unittest.log','SUMMARY.json','GATE.json'):
  remote=O+'/formal_operator_cpu_v2/'+name
  with s.open(remote,'rb') as stream:data=stream.read()
  (cpu/name).write_bytes(data);rows.append(dict(path=name,remote=remote,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 s.close();receipt=dict(status='PASS_IDENTICAL_PREREQUISITE_VALUES_DISTINCT_ENCODINGS_AND_REMOTE_CPU_COLLECTION',compact_stdout_sha256=hashlib.sha256(stdout).hexdigest(),remote_artifact_sha256=hashlib.sha256(exact).hexdigest(),same_values=True,prior_failed_launch_actual_NN_cells=0,files=rows,source_commit=json.loads(exact)['operator_source_commit']);(cpu/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());(F/'FORMAL_READINESS_ENCODING_RECEIPT_v2.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))
finally:c.close()

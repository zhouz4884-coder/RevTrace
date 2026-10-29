"""Read only the core controller's tiny completion gate and exact PID identity."""
import pathlib,json,hashlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
gate=B/'results/revtrace/physical_retirement_20261028/dsn_service_stability_controller_v1/GATE.json'
proc=pathlib.Path('/proc/1305360')
row={'core_completion_gate_exists':gate.exists(),'core_gate':json.loads(gate.read_text()) if gate.exists() else None}
if proc.exists():
 row['controller_identity_matches']=(int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])==493080422 and hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()=='f59c8f01629b9a7bcb2781cda31d1083e108d1328f98a4d0a9a6e9b288d80937')
else:row['controller_pid_present']=False
print(json.dumps(row,indent=2))

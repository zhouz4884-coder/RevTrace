"""Resume the already frozen v2 QA after an immutable output-name collision."""
from pathlib import Path
import hashlib,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
gate=E/'ROOT_NOARG_QA_v2.json'
subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(gate)],cwd=R,capture_output=True,check=True)
record=E/'paper_qa/RUN_RECORD_v2.json';j=json.loads(record.read_bytes())
j.update(root_source_gate_sha256=sha(gate),administrative_preflight_retry='Use a unique v2 preflight output; v1 gate remains immutable. QA v2 had not started.')
record.write_bytes((json.dumps(j,indent=2)+'\n').encode())
r=subprocess.run([sys.executable,'-B',str(E/'qa_source/validate.py'),'--config',str(E/'paper_qa/CONFIG_v2.json'),'--manifest',str(E/'packages/QA_SOURCE_v2.json')],cwd=E/'qa_source',capture_output=True)
(E/'paper_qa/QA_OUTPUT_v2.txt').write_bytes(r.stdout+r.stderr);j['returncode']=r.returncode
if not r.returncode:j.update(summary_sha256=sha(E/'paper_qa/FINAL_v2/SUMMARY.json'),gate_sha256=sha(E/'paper_qa/FINAL_v2/GATE.json'))
record.write_bytes((json.dumps(j,indent=2)+'\n').encode())
assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-2200:]
print(r.stdout.decode())

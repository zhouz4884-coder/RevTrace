set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
assert json.loads((O/'recovery_development/SUMMARY.json').read_text())['cells']==2
d=json.loads((O/'RECOVERY_DEVELOPMENT_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert hashlib.sha256((P/'INDEPENDENT_MANIFEST_v1.json').read_bytes()).hexdigest()=='c58574c1d5744f6b1bd078de4600da3077ba19cf1082b8d5e19011a4d870dba6'
assert hashlib.sha256((P/'run_n5_validation_v2.py').read_bytes()).hexdigest()=='11fdc2526249c1c828d5f34a1c7fafbd0d33288bf93667dc9f703393f6ffa436'
for name in ['CPU_N5_V3_LINUX_v1.xml','CPU_SUPERVISOR_V2_LINUX.xml']:
 r=ET.parse(P/name).getroot();s=list(r)[0] if r.tag=='testsuites' else r
 assert int(s.attrib['errors'])==int(s.attrib['failures'])==0
assert not (O/'formal_normal').exists() and not (O/'FORMAL_NORMAL_LAUNCH.json').exists()
cmd=[str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_n5_validation_v2.py'),'--stage','formal_normal']
with (O/'formal_normal_controller.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);q=Path('/proc')/str(p.pid)
 d=dict(pid=p.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],expected=105,
  controller_sha256=hashlib.sha256((P/'run_n5_validation_v2.py').read_bytes()).hexdigest(),
  runtime_commit='408d75624104e7e11af3f0f2832263c632b10ed8',no_formal_fault_without_independent_gate=True)
 (O/'FORMAL_NORMAL_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY

set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
assert not (O/'recovery_development').exists() and not (O/'RECOVERY_DEVELOPMENT_LAUNCH.json').exists()
x=ET.parse(P/'CPU_N5_V3_LINUX_v1.xml').getroot();s=list(x)[0] if x.tag=='testsuites' else x
assert int(s.attrib['tests'])==238 and int(s.attrib['failures'])==int(s.attrib['errors'])==0
cmd=[str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_n5_validation_v1.py'),'--stage','recovery_development']
with (O/'recovery_development_controller.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 q=Path('/proc')/str(p.pid)
 d=dict(pid=p.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
  controller_sha256=hashlib.sha256((P/'run_n5_validation_v1.py').read_bytes()).hexdigest(),expected=2,
  runtime_commit='408d75624104e7e11af3f0f2832263c632b10ed8')
 (O/'RECOVERY_DEVELOPMENT_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY

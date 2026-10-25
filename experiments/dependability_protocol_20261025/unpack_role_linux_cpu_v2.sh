set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/role_probe_v2"
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess,tarfile
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/role_probe_v2';N=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
d=json.loads((N/'FORMAL_NORMAL_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert json.loads((N/'formal_normal/SUMMARY.json').read_text())['cells']==105
if (N/'FORMAL_FAULT_LAUNCH.json').exists():
 d=json.loads((N/'FORMAL_FAULT_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
 assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
 assert json.loads((N/'formal_fault/SUMMARY.json').read_text())['cells']==21
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
tar=P/'ROLE_PROBE_SOURCE_v2.tar.gz';assert hashlib.sha256(tar.read_bytes()).hexdigest()=='69130e7ffeb248a0d72027f1c66d383468162044aec124884a9756b0c315ed49'
assert not (P/'probe').exists()
with tarfile.open(tar) as t:
 for m in t.getmembers():
  assert m.isfile();(P/m.name).resolve().relative_to(P.resolve())
 t.extractall(P,filter='data')
m=json.loads((P/'probe/SOURCE_MANIFEST.json').read_text());assert m['code_commit']=='b08fa4262d1c3ab7e07137eea340d0bb92be200c'
for r in m['files']:assert hashlib.sha256((P/'probe'/r['path']).read_bytes()).hexdigest()==r['sha256']
print('PASS_SOURCE_BYTES_NO_GPU',len(m['files']))
PY
cd "$P/probe"
REVTRACE_RUNTIME="$B/projects/revtrace_dependability_20261025/n5_v3/runtime" "$B/envs/revbatch-cu128/bin/python" -m pytest test_role_channel.py test_operator_controller.py test_power_window.py -q --junitxml=../CPU_LINUX_v1.xml
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
P=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dependability_20261025/role_probe_v2');x=ET.parse(P/'CPU_LINUX_v1.xml').getroot();s=list(x)[0] if x.tag=='testsuites' else x
assert int(s.attrib['tests'])==20 and int(s.attrib['failures'])==int(s.attrib['errors'])==0
out=P/'LINUX_CPU_GATE.json';assert not out.exists();out.write_text(json.dumps(dict(status='PASS_SOURCE_AND_CPU_ONLY',tests=20,
 harness_commit='b08fa4262d1c3ab7e07137eea340d0bb92be200c',core_runtime='408d75624104e7e11af3f0f2832263c632b10ed8',
 xml_sha256=hashlib.sha256((P/'CPU_LINUX_v1.xml').read_bytes()).hexdigest(),new_GPU_calls=0),indent=2)+'\n')
print(out.read_text())
PY

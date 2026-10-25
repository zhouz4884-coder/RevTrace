from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
W=Path(__file__).resolve().parent;S=W/'adversarial';F=W/'adversarial_frozen_v1';F.mkdir(exist_ok=False)
names=['role_channel.py','operator_controller.py','gpu_feedback_probe.py','test_role_channel.py','test_operator_controller.py',
 'GPU_PROTOCOL_v2.md','ROLE_CHANNEL_AND_STRICT_AUDIT_v1.md']
for name in names:shutil.copyfile(S/name,F/name)
(F/'.gitattributes').write_bytes(b'* -text\n')
subprocess.run(['git','init','-b','codex/role-channel-probe-20261026',str(F)],check=True,capture_output=True)
for k,v in [('user.name','Research Artifact'),('user.email','artifact@example.invalid'),('core.autocrlf','false')]:
 subprocess.run(['git','-C',str(F),'config',k,v],check=True)
subprocess.run(['git','-C',str(F),'add','.'],check=True)
subprocess.run(['git','-C',str(F),'-c','core.whitespace=cr-at-eol','diff','--cached','--check'],check=True)
subprocess.run(['git','-C',str(F),'commit','-m','Freeze role-limited coherent result fault operator and bounded CPU controls; GPU not run'],check=True,capture_output=True)
commit=subprocess.check_output(['git','-C',str(F),'rev-parse','HEAD'],text=True).strip();files=[]
for name in names+['.gitattributes']:
 data=(F/name).read_bytes();assert subprocess.check_output(['git','-C',str(F),'cat-file','blob','HEAD:'+name])==data
 files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
m=dict(code_commit=commit,core_runtime='408d75624104e7e11af3f0f2832263c632b10ed8',files=files,
 scope='CPU-tested prepared-input fault operator; NOT GPU/serving evidence; no current protected Canonical vulnerability claim',
 current_GPU_calls=0,pilot_expected_cases=8,formal_conditional_cases=64)
out=W/'ROLE_PROBE_SOURCE_MANIFEST_v1.json';assert not out.exists();out.write_text(json.dumps(m,indent=2)+'\n')
archive=W/'ROLE_PROBE_SOURCE_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as t:
 for r in files:t.add(F/r['path'],arcname='probe/'+r['path'])
 t.add(out,arcname='probe/SOURCE_MANIFEST.json')
print(json.dumps(dict(commit=commit,files=len(files),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),GPU_started=False)))

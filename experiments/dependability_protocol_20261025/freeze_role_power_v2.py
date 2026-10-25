from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,xml.etree.ElementTree as ET
W=Path(__file__).resolve().parent;F=W/'adversarial_frozen_v2';xml=W/'CPU_ROLE_POWER_V2_v1.xml'
x=ET.parse(xml).getroot();s=list(x)[0] if x.tag=='testsuites' else x
assert int(s.attrib['tests'])==20 and int(s.attrib['failures'])==int(s.attrib['errors'])==0
shutil.copyfile(W/'adversarial/MEASUREMENT_REPAIR_v2.md',F/'MEASUREMENT_REPAIR_v2.md')
for k,v in [('user.name','Research Artifact'),('user.email','artifact@example.invalid'),('core.autocrlf','false')]:subprocess.run(['git','-C',str(F),'config',k,v],check=True)
subprocess.run(['git','-C',str(F),'switch','-c','codex/role-power-window-20261026'],check=True)
subprocess.run(['git','-C',str(F),'add','gpu_feedback_probe.py','test_power_window.py','MEASUREMENT_REPAIR_v2.md'],check=True)
subprocess.run(['git','-C',str(F),'-c','core.whitespace=cr-at-eol','diff','--cached','--check'],check=True)
subprocess.run(['git','-C',str(F),'commit','-m','Bracket operator power window with uniform sampler padding; unchanged fault payload and selection rules'],check=True,capture_output=True)
git=lambda *args:subprocess.check_output(['git','-C',str(F),*args]);commit=git('rev-parse','HEAD').decode().strip()
assert git('rev-parse','HEAD^').decode().strip()=='f0eaae69323fbaa10b3892761a8ac2c149181013'
files=[]
for name in git('ls-files','-z').decode().split('\0'):
 if name:
  data=(F/name).read_bytes();assert git('cat-file','blob','HEAD:'+name)==data
  files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=dict(code_commit=commit,base_harness='f0eaae69323fbaa10b3892761a8ac2c149181013',core_runtime='408d75624104e7e11af3f0f2832263c632b10ed8',
 files=files,scope='measurement-only common sampler padding; fixed payload/models/state/verification unchanged',CPU_tests=20,
 same_input_pilot_repeat_required=True,new_GPU_calls=0)
out=W/'ROLE_PROBE_SOURCE_MANIFEST_v2.json';assert not out.exists();out.write_text(json.dumps(manifest,indent=2)+'\n')
archive=W/'ROLE_PROBE_SOURCE_v2.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as t:
 for r in files:t.add(F/r['path'],arcname='probe/'+r['path'])
 t.add(out,arcname='probe/SOURCE_MANIFEST.json')
print(json.dumps(dict(commit=commit,files=len(files),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())))

from pathlib import Path
import hashlib,json,subprocess,tarfile
W=Path(__file__).resolve().parent;R=W/'runtime_n5_v2'
for name in ['SOURCE_N5_v2.tar.gz','N5_SOURCE_MANIFEST_v2.json','RUNTIME_N5_v2.bundle']:assert not (W/name).exists()
for key,value in [('user.name','Research Artifact'),('user.email','artifact@example.invalid')]:subprocess.run(['git','-C',str(R),'config',key,value],check=True)
subprocess.run(['git','-C',str(R),'-c','core.whitespace=cr-at-eol','diff','--check'],check=True)
subprocess.run(['git','-C',str(R),'add','src/revtrace/certified_envelope.py','tests/test_envelope_event_driven.py','tests/test_envelope_failure_controls.py'],check=True)
subprocess.run(['git','-C',str(R),'commit','-m','Share event-driven ingress fixed point and stale-ACK fencing across safe controls'],check=True)
git=lambda *args:subprocess.check_output(['git','-C',str(R),*args])
commit=git('rev-parse','HEAD').decode().strip();files=[]
for name in git('ls-files','-z').decode().split('\0'):
    if not name:continue
    data=(R/name).read_bytes();assert git('cat-file','blob','HEAD:'+name)==data
    files.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
manifest=dict(code_commit=commit,base_runtime='49557578b35f4ab6d9cd54bc58d09990032de51d',files=files,
    scope='common engineering optimization, all strong baselines equally equipped; not new C2 performance evidence')
(W/'N5_SOURCE_MANIFEST_v2.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(W/'SOURCE_N5_v2.tar.gz','w:gz') as t:
    for r in files:t.add(R/r['path'],arcname='runtime/'+r['path'])
    t.add(W/'N5_SOURCE_MANIFEST_v2.json',arcname='runtime/SOURCE_MANIFEST.json')
subprocess.run(['git','-C',str(R),'bundle','create',str(W/'RUNTIME_N5_v2.bundle'),'HEAD'],check=True)
print(json.dumps(dict(commit=commit,files=len(files),archive_sha256=hashlib.sha256((W/'SOURCE_N5_v2.tar.gz').read_bytes()).hexdigest())))

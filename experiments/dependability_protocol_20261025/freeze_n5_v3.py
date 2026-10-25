from pathlib import Path
import hashlib,json,subprocess,tarfile
W=Path(__file__).resolve().parent;R=W/'runtime_n5_v3'
for name in ['SOURCE_N5_v3.tar.gz','N5_SOURCE_MANIFEST_v3.json','RUNTIME_N5_v3.bundle']:assert not (W/name).exists()
for k,v in [('user.name','Research Artifact'),('user.email','artifact@example.invalid')]:subprocess.run(['git','-C',str(R),'config',k,v],check=True)
subprocess.run(['git','-C',str(R),'switch','-c','codex/n5-recovery-observer-20261026'],check=True)
subprocess.run(['git','-C',str(R),'-c','core.whitespace=cr-at-eol','diff','--check'],check=True)
subprocess.run(['git','-C',str(R),'add','src/revtrace/certified_display.py','scripts/row_delivery_executor.py','scripts/run_tc_live_qwen.py','tests/test_crash_observation.py'],check=True)
subprocess.run(['git','-C',str(R),'commit','-m','Add opt-in paid crash observer for applied views and pre-dispatch row identity'],check=True)
git=lambda *a:subprocess.check_output(['git','-C',str(R),*a]);commit=git('rev-parse','HEAD').decode().strip();files=[]
for name in git('ls-files','-z').decode().split('\0'):
 if not name:continue
 data=(R/name).read_bytes();assert git('cat-file','blob','HEAD:'+name)==data
 files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=dict(code_commit=commit,base_runtime='21d15cb5bf847315f13deca2da2399b3d0577c31',files=files,
 scope='same protected scheduler; optional paid process-SIGKILL observation, not power durability or network ACK')
(W/'N5_SOURCE_MANIFEST_v3.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(W/'SOURCE_N5_v3.tar.gz','w:gz') as t:
 for r in files:t.add(R/r['path'],arcname='runtime/'+r['path'])
 t.add(W/'N5_SOURCE_MANIFEST_v3.json',arcname='runtime/SOURCE_MANIFEST.json')
subprocess.run(['git','-C',str(R),'bundle','create',str(W/'RUNTIME_N5_v3.bundle'),'HEAD'],check=True)
print(json.dumps(dict(commit=commit,files=len(files),archive_sha256=hashlib.sha256((W/'SOURCE_N5_v3.tar.gz').read_bytes()).hexdigest())))

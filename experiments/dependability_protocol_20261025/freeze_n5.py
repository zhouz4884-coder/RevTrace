from pathlib import Path
import hashlib,json,platform,subprocess,sys,tarfile
W=Path(__file__).resolve().parent;R=W/'runtime_n5'
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
base=json.loads((W/'N1_SOURCE_MANIFEST.json').read_text())
intended={'scripts/run_tc_live_qwen.py','src/revtrace/certified_display.py'}
for row in base['files']:
    if row['path'] not in intended:assert hashlib.sha256((R/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
subprocess.run(['git','-C',str(R),'config','user.name','Research Artifact'],check=True)
subprocess.run(['git','-C',str(R),'config','user.email','artifact@example.invalid'],check=True)
subprocess.run(['git','-C',str(R),'-c','core.whitespace=cr-at-eol','diff','--check'],check=True)
paths=['scripts/run_tc_live_qwen.py','src/revtrace/certified_display.py','src/revtrace/certified_envelope.py',
       'src/revtrace/degradation_state.py','src/revtrace/envelope_display.py','src/revtrace/input_debt_journal.py',
       'tests/test_certified_envelope.py','tests/test_envelope_snapshot.py']
subprocess.run(['git','-C',str(R),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(R),'commit','-m','Add certified degradation: atomic input debt, actual view controls and original-clock recovery'],check=True)
commit=git('rev-parse','HEAD').decode().strip();names=git('ls-files','-z').decode().split('\0')
files=[]
for name in names:
    if not name:continue
    data=(R/name).read_bytes();blob=git('cat-file','blob','HEAD:'+name);assert data==blob,name
    files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=dict(code_commit=commit,base_measured_runtime=base['code_commit'],files=files,
    unchanged_admission_and_WAL_core=True,source_scope='N5 live prototype before first GPU pilot')
(W/'N5_SOURCE_MANIFEST_v1.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(W/'SOURCE_N5_v1.tar.gz','w:gz') as t:
    for r in files:t.add(R/r['path'],arcname='runtime/'+r['path'])
    t.add(W/'N5_SOURCE_MANIFEST_v1.json',arcname='runtime/SOURCE_MANIFEST.json')
subprocess.run(['git','-C',str(R),'bundle','create',str(W/'RUNTIME_N5_v1.bundle'),'HEAD'],check=True)
(W/'N5_SOURCE_IDENTITY_v1.json').write_text(json.dumps(dict(code_commit=commit,files=len(files),
    archive_sha256=hashlib.sha256((W/'SOURCE_N5_v1.tar.gz').read_bytes()).hexdigest(),
    python=sys.version,platform=platform.platform(),new_GPU_calls=0),indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=len(files),archive_sha256=hashlib.sha256((W/'SOURCE_N5_v1.tar.gz').read_bytes()).hexdigest())))

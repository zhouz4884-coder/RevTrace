from pathlib import Path
import shutil,subprocess,json,hashlib
W=Path(__file__).resolve().parent;D=W/'s0_source_v1';assert not D.exists();D.mkdir()
names=['PROTOCOL.md','scan_historical_views.py']
for name in names:shutil.copyfile(W/name,D/name)
def git(*args):return subprocess.check_output(['git','-C',str(D),*args])
git('init','-b','codex/legal-progress-scan');git('config','core.autocrlf','false');git('add','--',*names)
git('-c','user.name=Research Artifact','-c','user.email=artifact@example.invalid','-c','commit.gpgsign=false','commit','-m','Freeze LP1 host-time historical selection scan')
record=dict(code_commit=git('rev-parse','HEAD').decode().strip(),baseline_runtime='b8aa802c687256d3801612dc8bee585ee849ddea',
    files=[dict(path=name,sha256=hashlib.sha256((D/name).read_bytes()).hexdigest()) for name in names])
(W/'SCAN_SOURCE_v1.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))

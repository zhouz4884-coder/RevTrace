from pathlib import Path
import shutil,subprocess,json,hashlib
W=Path(__file__).resolve().parent;D=W/'s0_source_v2';assert not D.exists();D.mkdir()
names=['PROTOCOL.md','scan_historical_views_v2.py']
for name in names:shutil.copyfile(W/name,D/name)
def git(*args):return subprocess.check_output(['git','-C',str(D),*args])
git('init','-b','codex/legal-progress-scan-v2');git('config','core.autocrlf','false');git('add','--',*names)
git('-c','user.name=Research Artifact','-c','user.email=artifact@example.invalid','-c','commit.gpgsign=false','commit','-m','Freeze LP1 consumer and host-registry opportunity crosscheck')
record=dict(code_commit=git('rev-parse','HEAD').decode().strip(),baseline_runtime='b8aa802c687256d3801612dc8bee585ee849ddea',
    studies=['CK5 six stage136 attempts','original N5 formal105 normal and21 cold recovery +2 development'],
    evidence='CPU replay; conservative and permissive consumer cuts; unpublished host-registry reauthorization upper bounds; no new model calls',
    files=[dict(path=name,sha256=hashlib.sha256((D/name).read_bytes()).hexdigest()) for name in names])
(W/'SCAN_SOURCE_v2.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))

"""Pre-result static correction to the new report glue; no metric change."""
from pathlib import Path
import hashlib,json,subprocess
H=Path(__file__).resolve().parent;S=H/'combined_source_v2'
subprocess.run(['git','clone','-c','core.autocrlf=false','--quiet',str(H/'combined_source_v1'),str(S)],check=True)
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
git('checkout','-b','codex/midpoint-four-point-report-v2')
p=S/'summarize_48.py';text=p.read_text(encoding='utf8');old='**{k:r.get(k) for k in ENDPOINTS},';new="**{k:r.get(k) for k in ENDPOINTS if not k.startswith(('compatible_','incompatible_','UNKNOWN_'))},";assert text.count(old)==1;p.write_text(text.replace(old,new),encoding='utf8',newline='\n')
p=S/'plot_48.py';b=p.read_bytes();assert b'deficit\\n' in b;p.write_bytes(b.replace(b'deficit\\n',b'deficit\n'))
git('add','.');git('commit','-m','Keep secondary keys distinct from primary metrics and fix line-break label')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=dict(code_commit=git('rev-parse','HEAD'),scope='Pre-result report glue correction only; no neural, core, timely definition or witness change',files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()])
with (H/'COMBINED_SOURCE_v2.json').open('x',encoding='utf8') as f:json.dump(m,f,indent=2);f.write('\n')
git('bundle','create',str(H/'COMBINED_SOURCE_v2.bundle'),'HEAD');assert not git('status','--porcelain','--untracked-files=all')
print(json.dumps(dict(code_commit=m['code_commit'],manifest_sha256=sha(H/'COMBINED_SOURCE_v2.json'))))

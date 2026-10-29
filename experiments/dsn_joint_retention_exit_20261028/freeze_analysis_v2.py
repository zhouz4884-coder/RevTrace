from pathlib import Path
import hashlib,json,subprocess
here=Path(__file__).resolve().parent;root=here/'analysis_source_v2'
def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
git('add','.');git('commit','-m','Check original and materialized fixture identities without conflating JSON serialization')
m=dict(code_commit=git('rev-parse','HEAD'),scope='Independent CPU recount repair: original fixture byte hash plus materialized byte hash and complete object equality; no neural execution changes',files=[dict(path=n,bytes=(root/n).stat().st_size,sha256=hashlib.sha256((root/n).read_bytes()).hexdigest()) for n in git('ls-files').splitlines()])
with (here/'ANALYSIS_SOURCE_v2.json').open('x',encoding='utf8') as f:json.dump(m,f,indent=2);f.write('\n')
git('bundle','create',str(here/'ANALYSIS_SOURCE_v2.bundle'),'HEAD');assert not git('status','--porcelain','--untracked-files=all')
print(json.dumps(m))

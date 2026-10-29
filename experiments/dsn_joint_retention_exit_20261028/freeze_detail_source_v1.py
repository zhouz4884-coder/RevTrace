from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent
root=here/'detail_source_v1';root.mkdir(exist_ok=False)
shutil.copyfile(here/'audit_presence_consumer_v1.py',root/'audit_presence_consumer_v1.py')
(root/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
(root/'PROTOCOL.md').write_text('Independent CPU-only actual-input evidence-presence audit and exact Owner-to-Consumer event linkage, complementing frozen aa4e recount. Missing actual audits may not count as equality. Preserve every cell; retain F2 vs unmodified lawful-pressure separation. Run only after 24-cell execution and frozen recount completion, with no timed GPU sharing IO. No neural calls or policy changes.\n',encoding='utf8')
subprocess.run(['git','-C',str(root),'init'],check=True,capture_output=True)
def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
git('config','core.autocrlf','false');git('checkout','-b','codex/dsn-joint-actual-input-consumer-v1')
git('add','.');git('commit','-m','Freeze complete actual input presence and Consumer linkage audit')
manifest=dict(code_commit=git('rev-parse','HEAD'),scope='Independent CPU-only actual-input and actual-Consumer linkage audit',files=[dict(path=n,bytes=(root/n).stat().st_size,sha256=hashlib.sha256((root/n).read_bytes()).hexdigest()) for n in git('ls-files').splitlines()])
with (here/'DETAIL_SOURCE_v1.json').open('x',encoding='utf8') as stream:json.dump(manifest,stream,indent=2);stream.write('\n')
git('bundle','create',str(here/'DETAIL_SOURCE_v1.bundle'),'HEAD');assert not git('status','--porcelain','--untracked-files=all')
print(json.dumps(manifest))

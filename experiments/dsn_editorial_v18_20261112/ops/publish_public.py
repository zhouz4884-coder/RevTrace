"""Publish only bounded v18 editorial records; manuscript and diff stay private."""
from pathlib import Path
import hashlib,json,re,subprocess
E=Path(__file__).resolve().parents[1];W=Path('C:/Users/LENOVO/.codex/worktrees/revtrace-dsn-evidence/RevTrace');prefix='experiments/'+E.name+'/'
def git(*a):return subprocess.check_output(['git','-c','http.version=HTTP/1.1','-C',str(W),*a],stderr=subprocess.PIPE)
for line in git('status','--porcelain').decode().splitlines():
 assert line[3:].startswith(prefix),line
base=git('rev-parse','HEAD').decode().strip();assert git('ls-remote','origin','refs/heads/main').split()[0].decode()==base
if git('branch','--show-current').decode().strip()!='codex/v18-editorial-delivery':
 git('switch','-c','codex/v18-editorial-delivery')
(E/'.gitattributes').write_bytes(b'* -text\n')
exclude={'V17_TO_V18_SOURCE.patch','ops/publish_private.py','PUBLIC_GITHUB_RECEIPT.json','PUBLICATION_MANIFEST.json'}
rows=[]
for p in sorted(E.rglob('*')):
 if not p.is_file()or'__pycache__'in p.parts:continue
 n=p.relative_to(E).as_posix()
 if n in exclude:continue
 b=p.read_bytes();assert len(b)<2_000_000,n
 assert p.suffix not in {'.pdf','.zip','.png','.jpg','.bundle'},n
 t=b.decode('utf8')
 for pattern in [r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'hf_[A-Za-z0-9]{25,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----']:assert not re.search(pattern,t),n
 q=W/prefix/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
 rows.append(dict(path=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
manifest=dict(record_type='V18_BOUNDED_EDITORIAL_DELIVERY_NOT_NEW_EXPERIMENT',files=rows,file_count=len(rows),bytes=sum(x['bytes']for x in rows),preserved_v17_pdf_sha256=json.loads((E/'BASE_V17_MANIFEST.json').read_bytes())['pdf_sha256'],manuscript_private_commit=json.loads((E/'PRIVATE_GITHUB_RECEIPT.json').read_bytes())['commit'],excluded_private_diff_and_operator=True,new_GPU_experiments=0)
raw=(json.dumps(manifest,indent=2)+'\n').encode();(W/prefix/'PUBLICATION_MANIFEST.json').write_bytes(raw);(E/'PUBLICATION_MANIFEST.json').write_bytes(raw)
git('add',prefix)
git('add','--renormalize',prefix)
changed=[x.decode()for x in git('diff','--cached','--name-only','-z').split(b'\0')if x];assert all(x.startswith(prefix)for x in changed)
for row in rows:
 b=git('show',':'+prefix+row['path']);assert len(b)==row['bytes']and hashlib.sha256(b).hexdigest()==row['sha256']
assert git('show',':'+prefix+'PUBLICATION_MANIFEST.json')==raw
assert not any(x.startswith(b'160000 ')for x in git('ls-files','--stage',prefix).splitlines())
git('commit','-m','Archive v18 editorial revision, preserved v17 identity, and reproducibility checks')
commit=git('rev-parse','HEAD').decode().strip();assert not git('status','--porcelain')
git('push','origin','HEAD:main');assert git('ls-remote','origin','refs/heads/main').split()[0].decode()==commit
receipt=dict(status='PASS_PUBLIC_V18_BOUNDED_RECORDS_INDEX_BLOBS_PUSH_AND_REMOTE_HEAD',repository='https://github.com/zhouz4884-coder/RevTrace',commit=commit,tree=git('rev-parse','HEAD^{tree}').decode().strip(),file_count=len(rows)+1,payload_bytes=manifest['bytes'],manifest_sha256=hashlib.sha256(raw).hexdigest(),private_manuscript_commit=manifest['manuscript_private_commit'],legacy_dirty_checkout_untouched=True)
(E/'PUBLIC_GITHUB_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(json.dumps(receipt))

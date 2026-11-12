"""Publish bounded amendment notes and only authorized older-paper deletions."""
from pathlib import Path
import hashlib,json,re,subprocess
E=Path(__file__).resolve().parents[1];W=Path('C:/Users/LENOVO/.codex/worktrees/revtrace-dsn-evidence/RevTrace');prefix='experiments/'+E.name+'/'
def git(*a):return subprocess.check_output(['git','-c','http.version=HTTP/1.1','-C',str(W),*a],stderr=subprocess.PIPE)
def names(*a):return {x.decode()for x in git(*a).split(b'\0')if x}
plan=json.loads((E/'CLEANUP_PLAN.json').read_bytes());root=str(W/'Paper_DSN/revisions').lower()
allowed={x['name']for x in plan['targets']if x['revision_root'].lower()==root}
def allowed_delete(n):
 parts=n.split('/');return len(parts)>3 and parts[:2]==['Paper_DSN','revisions']and parts[2]in allowed
deletes={n for n in names('ls-tree','-r','--name-only','-z','HEAD','--','Paper_DSN/revisions')if allowed_delete(n)}
assert deletes and all(not(W/n).exists()for n in deletes)
changes=names('diff','--no-renames','--name-only','-z')|names('diff','--cached','--no-renames','--name-only','-z')
assert all(n.startswith(prefix)or allowed_delete(n)for n in changes)
base=git('rev-parse','HEAD').decode().strip();assert git('ls-remote','origin','refs/heads/main').split()[0].decode()==base
if git('branch','--show-current').decode().strip()!='codex/v18-amendment-cleanup':git('switch','-c','codex/v18-amendment-cleanup')
(E/'.gitattributes').write_bytes(b'* -text\n')
exclude={'V17_TO_V18_SOURCE.patch','ops/publish_private.py','PUBLIC_GITHUB_RECEIPT.json','PUBLICATION_MANIFEST.json'};rows=[]
for p in sorted(E.rglob('*')):
 if not p.is_file()or'__pycache__'in p.parts:continue
 n=p.relative_to(E).as_posix()
 if n in exclude:continue
 b=p.read_bytes();assert len(b)<3_000_000 and p.suffix not in {'.pdf','.zip','.png','.jpg','.bundle'},n
 for pattern in [r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'hf_[A-Za-z0-9]{25,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----']:assert not re.search(pattern,b.decode('utf8')),n
 q=W/prefix/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);rows.append(dict(path=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
manifest=dict(record_type='V18_AMENDMENT_AND_AUTHORIZED_PAPER_CLEANUP',files=rows,file_count=len(rows),bytes=sum(x['bytes']for x in rows),removed_tracked_paper_files=sorted(deletes),new_GPU_experiments=0,experiment_data_removed=False,git_history_rewritten=False,private_commit=json.loads((E/'PRIVATE_GITHUB_RECEIPT.json').read_bytes())['commit'])
raw=(json.dumps(manifest,indent=2)+'\n').encode();(W/prefix/'PUBLICATION_MANIFEST.json').write_bytes(raw);(E/'PUBLICATION_MANIFEST.json').write_bytes(raw)
git('add',prefix);git('add','--renormalize',prefix);git('add','--update','--','Paper_DSN/revisions')
staged=names('diff','--cached','--no-renames','--name-only','-z');assert all(n.startswith(prefix)or allowed_delete(n)for n in staged)
assert names('diff','--cached','--no-renames','--name-only','--diff-filter=D','-z')==deletes
for row in rows:
 b=git('show',':'+prefix+row['path']);assert len(b)==row['bytes']and hashlib.sha256(b).hexdigest()==row['sha256'],row['path']
assert git('show',':'+prefix+'PUBLICATION_MANIFEST.json')==raw
git('commit','-m','Amend v18 evidence accounting and remove pre-v15 manuscript revisions')
commit=git('rev-parse','HEAD').decode().strip();assert not git('status','--porcelain')
git('push','origin','HEAD:main');assert git('ls-remote','origin','refs/heads/main').split()[0].decode()==commit
receipt=dict(status='PASS_AMENDED_V18_RECORDS_AND_AUTHORIZED_OLD_PAPER_DELETIONS_PUSHED',repository='https://github.com/zhouz4884-coder/RevTrace',commit=commit,tree=git('rev-parse','HEAD^{tree}').decode().strip(),public_record_files=len(rows)+1,removed_old_paper_files=len(deletes),manifest_sha256=hashlib.sha256(raw).hexdigest(),private_manuscript_commit=manifest['private_commit'],experiment_data_removed=False,git_history_rewritten=False)
(E/'PUBLIC_GITHUB_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(json.dumps(receipt))

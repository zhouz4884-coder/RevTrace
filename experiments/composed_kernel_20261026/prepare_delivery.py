"""Manifest-only public research packaging. Never stages the dirty root tree."""
from pathlib import Path
import shutil,json,hashlib,re,subprocess,tarfile
W=Path(__file__).resolve().parent
old=W.parent/'dependability_protocol_20261025/git_delivery_checkpoint_v1'
dest=W/'git_delivery_final_v1'
if not dest.exists():
    subprocess.run(['git','clone','--no-checkout',str(old),str(dest)],check=True)
else:
    assert subprocess.check_output(['git','-C',str(dest),'rev-parse','HEAD'],text=True).strip()=='5e8e1e0868356465aac40bfe75b59ca9d13453a4'
subprocess.run(['git','-C',str(dest),'remote','set-url','origin','https://github.com/zhouz4884-coder/RevTrace.git'],check=True)
prefix=Path('experiments/composed_kernel_20261026');target=dest/prefix
if target.exists():assert not any(target.iterdir())
else:target.mkdir(parents=True)
files=[]
for f in W.iterdir():
    if not f.is_file():continue
    if f.suffix in ['.py','.md','.json','.xml','.log','.sh'] and f.name!='remote_ops.py':files.append(f)
    elif f.name in ['.gitattributes','SOURCE_v6.tar.gz','RUNTIME_CK5_v6.bundle','BOUNDED_EVIDENCE_v1.tar.gz']:files.append(f)
files+=list((W/'analysis_v1').glob('*'))
manifest=json.loads((W/'SOURCE_v6.json').read_text())
source=manifest
files += [W/'runtime'/r['path'] for r in source['files']]
patterns=[re.compile(rb'ghp_[A-Za-z0-9]{30,}'),re.compile(rb'github_pat_[A-Za-z0-9_]{30,}'),
          re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
rows=[]
for f in sorted(set(files)):
    rel=f.relative_to(W);raw=f.read_bytes()
    assert len(raw)<60_000_000
    assert not any(p.search(raw) for p in patterns),('secret-shaped bytes',str(rel))
    out=target/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,out)
    assert out.read_bytes()==raw
    rows.append(dict(path=rel.as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
raw=(W/'SOURCE_v6.json').read_bytes()
shutil.copyfile(W/'SOURCE_v6.json',target/'runtime/SOURCE_MANIFEST.json')
rows.append(dict(path='runtime/SOURCE_MANIFEST.json',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
for name in ['SOURCE_v6.tar.gz','BOUNDED_EVIDENCE_v1.tar.gz']:
    with tarfile.open(target/name,'r:gz') as t:
        for m in t.getmembers():
            if not m.isfile():continue
            raw=t.extractfile(m).read()
            assert not any(p.search(raw) for p in patterns),('secret-shaped archive member',name,m.name)
record=dict(status='BOUNDED_PUBLIC_RESEARCH_PACKAGE',files=rows,
    excludes=['dirty root tree','manuscripts','weights','audio','large raw traces','credentials','operations','CPU fixture temporary trees'],
    source_commit=source['code_commit'],raw_archive_sha256=json.loads((W/'BOUNDED_METADATA_v1.json').read_text())['archive_sha256'])
(target/'DELIVERY_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n')
(W/'DELIVERY_PREPARATION_v1.json').write_text(json.dumps(dict(status='PREPARED_NOT_YET_PUSHED',
    delivery_clone=str(dest),prefix=prefix.as_posix(),files=len(rows)+1,
    manifest_sha256=hashlib.sha256((target/'DELIVERY_MANIFEST.json').read_bytes()).hexdigest()),indent=2)+'\n')
print(json.dumps(dict(status='PREPARED_NOT_PUSHED',files=len(rows)+1,bytes=sum(r['bytes'] for r in rows))))

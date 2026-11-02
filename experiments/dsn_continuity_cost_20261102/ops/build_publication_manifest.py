"""Bounded final publication inventory; excludes caches, raw banks and draft renders."""
from pathlib import Path
import hashlib,json,re,zipfile
E=Path(__file__).resolve().parents[1];R=E.parents[1]
paper=R/'Paper_DSN/revisions/20261102_dsn2027_release_v10'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
gate=json.loads((E/'FINAL_RELEASE_GATE.json').read_bytes())
assert gate['final_pdf_sha256']==sha(paper/'main.pdf')
assert gate['source_zip_sha256']==sha(paper/'RevTrace_DSN2027_anonymous_source_v10.zip')
qa=json.loads((E/'paper_qa/FINAL_QA.json').read_bytes());assert sha(E/'paper_qa/FINAL_QA.json')==gate['paper_QA_sha256']
prov=json.loads((paper/'PACKAGING_PROVENANCE.json').read_bytes())
for row in prov['inputs']:assert (paper/row['path']).stat().st_size==row['bytes'] and sha(paper/row['path'])==row['sha256']
with zipfile.ZipFile(paper/'RevTrace_DSN2027_anonymous_source_v10.zip') as z:
    for row in prov['inputs']:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
names=[]
for p in E.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(E)
    if '.git' in rel.parts or '__pycache__' in rel.parts:continue
    if p.name.startswith(('PROCESS_PATHS','SYNC_PROGRESS','FINAL_PUBLICATION','DELIVERY_RECEIPT','POST_PUBLICATION')):continue
    if rel.parts[0]=='paper_qa' and len(rel.parts)>1:
        part=rel.parts[1]
        if p.is_file() and (part in {'pre_cost','cold_build_v10'} or
                part.startswith(('final_render_','grayscale_')) and not part.endswith(gate['final_pdf_sha256'][:12])):continue
    names.append(p.relative_to(R).as_posix())
for row in prov['inputs']:names.append((paper/row['path']).relative_to(R).as_posix())
for name in ['.gitattributes','main.pdf','PACKAGING_PROVENANCE.json','RevTrace_DSN2027_anonymous_source_v10.zip']:
    names.append((paper/name).relative_to(R).as_posix())
names+=['Paper_DSN/CURRENT.md','experiments/LATEST_RESEARCH.json']
names=sorted(set(names));rows=[]
patterns=[rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{50,}',rb'hf_[A-Za-z0-9]{30,}']
for name in names:
    p=R/name;b=p.read_bytes();assert len(b)<20_000_000
    assert p.suffix.lower() not in {'.safetensors','.pt','.ckpt','.wav','.flac','.pyc'}
    if p.suffix.lower() in {'.md','.txt','.json','.csv','.tex','.bib'}:
        assert not any(re.search(pat,b) for pat in patterns),'Credential-shaped content: '+name
    rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
record=dict(scope='Only bounded research/source/config/summary/QA and isolatedv10 manuscript; no dirty legacy paper/runtime import.',files=len(rows),bytes=sum(r['bytes'] for r in rows),paper_pdf_sha256=gate['final_pdf_sha256'],source_zip_sha256=gate['source_zip_sha256'],raw_banks_models_environments_on8TB=True,rows=rows)
target=E/'FINAL_PUBLICATION_MANIFEST.json';assert not target.exists();target.write_bytes((json.dumps(record,indent=2)+'\n').encode())
paths=E/'FINAL_PUBLICATION_PATHS.json';assert not paths.exists()
paths.write_bytes((json.dumps(names+[target.relative_to(R).as_posix()],indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in record.items() if k!='rows'}))

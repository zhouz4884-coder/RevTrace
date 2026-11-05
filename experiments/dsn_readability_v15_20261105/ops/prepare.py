from pathlib import Path
import hashlib,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];OLD=R/'Paper_DSN/revisions/20261104_dsn2027_release_v14';NEW=R/'Paper_DSN/revisions/20261105_dsn2027_release_v15'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not NEW.exists();assert sha(OLD/'main.pdf')=='5462d73d98a711d94f04e852a1bfd028ed34cce1cf0aefd86a56418bec37d581'
for n in ['baseline','inputs','paper_qa','packages']:(E/n).mkdir(exist_ok=True)
protected=[]
for p in OLD.rglob('*'):
 if p.is_file() and (p.suffix in {'.tex','.bib','.pdf','.svg','.zip'} or p.name in {'.gitattributes','README.md','PACKAGING_PROVENANCE.json'}):protected.append(dict(path=p.relative_to(R).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
frozen=R/'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json'
for r in json.loads(frozen.read_bytes())['rows']:assert sha(R/r['path'])==r['sha256']
record=dict(base_commit='3bcbb7638e6d9106965e4274a6c388a0186ab7ee',protected_v14=protected,frozen_v11_manifest_sha256=sha(frozen),legacy_HEAD=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),CURRENT_sha256=sha(R/'experiments/repository_identity_20261027/CURRENT.json'),scope='Language and bounded figure annotation only; scientific evidence frozen',new_model_calls=0)
(E/'baseline/FROZEN.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());NEW.mkdir()
for p in OLD.rglob('*'):
 rel=p.relative_to(OLD)
 if p.is_file() and (p.suffix in {'.tex','.bib'} or (rel.parts[0]=='figures' and p.suffix in {'.pdf','.svg'}) or p.name in {'.gitattributes','README.md'}):
  q=NEW/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
shutil.copyfile(OLD/'RevTrace_DSN2027_anonymous_evidence_v13.zip',NEW/'RevTrace_DSN2027_anonymous_evidence_v13.zip')
for uid,n in [('c702ca7d-c5e9-4065-a434-9c52fcac85c6','EXTERNAL_COMMENTS_1.txt'),('6fe9e5ce-df89-4d3b-8e8a-eddecf3115ac','EXTERNAL_COMMENTS_2.txt')]:shutil.copyfile(Path('C:/Users/LENOVO/.codex/attachments')/uid/'已粘贴的文本.txt',E/'inputs'/n)
(E/'.gitattributes').write_bytes(b'* -text\n');print(json.dumps(dict(new_revision=str(NEW),protected_v14_files=len(protected))))

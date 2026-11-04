from pathlib import Path
import hashlib,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1]
OLD=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13';NEW=R/'Paper_DSN/revisions/20261104_dsn2027_release_v14'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not NEW.exists();assert sha(OLD/'main.pdf')=='1413182663224acb507c2c68080f4dc8d340b2d7dab47a678e2aea39aa941928'
for n in ['baseline','inputs','paper_qa','packages']:(E/n).mkdir(exist_ok=True)
protected=[]
for p in sorted(OLD.rglob('*')):
 if p.is_file() and (p.suffix in {'.tex','.bib','.pdf','.svg','.zip'} or p.name in {'README.md','PACKAGING_PROVENANCE.json','.gitattributes'}):
  protected.append(dict(path=p.relative_to(R).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
frozen=R/'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json'
for r in json.loads(frozen.read_bytes())['rows']:assert sha(R/r['path'])==r['sha256']
record=dict(base_commit='1f841da127d7bba5cead8b129da25da56a50b0eb',legacy_HEAD=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),protected_v13=protected,frozen_v11_manifest_sha256=sha(frozen),CURRENT_sha256=sha(R/'experiments/repository_identity_20261027/CURRENT.json'),new_model_calls=0)
(E/'baseline/FROZEN.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
NEW.mkdir()
for p in OLD.rglob('*'):
 rel=p.relative_to(OLD)
 if p.is_file() and (p.suffix in {'.tex','.bib'} or (rel.parts[0]=='figures' and p.suffix in {'.pdf','.svg'}) or p.name in {'README.md','.gitattributes'}):
  q=NEW/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
# Reuse the already checked companion with its original v13 identity and bytes.
shutil.copyfile(OLD/'RevTrace_DSN2027_anonymous_evidence_v13.zip',NEW/'RevTrace_DSN2027_anonymous_evidence_v13.zip')
for src,name in [('E:/Downloads/RevTrace_v13_Reviewer_Audit_and_Revision_1f841da.md','REVIEW_PLAN.md'),('C:/Users/LENOVO/.codex/attachments/5bcbc4c6-9fc4-4753-b8a1-d40b3cd87162/已粘贴的文本.txt','EXTERNAL_COMMENTS_1.txt'),('C:/Users/LENOVO/.codex/attachments/94741a8e-a1bc-42a0-a6e3-f7f21edca3bb/已粘贴的文本.txt','EXTERNAL_COMMENTS_2.txt')]:shutil.copyfile(src,E/'inputs'/name)
(E/'.gitattributes').write_bytes(b'* -text\n')
print(json.dumps(dict(revision=str(NEW),protected_files=len(protected),method_changed=False)))

"""Create an isolated manuscript revision from verified v9 inputs."""
from pathlib import Path
import hashlib,json,shutil
E=Path(__file__).resolve().parents[1];R=E.parents[1]
old=R/'Paper_DSN/revisions/20261101_dsn2027_release_v9'
new=R/'Paper_DSN/revisions/20261102_dsn2027_release_v10'
assert not new.exists();new.mkdir()
copied=[]
for p in sorted(old.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(old)
    keep=p.suffix.lower() in {'.tex','.bib','.sty','.cls'} or (rel.parts[0] in {'figures','tables'} and p.suffix.lower() in {'.pdf','.png','.svg','.eps'}) or p.name=='.latexmkrc'
    if not keep:continue
    q=new/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    assert q.read_bytes()==p.read_bytes()
    copied.append(dict(path=rel.as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
record=dict(baseline=str(old.relative_to(R)),revision=str(new.relative_to(R)),
    baseline_pdf_sha256=hashlib.sha256((old/'main.pdf').read_bytes()).hexdigest(),
    source_inputs=copied,scope='Isolated v10 inputs; v9 and legacy manuscripts preserved; no new experiment numbers inserted.')
target=E/'MANUSCRIPT_BASELINE_v10.json';assert not target.exists();target.write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(dict(new_revision=str(new),copied_files=len(copied),baseline_pdf_sha256=record['baseline_pdf_sha256'])))

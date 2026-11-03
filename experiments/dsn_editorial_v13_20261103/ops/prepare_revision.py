"""Start an editorial revision without modifying a frozen experiment or release."""
from pathlib import Path
import hashlib, json, shutil, subprocess
from datetime import datetime, timezone

E = Path(__file__).resolve().parents[1]
R = E.parents[1]
OLD = R / 'Paper_DSN/revisions/20261102_dsn2027_release_v12'
NEW = R / 'Paper_DSN/revisions/20261103_dsn2027_release_v13'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not NEW.exists(), 'Do not overwrite an existing revision'
assert sha(OLD / 'main.pdf') == 'a9083a908c345003ca0c7f87a23bdb8c647c8350fd74c1ebbeefbcf9f99dbbd9'
for name in ['baseline', 'review', 'paper_qa', 'inputs', 'figures', 'packages']:
    (E / name).mkdir(exist_ok=True)
rows = []
for p in sorted(OLD.rglob('*')):
    if p.is_file() and (p.suffix in {'.tex', '.bib', '.pdf', '.zip'} or p.name in {'README.md', 'PACKAGING_PROVENANCE.json'}):
        rows.append(dict(path=p.relative_to(R).as_posix(), bytes=p.stat().st_size, sha256=sha(p)))
frozen = json.loads((R / 'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json').read_bytes())
for row in frozen['rows']:
    p = R / row['path']
    assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], row['path']
record = dict(utc=datetime.now(timezone.utc).isoformat(), baseline_release='v12',
              verified_delivery_commit='1268e587b1ff71ab539fc6a353137c355885a859',
              legacy_root_head=subprocess.check_output(['git', '-C', str(R), 'rev-parse', 'HEAD'], text=True).strip(),
              frozen_v12_files=rows, frozen_v11_manifest_sha256=sha(R / 'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json'),
              frozen_v11_verified_files=len(frozen['rows']), new_model_calls=0,
              scope='Writing, vector figures and checks only; no experiment or model changes')
(E / 'baseline/FROZEN_INPUTS.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
NEW.mkdir()
for p in sorted(OLD.rglob('*')):
    rel = p.relative_to(OLD)
    if p.is_file() and (p.suffix in {'.tex', '.bib'} or (rel.parts[0] == 'figures' and p.suffix == '.pdf') or p.name == 'README.md'):
        target = NEW / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
shutil.copyfile('E:/Downloads/RevTrace_v12_Final_Editorial_Revision_Plan.md', E / 'inputs/EXTERNAL_REVISION_PLAN.md')
shutil.copyfile('C:/Users/LENOVO/.codex/attachments/2705c9c5-a386-4008-97a4-33ddf98c09aa/已粘贴的文本.txt', E / 'inputs/EXTERNAL_EDITORIAL_COMMENTS.zh.txt')
print(json.dumps(dict(new_release=str(NEW), frozen_v12_files=len(rows), frozen_v11_files=len(frozen['rows']))))

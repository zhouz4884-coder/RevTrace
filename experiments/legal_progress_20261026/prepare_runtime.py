from pathlib import Path
import shutil,json,hashlib
W=Path(__file__).resolve().parent;B=W.parent/'composed_kernel_20261026';E=W.parent/'evidence_retirement_20261026/execution_v4'
dest=W/'runtime';assert not dest.exists();dest.mkdir();source=json.loads((B/'SOURCE_v6.json').read_text());rows=[]
for r in source['files']:
    old=B/'runtime'/r['path'];assert hashlib.sha256(old.read_bytes()).hexdigest()==r['sha256']
    selected=E/'runtime'/r['path'] if r['path']=='src/revtrace/composed_kernel.py' else old
    out=dest/r['path'];out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(selected,out)
    rows.append(dict(path=r['path'],baseline_sha256=r['sha256'],current_sha256=hashlib.sha256(out.read_bytes()).hexdigest()))
(W/'INITIAL_SOURCE_IDENTITY.json').write_text(json.dumps(dict(status='BYTE_VERIFIED_INDEPENDENT_RUNTIME',base=source['code_commit'],
    sealed_core_from_ER1='b4a4502dfcf796b3c509b81ecb93312bcace51e2',files=rows),indent=2)+'\n')
print(json.dumps(dict(files=len(rows),changed_from_CK5=[r['path'] for r in rows if r['baseline_sha256']!=r['current_sha256']])))

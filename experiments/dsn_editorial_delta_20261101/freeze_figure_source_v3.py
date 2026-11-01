"""Freeze one editorial-only renderer; no measured-data rendering here."""
from pathlib import Path
import hashlib,json,subprocess,sys
E=Path(__file__).resolve().parent;R=E.parents[1];S=E/'figure_source_v3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not (S/'.git').exists()
subprocess.run(['git','init','-b','codex/dsn-editorial-figures-20261101-v3',str(S)],check=True,capture_output=True)
git('config','core.autocrlf','false');git('config','user.name','RevTrace artifact');git('config','user.email','artifact@revtrace.invalid')
git('add','.');git('commit','-m','Freeze editorial-only figure refinement with immutable v7 values')
c=git('rev-parse','HEAD');assert not git('status','--porcelain','--untracked-files=all')
rows=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()]
m=E/'FIGURE_SOURCE_v3.json';assert not m.exists();m.write_bytes((json.dumps(dict(code_commit=c,source_commit=c,scope='Editorial-only plotting; no actual interval reader included',files=rows),indent=2)+'\n').encode())
bundle=E/'FIGURE_SOURCE_v3.bundle';git('bundle','create',str(bundle),'HEAD')
subprocess.run(['git','-C',str(R),'bundle','verify',str(bundle)],check=True,capture_output=True)
subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/codex/execution/dsn-editorial-figures-20261101-v3'],check=True,capture_output=True)
snapshot=E/'figure_snapshot_v3';snapshot.mkdir()
for row in rows:
 p=snapshot/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((S/row['path']).read_bytes())
sys.path.insert(0,str(S));from render_editorial_figures import environment
env=E/'FIGURE_ENVIRONMENT_v3.json';env.write_bytes((json.dumps(environment(),indent=2)+'\n').encode())
d=dict(status='READY_FOR_ROOT_SOURCE_GATE',source_root=str(S),source_commit=c,source_manifest=str(m),source_manifest_sha256=sha(m),bundle_sha256=sha(bundle),files=len(rows),environment=str(env),environment_sha256=sha(env),frozen_config=str(S/'CONFIG.json'),frozen_config_sha256=sha(S/'CONFIG.json'),intended_results=str(E/'FIGURES_v3'),intended_summary=str(E/'FIGURES_v3/SUMMARY.json'),intended_gate=str(E/'FIGURES_v3/GATE.json'),new_model_calls=0,actual_reader_calls=0)
(E/'FIGURE_FREEZE_v3.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(d))

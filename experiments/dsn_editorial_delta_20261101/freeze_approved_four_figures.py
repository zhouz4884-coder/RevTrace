"""Freeze the once-approved four-figure source and scenes, without plotting."""
from pathlib import Path
import hashlib,json,subprocess,sys,ast
E=Path(__file__).resolve().parent;R=E.parents[1];S=E/'final_source_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not (S/'.git').exists()
for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
subprocess.run(['git','init','-b','codex/dsn-editorial-approved-figures-20261101',str(S)],check=True,capture_output=True)
git('config','core.autocrlf','false');git('config','user.name','RevTrace artifact');git('config','user.email','artifact@revtrace.invalid')
git('add','.');git('commit','-m','Freeze approved shape-first mechanism and factorial/native statistical figures')
c=git('rev-parse','HEAD');assert not git('status','--porcelain','--untracked-files=all')
rows=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()]
m=E/'FIGURE_SOURCE_FINAL.json';assert not m.exists();m.write_bytes((json.dumps(dict(code_commit=c,source_commit=c,scope='Approved four-figure editorial renderer; no raw reader or neural models',files=rows),indent=2)+'\n').encode())
bundle=E/'FIGURE_SOURCE_FINAL.bundle';git('bundle','create',str(bundle),'HEAD')
subprocess.run(['git','-C',str(R),'bundle','verify',str(bundle)],check=True,capture_output=True)
subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/codex/execution/dsn-editorial-approved-figures-20261101'],check=True,capture_output=True)
snap=E/'figure_snapshot_final';snap.mkdir()
for row in rows:
 p=snap/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((S/row['path']).read_bytes())
sys.path.insert(0,str(S));from render import environment
env=E/'FIGURE_ENVIRONMENT_FINAL.json';env.write_bytes((json.dumps(environment(),indent=2)+'\n').encode())
d=dict(status='READY_FOR_ROOT_SOURCE_GATE',source_root=str(S),source_commit=c,source_manifest=str(m),source_manifest_sha256=sha(m),bundle_sha256=sha(bundle),files=len(rows),environment=str(env),environment_sha256=sha(env),frozen_config=str(S/'CONFIG.json'),frozen_config_sha256=sha(S/'CONFIG.json'),scene_sha256=sha(S/'SCENE.json'),palette_sha256=sha(S/'COLOUR_SCENE.json'),intended_results=str(E/'FIGURES_FINAL'),intended_summary=str(E/'FIGURES_FINAL/SUMMARY.json'),intended_gate=str(E/'FIGURES_FINAL/GATE.json'),new_model_calls=0,actual_reader_calls=0)
(E/'FIGURE_FREEZE_FINAL.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(d))

"""Freeze independent artwork code and pin all bounded original inputs."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
E=Path(__file__).resolve().parent;R=E.parents[1];S=E/'figure_source_dev'
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
assert not (S/'.git').exists()
subprocess.run(['git','init','-b','codex/dsn-story-figures-20261031',str(S)],check=True,capture_output=True)
git('config','core.autocrlf','false');git('config','user.name','RevTrace artifact');git('config','user.email','artifact@revtrace.invalid')
git('add','.');git('commit','-m','Freeze DSN story figures and actual same-input interval extraction')
commit=git('rev-parse','HEAD');assert not git('status','--porcelain','--untracked-files=all')
files=[]
for name in git('ls-files').splitlines():
 data=(S/name).read_bytes();files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=E/'FIGURE_SOURCE_v1.json';assert not manifest.exists()
manifest.write_bytes((json.dumps(dict(code_commit=commit,source_commit=commit,scope='Independent CPU writing renderer and retrospective bounded interval extraction; no new neural runs',files=files),indent=2)+'\n').encode())
bundle=E/'FIGURE_SOURCE_v1.bundle';git('bundle','create',str(bundle),'HEAD')
subprocess.run(['git','-C',str(R),'bundle','verify',str(bundle)],check=True,capture_output=True)
subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/codex/execution/dsn-story-figures-v1'],check=True,capture_output=True)
snapshot=E/'figure_snapshot_v1';snapshot.mkdir()
for row in files:
 dest=snapshot/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((S/row['path']).read_bytes())
sys.path.insert(0,str(S))
from render_story_figures import environment
env=E/'FIGURE_ENVIRONMENT_v1.json';assert not env.exists();env.write_bytes((json.dumps(environment(),indent=2)+'\n').encode())
record=dict(status='FROZEN_READY_FOR_ROOT_NOARG_NOT_EXECUTED',actual_source_commit=commit,
 source_root=str(S),source_manifest=str(manifest),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
 bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),files=len(files),
 frozen_config=str(S/'CONFIG.json'),frozen_config_sha256=hashlib.sha256((S/'CONFIG.json').read_bytes()).hexdigest(),
 environment=str(env),environment_sha256=hashlib.sha256(env.read_bytes()).hexdigest(),
 intended_outputs=str(E/'FIGURES_v1'),intended_summary=str(E/'FIGURES_v1/SUMMARY.json'),intended_gate=str(E/'FIGURES_v1/GATE.json'),
 raw_input_location='Byte-pinned bounded extracts, original actual service raw on designated8TB disk',new_model_calls=0)
(E/'FIGURE_FREEZE_v1.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(record))

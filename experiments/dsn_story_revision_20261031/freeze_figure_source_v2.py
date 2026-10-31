"""Freeze the pure replot separately from actual73026 interval analysis."""
from pathlib import Path
import hashlib,json,subprocess,sys
E=Path(__file__).resolve().parent;R=E.parents[1];S=E/'figure_source_v2'
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
git('add','.');git('commit','-m','Replot frozen interval data with clear matrix spacing and actual Joint miss')
commit=git('rev-parse','HEAD');assert not git('status','--porcelain','--untracked-files=all')
files=[]
for name in git('ls-files').splitlines():
 data=(S/name).read_bytes();files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=E/'FIGURE_SOURCE_v2.json';assert not manifest.exists()
manifest.write_bytes((json.dumps(dict(code_commit=commit,source_commit=commit,
 scope='Pure figure replot; actual interval extraction remains73026; no actual14-input reader invocation',files=files),indent=2)+'\n').encode())
bundle=E/'FIGURE_SOURCE_v2.bundle';git('bundle','create',str(bundle),'HEAD')
subprocess.run(['git','-C',str(R),'bundle','verify',str(bundle)],check=True,capture_output=True)
subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/codex/execution/dsn-story-figures-v2'],check=True,capture_output=True)
snapshot=E/'figure_snapshot_v2';snapshot.mkdir()
for row in files:
 dest=snapshot/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((S/row['path']).read_bytes())
sys.path.insert(0,str(S));from render_story_figures import environment
env=E/'FIGURE_ENVIRONMENT_v2.json';assert not env.exists();env.write_bytes((json.dumps(environment(),indent=2)+'\n').encode())
record=dict(status='FROZEN_REPLOT_READY_FOR_ROOT_NOARG_NOT_EXECUTED',actual_source_commit=commit,
 actual_interval_analysis_source_commit='73026a11f6db202d723e6028ad85e6833888ec78',
 source_root=str(S),source_manifest=str(manifest),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
 bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),files=len(files),
 frozen_config=str(S/'CONFIG.json'),frozen_config_sha256=hashlib.sha256((S/'CONFIG.json').read_bytes()).hexdigest(),
 environment=str(env),environment_sha256=hashlib.sha256(env.read_bytes()).hexdigest(),
 intended_outputs=str(E/'FIGURES_v2'),intended_summary=str(E/'FIGURES_v2/SUMMARY.json'),intended_gate=str(E/'FIGURES_v2/GATE.json'),
 raw_input_location='Frozen bounded measurement copies and previously completed73026 interval data',new_model_calls=0,
 actual_real_input_reader_repeated=False)
(E/'FIGURE_FREEZE_v2.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record))

"""Text-only final figure revision after independent cold reads; no data analysis."""
from pathlib import Path
import ast,hashlib,json,subprocess,sys
E=Path(__file__).resolve().parent;R=E.parents[1];P=E/'figure_source_v2';S=E/'figure_source_v3'
assert not S.exists()
protected=[dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 for p in sorted((E/'FIGURES_v2').iterdir()) if p.is_file()]
(E/'FIGURE_V2_BEFORE_V3_BYTES.json').write_bytes((json.dumps(protected,indent=2)+'\n').encode())
subprocess.run(['git','-c','core.autocrlf=false','clone','--no-hardlinks',str(P),str(S)],check=True,capture_output=True)
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
git('config','core.autocrlf','false');git('config','user.name','RevTrace artifact');git('config','user.email','artifact@revtrace.invalid')
git('switch','-c','codex/dsn-story-figures-v3')
p=S/'render_story_figures.py';s=p.read_text(encoding='utf8')
old="box(ax,5.27,2.16,1.73,.66,'[AU] Original result '+r'$P_3$'+'\\ncomplete + authorized\\nsync → select / install',BLUE,'#EAF1F8')"
new="box(ax,5.08,2.10,1.93,.78,'Original Correct/Update result '+r'$P_3$'+'\\n[AU] complete result +\\nchecked parent\\nsync → install',BLUE,'#EAF1F8')"
assert old in s;s=s.replace(old,new)
s=s.replace("arrow(ax,(4.95,2.49),(5.27,2.49),BLUE)","arrow(ax,(4.95,2.49),(5.08,2.49),BLUE)")
assert 'Unknown: wait; no commit' in s;s=s.replace('Unknown: wait; no commit','Unknown: may run/buffer; no commit')
assert '(b) The same content arrives sooner' in s;s=s.replace('(b) The same content arrives sooner','(b) More matching content meets deadlines')
s=s.replace("ax.text(0,3.70,'Matched',","ax.text(0,3.70,'Matched trials',")
needle=" for row in sm['protected_v4_files']:assert sha(row['path'])==row['sha256']"
assert s.count(needle)==2
s=s.replace(needle,needle+"\n for row in sm['protected_v2_artwork']:assert sha(row['path'])==row['sha256']")
p.write_bytes(s.encode())
sm=json.loads((S/'SOURCE_MAP.json').read_bytes());sm['protected_v2_artwork']=protected
(S/'SOURCE_MAP.json').write_bytes((json.dumps(sm,indent=2)+'\n').encode())
cfg=json.loads((S/'CONFIG.json').read_bytes());cfg['experiment_id']='DSN_STORY_REVISION_FIGURES_20261031_V3_TEXT_REPLOT'
cfg['scope']='Text-only artwork revision after cold reading; original data and actual73026 interval analysis unchanged'
cfg['input_map_sha256']=hashlib.sha256((S/'SOURCE_MAP.json').read_bytes()).hexdigest()
(S/'CONFIG.json').write_bytes((json.dumps(cfg,indent=2)+'\n').encode())
with (S/'README.md').open('a',encoding='utf8',newline='\n') as f:
 f.write('\n## V3 text-only cold-read fixes\n\nUNKNOWN explicitly permits running/buffering without commit. The AU box names\nthe complete original Correct/Update result and checked parent before sync/install.\nThe native panel headline states matching content meeting deadlines and its first\nbank is named Matched trials. Data, partitions and original interval analysis are\nunchanged; all v2 output bytes/gates are protected before and after.\n')
for p in S.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
git('add','.');git('commit','-m','Clarify input-pending, original selection and matching-content figure labels')
commit=git('rev-parse','HEAD');assert not git('status','--porcelain','--untracked-files=all')
files=[]
for rel in git('ls-files').splitlines():
 data=(S/rel).read_bytes();files.append(dict(path=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=E/'FIGURE_SOURCE_v3.json';assert not manifest.exists()
manifest.write_bytes((json.dumps(dict(code_commit=commit,source_commit=commit,
 scope='Text-only figure replot; actual interval analysis73026 and all measured data unchanged',files=files),indent=2)+'\n').encode())
bundle=E/'FIGURE_SOURCE_v3.bundle';git('bundle','create',str(bundle),'HEAD')
subprocess.run(['git','-C',str(R),'bundle','verify',str(bundle)],check=True,capture_output=True)
subprocess.run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/codex/execution/dsn-story-figures-v3'],check=True,capture_output=True)
snap=E/'figure_snapshot_v3';snap.mkdir()
for row in files:
 dest=snap/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((S/row['path']).read_bytes())
sys.path.insert(0,str(S));from render_story_figures import environment
env=E/'FIGURE_ENVIRONMENT_v3.json';assert not env.exists();env.write_bytes((json.dumps(environment(),indent=2)+'\n').encode())
record=dict(status='FROZEN_TEXT_REPLOT_READY_FOR_ROOT_NOARG_NOT_EXECUTED',actual_plot_source_commit=commit,
 actual_interval_analysis_commit='73026a11f6db202d723e6028ad85e6833888ec78',source_root=str(S),source_manifest=str(manifest),
 manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
 files=len(files),frozen_config_sha256=hashlib.sha256((S/'CONFIG.json').read_bytes()).hexdigest(),
 environment=str(env),environment_sha256=hashlib.sha256(env.read_bytes()).hexdigest(),intended_outputs=str(E/'FIGURES_v3'),
 intended_summary=str(E/'FIGURES_v3/SUMMARY.json'),intended_gate=str(E/'FIGURES_v3/GATE.json'),
 protected_previous_artwork_files=len(protected),new_model_calls=0,actual_reader_repeated=False)
(E/'FIGURE_FREEZE_v3.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(record))

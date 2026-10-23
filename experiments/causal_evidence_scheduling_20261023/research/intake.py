"""Verify the named delivered source, then make a separate CES source branch."""
from pathlib import Path
import hashlib,json,shutil,subprocess,time
W=Path(__file__).resolve().parent
OLD=W.parent/'causal_row_completion_20261023'
G=W.parent/'online_admission_20261022/git_delivery_stage_v1'
BASE='23ba88cfc2ff73cfa209847d4a8866ef5272c8ad'
def git(root,*a):return subprocess.check_output(['git','-C',str(root),*a]).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert git(G,'rev-parse','HEAD')==BASE
published=json.loads(subprocess.check_output(['git','-C',str(G),'show',BASE+':experiments/causal_row_completion_20261023/MANIFEST.json']))
assert published['formal_cells']==150
S=OLD/'source_row_sdk_v2';m=json.loads((S/'SOURCE_MANIFEST.json').read_text())
assert m['code_commit']=='2bc71af5457de5d065ff9e771d2fad428c5c6ed9'
assert git(S,'rev-parse','HEAD')==m['code_commit']
for r in m['files']:assert sha(S/r['path'])==r['sha256']
D=W/'runtime';assert not D.exists();shutil.copytree(S,D)
git(D,'switch','-c','codex/ces-20261023')
(D/'SOURCE_MANIFEST.json').unlink() # obsolete identity, regenerated before execution
papers=[]
for folder in ['Paper','Paper_TC','Paper_DSN']:
 for p in sorted((W.parents[1]/folder).rglob('*')):
  if p.is_file():papers.append({'path':str(p),'sha256':sha(p)})
(W/'PAPER_BEFORE.json').write_text(json.dumps(papers,indent=2)+'\n')
record={'experiment_id':'REVTRACE-CES-20261023','time_unix':time.time(),
 'GitHub_baseline':BASE,'sdk_commit':m['code_commit'],'verified_source_files':len(m['files']),
 'published_manifest_sha256':hashlib.sha256(subprocess.check_output(['git','-C',str(G),'show',BASE+':experiments/causal_row_completion_20261023/MANIFEST.json'])).hexdigest(),
 'root_AGENTS_sha256':sha(W.parents[1]/'AGENTS.md'),'paper_files_frozen':len(papers),
 'prior_GONOGO':json.loads((OLD/'reports_v1/GO_NO_GO.json').read_text()),
 'no_new_GPU_calls':True}
(W/'INTAKE.json').write_text(json.dumps(record,indent=2)+'\n')
(W/'ACTIVE_STATE.json').write_text(json.dumps({'phase':'IMPLEMENTATION_AND_CALIBRATION','GPU_started':False,'baseline':BASE},indent=2)+'\n')
print(json.dumps(record))

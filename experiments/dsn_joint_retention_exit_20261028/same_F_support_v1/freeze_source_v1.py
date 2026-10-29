"""Local-only complete freeze; never stages or executes a remote workload."""
from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;root=here/'source_v1';root.mkdir(exist_ok=False)
for name in ['quality_recount.py','test_quality_recount.py','PROTOCOL.zh.md']:shutil.copyfile(here/name,root/name)
(root/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
subprocess.run(['git','-C',str(root),'init'],check=True,capture_output=True)
def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
git('config','core.autocrlf','false');git('checkout','-b','codex/dsn-joint-same-f-quality-v1');git('add','.');git('commit','-m','Freeze original-first-credit same-F Canonical support and fixed 96-row quality audit')
manifest=dict(code_commit=git('rev-parse','HEAD'),scope='CPU-only orchestration and fixed-row supplement; primary usefulness analysis remains clean fde6272b494db43a66eebea7444d7c9d1037e687',files=[dict(path=n,bytes=(root/n).stat().st_size,sha256=hashlib.sha256((root/n).read_bytes()).hexdigest()) for n in git('ls-files').splitlines()])
with (here/'SOURCE_v1.json').open('x',encoding='utf8') as stream:json.dump(manifest,stream,indent=2);stream.write('\n')
git('bundle','create',str(here/'SOURCE_v1.bundle'),'HEAD');assert not git('status','--porcelain','--untracked-files=all')
receipt=dict(status='FROZEN_LOCAL_PREPARATION_NOT_REMOTE_EXECUTION',experiment_id='REVTRACE-DSN-RXK-SAMEF-SUPPORT-20261029-v1',orchestration_source_commit=manifest['code_commit'],primary_analysis_commit='fde6272b494db43a66eebea7444d7c9d1037e687',files=[dict(path=name,bytes=(here/name).stat().st_size,sha256=hashlib.sha256((here/name).read_bytes()).hexdigest()) for name in ['PLAN_v1.json','NEURAL_PLAN_v1.json','TARGET_BATCHES_v1.json','PRIOR_INPUT_RECORD_v1.json','SOURCE_v1.json','SOURCE_v1.bundle','LOCAL_SYNTHETIC_CONTROLS.json','LOCAL_SYNTHETIC_CONTROLS.log']],expected_remote_environment='8TB envs/revbatch-cu128 Python, to be recorded and validated at actual CPU launch; local controls are synthetic only',remote_actions=0,new_GPU_calls=0)
(here/'FREEZE_RECEIPT_v1.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(json.dumps(receipt))

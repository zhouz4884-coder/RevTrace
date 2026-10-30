"""Root-only complete runtime freeze. Default is read-only; no model execution."""
import argparse,datetime,hashlib,json,pathlib,shutil,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'source_dev'
BDFA='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
def put(p,x):assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--version',default='v1');p.add_argument('--commit-message');a=p.parse_args()
 import re
 assert re.fullmatch(r'v[1-9]\d*',a.version)
 tracked=git('ls-files').splitlines();untracked=git('ls-files','--others','--exclude-standard').splitlines();extra=[n for n in untracked if pathlib.Path(n).suffix=='.py'];unexpected=sorted(set(untracked)-set(extra))
 assert not unexpected,('untracked non-Python runtime input must be explicitly resolved',unexpected)
 assert all((S/n).is_file() for n in tracked),'no silent deletion of prior source/test files'
 assert git('branch','--show-current').startswith('codex/')
 if not a.freeze:print(json.dumps(dict(status='DRY_RUN_NO_MUTATION',tracked=len(tracked),new_python=extra,dirty=bool(git('status','--porcelain','--untracked-files=all')),version=a.version)));return
 packages=F/'packages';packages.mkdir(exist_ok=True);mp=packages/('SOURCE_'+a.version+'.json');bundle=packages/('SOURCE_'+a.version+'.bundle');snapshot=F/('source_snapshot_'+a.version);frozen=F/('source_'+a.version)
 assert not any(x.exists() for x in (mp,bundle,snapshot,frozen)),'new version required; existing freeze never overwritten'
 if git('status','--porcelain','--untracked-files=all'):
  assert a.commit_message,'root must explicitly supply --commit-message or commit the source first'
  git('add','-u','--','.')
  if extra:git('add','--',*extra)
  git('commit','-m',a.commit_message)
 assert not git('status','--porcelain','--untracked-files=all')
 commit=git('rev-parse','HEAD');subprocess.run(['git','-C',str(S),'merge-base','--is-ancestor',BDFA,commit],check=True)
 files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()]
 required={'resilience_trial.py','resilience_owner.py','resilience_storage.py','resilience_metrics.py','resilience_policy.py','resilience_inbound.py','resilience_transport.py','resilience_consumer.py','long_reference.py','state_telemetry.py'}
 assert required<={r['path'] for r in files}
 manifest=dict(source_commit=commit,code_commit=commit,predecessor_source_commit=BDFA,files=files,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Complete same-source native resilience/normal service and long original-task oracle; not an archive HEAD or neural result.')
 put(mp,manifest);snapshot.mkdir()
 for row in files:
  t=snapshot/row['path'];t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes((S/row['path']).read_bytes())
 git('bundle','create',str(bundle.resolve()),'HEAD')
 subprocess.run(['git','-C',str(R),'fetch',str(bundle.resolve()),'HEAD:refs/research/dsn-native-resilience-'+a.version],check=True)
 subprocess.run(['git','clone','-q','--no-checkout',str(bundle.resolve()),str(frozen)],check=True)
 subprocess.run(['git','-C',str(frozen),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(frozen),'checkout','-q',commit],check=True)
 put(F/('CURRENT_RUNTIME_CANDIDATE_'+a.version+'.json'),dict(source_worktree=str(frozen.resolve()),source_manifest=str(mp.resolve()),source_manifest_sha256=sha(mp),source_commit=commit,GPU_queue='FROZEN_RUNTIME_NOT_YET_GPU_LAUNCHED',scope='Candidate only; root explicitly selects CURRENT and runs no-argument preflight.'))
 put(F/('RUNTIME_FREEZE_'+a.version+'.json'),dict(source_commit=commit,source_manifest_sha256=sha(mp),bundle_sha256=sha(bundle),files=len(files),snapshot=str(snapshot),source=str(frozen),GPU_launched=False,global_CURRENT_changed=False))
 print(json.dumps(dict(status='COMPLETE_SOURCE_FROZEN_NOT_LAUNCHED',source_commit=commit,manifest_sha256=sha(mp),files=len(files),source=str(frozen)),indent=2))
if __name__=='__main__':main()


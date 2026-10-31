"""Byte-preserved process snapshot in the existing isolated delivery worktree."""
import argparse,hashlib,json,re,subprocess,zipfile
from pathlib import Path
from release_delivery_checks import validate_final_record
R=Path(__file__).resolve().parents[2];T=Path(__file__).resolve().parent
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace').resolve()
p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--message',required=True);p.add_argument('--release',type=Path);p.add_argument('--archive',type=Path);p.add_argument('--final-record',type=Path,default=T/'FINAL_RELEASE_RECORD_v1.json',help='Matching audited release/archive record; legacy default preserved');a=p.parse_args()
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],text=True,encoding='utf8').strip()
assert not git('status','--porcelain','--untracked-files=all')
files={R/'experiments/LATEST_RESEARCH.json'}
assert bool(a.release)==bool(a.archive),'Final release and its audited archive must be supplied together'
if a.release:
 release=a.release.resolve();archive=a.archive.resolve()
 assert release.is_relative_to(R/'Paper_DSN/revisions') and release.is_dir()
 assert archive.is_relative_to(R/'Paper_DSN') and archive.is_file() and archive.suffix=='.zip'
 provenance=release/'PACKAGING_PROVENANCE.json'
 data=json.loads(provenance.read_text(encoding='utf8'))
 for record in data['files']:
  f=(release/record['target']).resolve();assert f.is_relative_to(release) and f.is_file()
  assert hashlib.sha256(f.read_bytes()).hexdigest()==record['target_sha256'],f
  files.add(f)
 expected={record['target'] for record in data['files']}|{'PACKAGING_PROVENANCE.json','main.pdf'}
 with zipfile.ZipFile(archive) as package:
  assert len(package.namelist())==len(expected) and set(package.namelist())==expected,'Archive must match the exact clean-source whitelist'
  for name in expected:assert package.read(name)==(release/name).read_bytes(),name
 validate_final_record(a.final_record,release,archive,R)
 attr=release/'.gitattributes'
 if not attr.exists():attr.write_text('* -text\n',encoding='utf8')
 files.update([provenance,release/'main.pdf',attr,R/'Paper_DSN/CURRENT.md',archive])
 for f in files:assert f.is_file(),f
new_families={'dsn_streamcorrect_stage_profile_20261029','dsn_native_content_20261029','dsn_full_interval_case_20261029','dsn_streamcorrect_stage_handoff_20261029','dsn_streamcorrect_encoder_profile_20261029','dsn_streamcorrect_independent_20261029','dsn_native_resilience_20261030','dsn_native_sustained_20261030','dsn_native_refinement_20261030','dsn_strengthening_20261031'}
for name in ['dsn_service_stability_20261028','dsn_joint_retention_exit_20261028','dsn_manuscript_update_20261028','dsn_midpoint_continuity_20261029',*sorted(new_families)]:
 D=R/'experiments'/name
 if not D.exists():continue
 attr=D/'.gitattributes'
 if not attr.exists():attr.write_text('* -text\n',encoding='utf8')
 for f in D.rglob('*'):
  if not f.is_file() or any(x in f.parts for x in ['.git','__pycache__','.pytest_cache']):continue
  if name in new_families and any(x=='source_dev' or x.endswith('_source_dev') or x.startswith('source_v') or re.search(r'_source_v\d+$',x) for x in f.relative_to(D).parts):continue
  if f.suffix in ['.pyc','.bin'] or f.name.startswith(('PUBLICATION_','PROCESS_')):continue
  if f.name in ['prepare_remote.py','fetch_old_dev.py','launch_gpu.py','ROOT_CONTINUATION_STATE.md']:continue
  assert f.stat().st_size<20_000_000,f
  files.add(f)
S=R/'experiments/dsn_streamcorrect_adaptation_20261028'
attr=S/'.gitattributes'
if not attr.exists():attr.write_text('* -text\n',encoding='utf8')
for f in S.rglob('*'):
 if not f.is_file() or any(x in f.parts for x in ['.git','__pycache__','.pytest_cache']):continue
 if any(x.startswith('source_v') or re.search(r'_source_v\d+$',x) for x in f.relative_to(S).parts):continue
 if f.suffix in ['.pyc','.bin'] or f.name.startswith(('PROCESS_','PUBLICATION_')):continue
 assert f.stat().st_size<20_000_000,f
 files.add(f)
records=[]
for f in sorted(files):
 data=f.read_bytes();target=(W/f.relative_to(R)).resolve();assert target.is_relative_to(W)
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 records.append(dict(path=f.relative_to(R).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
manifest=T/('PROCESS_'+a.snapshot+'.json');assert not manifest.exists()
manifest.write_text(json.dumps(dict(schema='bounded-process-snapshot-v1',stage=a.snapshot,files=records,scope='Plans, frozen source, actual bounded results and explicit per-study completion/ongoing status. Frozen follow-up plans are not completed experiments.',raw_logs='designated8TB only',manifest_self_excluded=True),indent=2)+'\n',encoding='utf8')
dest=W/manifest.relative_to(R);dest.write_bytes(manifest.read_bytes());files.add(manifest)
ignored_author_script=R/'experiments/dsn_streamcorrect_stage_handoff_20261029/author_reference/runs/run_single_eval_aishell.sh'
spec=T/('PROCESS_'+a.snapshot+'.bin');spec.write_bytes(b''.join(f.relative_to(R).as_posix().encode()+b'\0' for f in sorted(files) if f!=ignored_author_script))
subprocess.run(['git','-C',str(W),'-c','core.autocrlf=false','--literal-pathspecs','add','--pathspec-from-file='+str(spec),'--pathspec-file-nul'],check=True,capture_output=True)
if ignored_author_script in files:
 subprocess.run(['git','-C',str(W),'-c','core.autocrlf=false','--literal-pathspecs','add','-f',ignored_author_script.relative_to(R).as_posix()],check=True,capture_output=True)
index={}
for raw in subprocess.check_output(['git','-C',str(W),'ls-files','--stage','-z']).split(b'\0'):
 if not raw:continue
 header,name=raw.split(b'\t',1);index[name.decode()]=header.decode().split()[1]
for f in files:
 data=f.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 assert index[f.relative_to(R).as_posix()]==blob,f
git('commit','-m',a.message)
assert not git('status','--porcelain','--untracked-files=all')
commit=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
subprocess.run(['git','-C',str(W),'-c','http.version=HTTP/1.1','push','origin','HEAD:main'],check=True)
remote=git('ls-remote','origin','refs/heads/main').split()[0];assert remote==commit
receipt=dict(stage=a.snapshot,commit=commit,tree=tree,files=len(files),bytes=sum(f.stat().st_size for f in files),remote_main_verified=True)
(T/('PUBLICATION_'+a.snapshot+'.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

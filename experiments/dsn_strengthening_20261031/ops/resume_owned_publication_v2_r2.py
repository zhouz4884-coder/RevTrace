"""Resume only this exact owned pre-commit snapshot after LF canonicalization."""
import hashlib,json,pathlib,subprocess
R=pathlib.Path(__file__).resolve().parents[3];E=R/'experiments/dsn_strengthening_20261031';T=R/'experiments/dsn_manuscript_update_20261028'
W=pathlib.Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace').resolve()
BASE='f73cecac0178e30387a6e9a9ed86b08f8da8e985';OLD='dsn2027_strengthening_20261031_release_v2';NEW=OLD+'_r2'
def git(*args):return subprocess.check_output(['git','-C',str(W),*args])
def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,x):
    assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
oldmanifest=T/('PROCESS_'+OLD+'.json');oldbytes=oldmanifest.read_bytes();prior=json.loads(oldbytes)
assert git('rev-parse','HEAD').decode().strip()==BASE
assert not git('diff','--name-only','-z').strip(b'\0'),'unrelated unstaged edits exist'
oldrel=oldmanifest.relative_to(R).as_posix();allowed={row['path'] for row in prior['files']}|{oldrel}
changed={x.decode() for x in git('diff','--cached','--name-only','-z').split(b'\0') if x}
assert changed and changed<=allowed,'staged changes outside this exact owned snapshot'
assert not git('ls-tree','--name-only','HEAD','--',oldrel).strip(),'old process candidate existed in parent'
# Preserve the rejected candidate, never relabel it as byte-verified.
preserved=E/'DELIVERY_FAILED_STAGE_v2_ORIGINAL_MANIFEST.json';put(preserved,prior)
current=R/'Paper_DSN/CURRENT.md';raw=current.read_bytes();indexed=git('show',':Paper_DSN/CURRENT.md')
assert raw!=indexed and raw.replace(b'\r\n',b'\n')==indexed
failure=E/'DELIVERY_BYTE_GATE_FAILURE_v2.json';put(failure,dict(status='PRE_COMMIT_BYTE_GATE_REJECTED_ONLY_CURRENT_EOL_NORMALIZATION',archive_HEAD_unchanged=BASE,raw_CURRENT_sha256=sha(raw),index_CURRENT_sha256=sha(indexed),old_PROCESS_sha256=sha(oldbytes),preserved_manifest=preserved.relative_to(R).as_posix(),scientific_or_PDF_changes=False,old_candidate_was_not_pushed=True))
current.write_bytes(indexed)
# Only this newly generated, absent-at-HEAD candidate is removed from delivery.
oldtarget=(W/oldrel).resolve();assert oldtarget.is_relative_to(W) and oldtarget.read_bytes()==oldbytes
subprocess.run(['git','-C',str(W),'rm','--cached','--',oldrel],check=True,capture_output=True)
oldtarget.unlink()
files={R/row['path'] for row in prior['files']}|{preserved,failure,pathlib.Path(__file__).resolve()}
records=[]
for f in sorted(files):
    data=f.read_bytes();assert len(data)<20_000_000
    target=(W/f.relative_to(R)).resolve();assert target.is_relative_to(W)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    records.append(dict(path=f.relative_to(R).as_posix(),bytes=len(data),sha256=sha(data)))
manifest=T/('PROCESS_'+NEW+'.json');put(manifest,dict(schema='bounded-process-snapshot-v1',stage=NEW,parent_stage=OLD,previous_candidate_retained_as_failure=True,files=records,raw_logs='designated8TB only',manifest_self_excluded=True))
(W/manifest.relative_to(R)).write_bytes(manifest.read_bytes());files.add(manifest)
ignored=R/'experiments/dsn_streamcorrect_stage_handoff_20261029/author_reference/runs/run_single_eval_aishell.sh'
spec=T/('PROCESS_'+NEW+'.bin');assert not spec.exists();spec.write_bytes(b''.join(f.relative_to(R).as_posix().encode()+b'\0' for f in sorted(files) if f!=ignored))
subprocess.run(['git','-C',str(W),'-c','core.autocrlf=false','--literal-pathspecs','add','--pathspec-from-file='+str(spec),'--pathspec-file-nul'],check=True,capture_output=True)
if ignored in files:subprocess.run(['git','-C',str(W),'-c','core.autocrlf=false','--literal-pathspecs','add','-f',ignored.relative_to(R).as_posix()],check=True,capture_output=True)
index={}
for row in git('ls-files','--stage','-z').split(b'\0'):
    if row:
        header,name=row.split(b'\t',1);index[name.decode()]=header.decode().split()[1]
for f in files:
    data=f.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert index[f.relative_to(R).as_posix()]==blob,f
assert {x.decode() for x in git('diff','--cached','--name-only','-z').split(b'\0') if x}<={f.relative_to(R).as_posix() for f in files}
git('commit','-m','Strengthen native serving evidence and release DSN2027 manuscript v2')
assert not git('status','--porcelain','--untracked-files=all').strip()
commit=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
subprocess.run(['git','-C',str(W),'-c','http.version=HTTP/1.1','push','origin','HEAD:main'],check=True)
remote=git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').decode().split()[0];assert remote==commit
record=dict(stage=NEW,commit=commit,tree=tree,files=len(files),bytes=sum(f.stat().st_size for f in files),remote_main_verified=True,original_source_and_pdf_unchanged=True)
put(T/('PUBLICATION_'+NEW+'.json'),record);print(json.dumps(record,indent=2))

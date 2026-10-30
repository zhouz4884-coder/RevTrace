"""Freeze literal selected-record/strict-clock counters without changing NN."""
import hashlib,json,pathlib,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'native_work_source_v1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
git=lambda *a:subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD');rows=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in sorted(git('ls-files').splitlines())]
M=F/'packages/NATIVE_WORK_SOURCE_v1.json';assert not M.exists();M.write_bytes((json.dumps(dict(source_commit=commit,code_commit=commit,files=rows,scope='Pure literal selected-Canonical native marker and strict actual post-fault consume counters, not forward/paid-work meter.'),indent=2)+'\n').encode());bundle=F/'packages/NATIVE_WORK_SOURCE_v1.bundle';subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True);subprocess.run(['git','-C',str(R),'fetch',str(bundle.resolve()),'HEAD:refs/research/dsn-native-work-count-v1'],check=True,capture_output=True)
snapshot=F/'native_work_snapshot_v1';snapshot.mkdir()
for row in rows:(snapshot/row['path']).write_bytes((S/row['path']).read_bytes())
target=F/'CURRENT_NATIVE_WORK_CANDIDATE_v1.json';target.write_bytes((json.dumps(dict(source_worktree=str(S.resolve()),source_manifest=str(M.resolve()),source_manifest_sha256=sha(M),source_commit=commit,GPU_queue='AFTER_FULL_NN_ONLY_PURE_CPU_NATIVE_MARKER_STRICT_CLOCK_RECOUNT'),indent=2)+'\n').encode());print(json.dumps(dict(source_commit=commit,manifest_sha256=sha(M),files=len(rows),CPU_not_yet_run=True,NN_calls=0)))

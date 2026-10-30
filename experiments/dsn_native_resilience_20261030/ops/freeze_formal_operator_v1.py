"""Freeze the separate formal serial operator; no neural or remote action."""
import hashlib,json,pathlib,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'formal_operator_source_v1'
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):assert not p.exists();p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD')
rows=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in sorted(git('ls-files').splitlines())]
manifest=F/'packages/FORMAL_OPERATOR_SOURCE_v1.json';put(manifest,dict(source_commit=commit,code_commit=commit,role='formal_serial28or8_operator_not_neural',neural_source_commit='9492d3f9cb35e2b2849ec020817750a221248f0e',files=rows))
bundle=F/'packages/FORMAL_OPERATOR_SOURCE_v1.bundle';subprocess.run(['git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD'],check=True);subprocess.run(['git','-C',str(R),'fetch',str(bundle.resolve()),'HEAD:refs/research/dsn-native-formal-operator-v1'],check=True,capture_output=True)
snap=F/'formal_operator_snapshot_v1';snap.mkdir()
for row in rows:(snap/row['path']).write_bytes((S/row['path']).read_bytes())
put(F/'CURRENT_FORMAL_OPERATOR_CANDIDATE_v1.json',dict(source_worktree=str(S.resolve()),source_manifest=str(manifest.resolve()),source_manifest_sha256=sha(manifest),source_commit=commit,GPU_queue='LOCAL_CPU_FORMAL_OPERATOR21_NO_NEURAL',scope='Next run only; no historical NN attribution.'))
print(json.dumps(dict(source_commit=commit,manifest_sha256=sha(manifest),files=len(rows),CPU_not_yet_executed=True)))

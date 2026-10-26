"""Materialize ONLY the new owned study prefix in an independent Git index."""
from pathlib import Path
import json,shutil,hashlib,subprocess,tarfile,re
W=Path(__file__).resolve().parent;G=W/'delivery_git_v1';D=G/'experiments/legal_progress_20261026';D.mkdir(parents=True,exist_ok=False)
BASE='62b1003c2db6766118244c78fa95e2c3fac42c16'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,rel):
    q=D/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def git(*args):return subprocess.check_output(['git','-C',str(G),*args])
assert git('rev-parse','HEAD').decode().strip()==BASE
assert not git('ls-tree','HEAD','experiments/legal_progress_20261026')
assert json.loads((W/'FINAL_METRICS.json').read_text())['status'].startswith('PASS_')
assert json.loads((W/'REMOTE_COMPLETION.json').read_text())['pending_GPU_stages']==[]
for p in W.iterdir():
    if not p.is_file():continue
    if p.suffix in ['.py','.md','.json','.csv','.xml','.sh'] and p.name not in ['fetch_reference.py']:
        copy(p,Path(p.name))
for name in ['RAW_EVIDENCE.tar.gz','M_FORMAT_RAW.tar.gz']:copy(W/name,Path(name))
for p in (W/'runtime').rglob('*'):
    if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts:copy(p,Path('runtime')/p.relative_to(W/'runtime'))
for p in (W/'cpu_full_v2').rglob('*'):
    if p.is_file():copy(p,Path('cpu_full_counterexample')/p.relative_to(W/'cpu_full_v2'))
legacy=W.parent/'evidence_retirement_20261026'
for name in ['MEMORY_DEVELOPMENT_v3_SUMMARY.json','MEMORY_DEVELOPMENT_v3_CALLS.json','MEMORY_DEVELOPMENT_v4_CALLS.json',
             'MEMORY_TASKS_SHA256.json','MEMORY_TASKS_v4_SHA256.json','MEMORY_TASKS_v4.json']:
    copy(legacy/name,Path('legacy_evidence')/name)
releases=[]
for p in sorted(W.glob('*_SOURCE.json')):
    name=p.name[:-len('_SOURCE.json')];src=W/name
    if not src.is_dir() or not (src/'.git').exists():continue
    source=json.loads(p.read_text());archive=W/(name+'.tar.gz')
    if archive.exists():copy(archive,Path('frozen_sources')/archive.name)
    bundle=D/'frozen_sources'/(name+'.bundle');bundle.parent.mkdir(exist_ok=True)
    subprocess.run(['git','-C',str(src),'bundle','create',str(bundle),'--all'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD']).decode().strip()==source['code_commit']
    releases.append(dict(name=name,code_commit=source['code_commit'],files=len(source['files']),
        tar_sha256=sha(archive) if archive.exists() else None,bundle_sha256=sha(bundle),
        status=('PREPARED_NOT_EXECUTED' if name=='x_service_execution_v1' else 'CPU_FINAL_SOURCE' if name.startswith('final_source') else 'see stage protocol and raw completion/failure record')))
# The native-source inspection clone/vendor API dump are intentionally excluded.
source_file=D/'SOURCE_RELEASES.json';source_file.write_text(json.dumps(dict(releases=releases,baseline=BASE,
    exclude=['unlicensed VoiceAgent clone','installed vendor API full dump','credentials/helper','model/audio/env/cache','manuscript/private mirror']),indent=2)+'\n')
(D/'.gitattributes').write_text('* -text\n')
bad=re.compile(rb'(?:github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{25,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
for p in D.rglob('*'):
    if not p.is_file():continue
    assert not any(x in p.parts for x in ['reference_voiceagent_git','__pycache__','.git'])
    assert p.suffix not in ['.safetensors','.flac','.wav','.mp3','.pdf','.tex','.bib']
    if p.suffix in ['.py','.md','.json','.sh','.csv','.xml']:assert not bad.search(p.read_bytes()),'credential pattern in '+str(p)
files=[dict(path=p.relative_to(D).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(D.rglob('*')) if p.is_file()]
assert sum(r['bytes'] for r in files)<70*2**20,'bounded Git payload too large'
manifest=dict(status='BOUNDED_OWNED_PAYLOAD_BYTE_FROZEN',baseline=BASE,files=files,file_count=len(files),total_bytes=sum(r['bytes'] for r in files),
    exclude_self='DELIVERY_MANIFEST.json',research_complete=True,paper_edits=False)
(D/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
git('add','-f','--','experiments/legal_progress_20261026')
diff=git('diff','--cached','--name-status').decode().splitlines();assert diff and all(l.startswith('A\texperiments/legal_progress_20261026/') for l in diff)
git('-c','user.name=Research Artifact','-c','user.email=artifact@example.invalid','-c','commit.gpgsign=false','commit','-m',
    'Archive LP1 historical-view audit, current-input KV service and content-only future-harm controls')
head=git('rev-parse','HEAD').decode().strip()
changed=git('diff-tree','--no-commit-id','--name-status','-r',BASE,head).decode().splitlines()
assert changed and all(l.startswith('A\texperiments/legal_progress_20261026/') for l in changed),'old tree changed'
for r in files:
    blob=git('cat-file','blob',head+':experiments/legal_progress_20261026/'+r['path']);assert hashlib.sha256(blob).hexdigest()==r['sha256']
out=dict(status='COMMITTED_AND_ALL_NEW_GIT_BLOBS_BYTE_VERIFIED',commit=head,baseline=BASE,changed_files=len(changed),
    payload_files=len(files)+1,payload_bytes=manifest['total_bytes'],manifest_sha256=sha(D/'DELIVERY_MANIFEST.json'),
    prior_tree_unchanged=True,ready_for_authorized_push=True)
(W/'LOCAL_DELIVERY_READY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if (D/'reference_voiceagent_git').exists():raise AssertionError('upstream source must not ship')

"""Pure-stdlib source/receipt and per-speaker ABBA contracts."""
from __future__ import annotations
import hashlib,json,os,pathlib,random,subprocess,sys
NN4F='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
SUPPORT='a13fa0a335529dc188f7e738877a3acd027ce4a7'
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
SEED=20261102
class GateError(RuntimeError):pass
def need(ok,text):
    if not ok:raise GateError(text)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def put(path,value,replace=False):
    with pathlib.Path(path).open('w' if replace else 'x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def disk(path):
    p=pathlib.Path(path);need(p.is_absolute() and p.resolve().is_relative_to(B.resolve()),'new output outside designated8TB');return p
def verify_source(root,manifest,expected=None):
    root=pathlib.Path(root).resolve(strict=True);manifest=pathlib.Path(manifest).resolve(strict=True);m=read(manifest)
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
    commit=m.get('source_commit',m.get('code_commit'))
    need(isinstance(commit,str) and len(commit)==40 and (expected is None or commit==expected),'wrong full source commit')
    need(pathlib.Path(git('rev-parse','--show-toplevel')).resolve()==root and git('rev-parse','HEAD')==commit and git('cat-file','-t',commit)=='commit','source identity unresolved')
    need(git('config','--get','core.autocrlf')=='false' and not git('status','--porcelain','--untracked-files=all'),'source dirty or line conversion enabled')
    need(set(git('ls-files','-z').split('\0'))-{''}=={r['path'] for r in m['files']},'complete source manifest mismatch')
    for r in m['files']:
        p=root/r['path'];need(not p.is_symlink() and p.resolve().is_relative_to(root) and p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],'source bytes differ')
    return dict(source_commit=commit,source_root=str(root),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),complete_files=len(m['files']),clean=True)
def selected_sources(receipt,expected):
    need(receipt['status']=='PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE','strict test selection not complete')
    sources=receipt['sources'];need(len(sources)==expected and expected>0,'frozen source count differs')
    need(len({s['speaker_id'] for s in sources})==len({s['source_id'] for s in sources})==expected,'one independent utterance per distinct speaker required')
    for s in sources:
        need(s['original_split']=='StreamCorrect/aishell1_testset','mixed/non-test split forbidden')
        need(s['archive_member']['path']=='StreamCorrect/aishell1_testset/'+s['source_id']+'.wav','source archive membership differs')
        h=s['header'];need(h['sample_rate']==16000 and h['channels']==1 and h['sample_width']==2,'original PCM contract changed')
        need(128000<=s['frames']<=144000 and abs(s['duration']-s['frames']/16000)<1e-10,'original8–9s source duration/header changed')
    need(receipt['model_calls']==0,'selection receipt must precede neural outcomes')
    return sources
def abba_blocks(sources):
    rng=random.Random(SEED);ordered=sorted(sources,key=lambda s:(s['speaker_id'],s['source_id']));rng.shuffle(ordered);orders={}
    for s in ordered:
        order=['conservative','fullcall'];rng.shuffle(order);orders[s['speaker_id']]=order
    blocks=[]
    for repeat in (0,1):
        for s in (ordered if repeat==0 else list(reversed(ordered))):
            order=orders[s['speaker_id']] if repeat==0 else orders[s['speaker_id']][::-1]
            blocks.append(dict(source=s,repeat=repeat,primary_gpu=repeat,strategies=list(order)))
    return blocks,orders
def validate_matrix(cells,sources):
    need(len(cells)==4*len(sources) and len({c['cell_id'] for c in cells})==len(cells),'complete4N matrix required')
    for s in sources:
        own=[c for c in cells if c['source_id']==s['source_id']]
        r0=sorted((c for c in own if c['repeat']==0),key=lambda c:c['position']);r1=sorted((c for c in own if c['repeat']==1),key=lambda c:c['position'])
        need(len(r0)==len(r1)==2 and {c['strategy'] for c in r0}=={'conservative','fullcall'},'speaker repeat policy matrix changed')
        need([c['strategy'] for c in r1]==[c['strategy'] for c in r0][::-1],'per-speaker ABBA did not reverse')
        need(all(c['primary_gpu']==0 for c in r0) and all(c['primary_gpu']==1 for c in r1),'same-repeat GPU role or repeat rotation changed')
    blocks,_=abba_blocks(sources)
    expected=[(b['source']['source_id'],a,b['repeat'],b['primary_gpu']) for b in blocks for a in b['strategies']]
    actual=[(c['source_id'],c['strategy'],c['repeat'],c['primary_gpu']) for c in sorted(cells,key=lambda c:c['position'])]
    need(actual==expected and [c['position'] for c in cells]==list(range(len(cells))),'metadata-only seeded plan order differs')
def reference_binding(path,selection_path,sources):
    ref=read(path);need(ref['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES' and ref['actual_NN_source_commit']==NN4F,'original/restore reference incomplete or wrong source')
    need(ref['selection_receipt']['sha256']==sha(selection_path),'reference selection changed')
    need(set(ref['source_ids'])=={s['source_id'] for s in sources} and set(ref['speaker_ids'])=={s['speaker_id'] for s in sources},'reference did not cover complete fixed selection')
    need(ref['sources']==sources,'reference complete frozen source objects changed')
    for key in ('reference_details','reference_gate','genesis'):
        r=ref[key];need(sha(r['path'])==r['sha256'],'terminal reference bytes differ: '+key)
        if 'bytes' in r:need(pathlib.Path(r['path']).stat().st_size==r['bytes'],'reference length differs')
    need(read(ref['reference_gate']['path'])['status'].startswith('PASS'),'reference gate failed')
    expected=sum((s['frames']+7999)//8000 for s in sources)
    need(ref['reference_details']['expected_steps']==expected,'reference step scope incomplete')
    details=read(ref['reference_details']['path']);need(len(details)==expected and len({(x['source_id'],x['end']) for x in details})==expected,'reference DETAILS missing/duplicate')
    return ref
def child_env():
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
    env.pop('PYTORCH_ALLOC_CONF',None);env.pop('CUDA_VISIBLE_DEVICES',None);return env


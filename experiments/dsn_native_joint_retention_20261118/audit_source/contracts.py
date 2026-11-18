"""Provenance and idle-window gates, no source activation or model import."""
from pathlib import Path
import datetime,hashlib,json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
NN='de0936b2e30179d63aeef6e235cd1af685578c58'
DRIVER='f367c4e1068a9391a0e99d8537c94995a3388e13'
NN_MANIFEST='ce99ca421f5f8b416a1545c57a600ee6a28f43e7d2c10294caa00f0d6636a7c9'
DRIVER_MANIFEST='c9c0fa0c14424fae51d3e822f35286ba69c28b11233fa6c2aef848a231ec724b'
PLAN='2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6'
V5='32fcbdf1cac6f74326b9569a874d3d6d7b80b12757e4dd0e61b91d72ce0e4989'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def put(path,value):
    with Path(path).open('x',encoding='utf8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def disk(path):
    p=Path(path).resolve()
    if not p.is_relative_to(B):raise ValueError('output/input outside designated8TB')
    return p
def source(root,manifest,expected=None):
    root=Path(root).resolve();m=read(manifest)
    g=lambda *args:subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
    commit=m.get('code_commit',m.get('source_commit'))
    if expected is not None and commit!=expected:raise ValueError('wrong actual execution source')
    if Path(g('rev-parse','--show-toplevel')).resolve()!=root or g('rev-parse','HEAD')!=commit or g('cat-file','-t',commit)!='commit':raise ValueError('execution source is not complete/resolvable')
    if g('status','--porcelain','--untracked-files=all') or g('config','--get','core.autocrlf')!='false':raise ValueError('dirty or byte-converted execution source')
    if set(g('ls-files').splitlines())!={r['path'] for r in m['files']}:raise ValueError('complete source manifest mismatch')
    for r in m['files']:
        p=root/r['path']
        if p.is_symlink() or not p.resolve().is_relative_to(root) or p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('source byte mismatch: '+r['path'])
    return dict(code_commit=commit,source_root=str(root),source_manifest=str(Path(manifest).resolve()),source_manifest_sha256=sha(manifest),files=len(m['files']))
def idle(receipt_path):
    r=read(receipt_path)
    if not (r.get('root_authorized_postpilot_idle_window') is True and r.get('timed_service_active') is False and r.get('pilot_driver_confirmed_exited') is True and r.get('pilot_plan_sha256')==PLAN):
        raise ValueError('Root postpilot idle window not declared; never analyze during service')
    expiry=datetime.datetime.fromisoformat(r['not_after_utc'].replace('Z','+00:00'))
    if expiry.tzinfo is None or datetime.datetime.now(datetime.timezone.utc)>=expiry:raise ValueError('Root idle window expired')
    owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=15).strip()
    if owners:raise ValueError('CUDA owner exists; opportunity tests/raw analysis held')
    return r
def check_files(records):
    for r in records:
        p=Path(r['path'])
        if p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('frozen input changed: '+str(p))

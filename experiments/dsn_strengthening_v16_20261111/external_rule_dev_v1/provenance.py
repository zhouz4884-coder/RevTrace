"""Experiment/source/input identity, idle enforcement and neural import block."""
from pathlib import Path
import datetime,hashlib,importlib.abc,json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
EXPERIMENT='REVTRACE-V16-EXTERNAL-LA2-SHADOW-20261111-V2'
PLAN='2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6'
OP_CONFIG='420dd86121c1487dbc6a3ac3b26398f411b4d96d6cdb14e0aa00685cc24f19d5'
NN='de0936b2e30179d63aeef6e235cd1af685578c58'
OP='0d54630951dff6e1a423a1652704ee39eea0b8ce'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def put(p,v):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def disk(p):
    p=Path(p).resolve()
    if not p.is_relative_to(B):raise ValueError('raw/output escaped designated8TB')
    return p
def source(root,manifest,commit=None):
    root=Path(root).resolve();m=read(manifest);wanted=m['code_commit']
    g=lambda *a:subprocess.check_output(['git','-C',str(root),*a],text=True,stderr=subprocess.PIPE).strip()
    if commit is not None and wanted!=commit:raise ValueError('wrong execution source role')
    if Path(g('rev-parse','--show-toplevel')).resolve()!=root or g('rev-parse','HEAD')!=wanted or g('cat-file','-t',wanted)!='commit':raise ValueError('complete execution commit not resolvable')
    if g('status','--porcelain','--untracked-files=all') or g('config','--get','core.autocrlf')!='false':raise ValueError('dirty/byte-translated execution source')
    if set(g('ls-files').splitlines())!={x['path'] for x in m['files']}:raise ValueError('complete manifest path set differs')
    for x in m['files']:
        p=root/x['path']
        if p.is_symlink() or not p.resolve().is_relative_to(root) or p.stat().st_size!=x['bytes'] or sha(p)!=x['sha256']:raise ValueError('source byte mismatch: '+x['path'])
    return dict(code_commit=wanted,source_root=str(root),source_manifest=str(Path(manifest).resolve()),source_manifest_sha256=sha(manifest),files=len(m['files']))
def check_files(records):
    for x in records:
        p=disk(x['path'])
        if p.stat().st_size!=x['bytes'] or sha(p)!=x['sha256']:raise ValueError('frozen input changed: '+str(p))
def idle(path):
    r=read(path)
    if r.get('root_authorized_CPU_idle_window') is not True or r.get('timed_service_active') is not False or r.get('experiment_id')!=EXPERIMENT:
        raise ValueError('Root has not allocated this offline CPU window')
    expiry=datetime.datetime.fromisoformat(r['not_after_utc'].replace('Z','+00:00'))
    if expiry.tzinfo is None or datetime.datetime.now(datetime.timezone.utc)>=expiry:raise ValueError('Root CPU window expired')
    if subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=15).strip():raise ValueError('GPU owner active: CPU controls/replay held')
    return r
class NoNeural(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa'):
            raise ImportError('offline external-rule audit forbids neural imports')

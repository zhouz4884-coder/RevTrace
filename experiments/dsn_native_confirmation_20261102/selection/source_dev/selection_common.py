"""CPU metadata identity helpers; no audio/model imports."""
from __future__ import annotations
import hashlib,io,json,subprocess,zipfile
from pathlib import Path,PurePosixPath

class SelectionError(RuntimeError):pass
def need(x,message):
    if not x:raise SelectionError(message)
def readable(path):return path if hasattr(path,'open') else Path(path)
def read(path):return json.loads(readable(path).read_bytes())
def sha(path):
    h=hashlib.sha256()
    with readable(path).open('rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest()
def put(path,obj):
    with readable(path).open('x',encoding='utf8',newline='\n') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
def verify_source(root,manifest):
    root=Path(root).resolve(strict=True);m=read(manifest);commit=m.get('source_commit',m.get('code_commit'))
    need(Path(git(root,'rev-parse','--show-toplevel')).resolve()==root,'not standalone execution tree')
    need(git(root,'rev-parse','HEAD')==commit and len(commit)==40,'actual source HEAD differs')
    need(not git(root,'status','--porcelain','--untracked-files=all'),'dirty source')
    need(git(root,'config','--get','core.autocrlf')=='false','source byte identity requires autocrlf=false')
    tracked=set(git(root,'ls-files','-z').split('\0'))-{''}
    need(tracked=={r['path'] for r in m['files']},'incomplete source manifest')
    for row in m['files']:
        path=root/row['path'];need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root),'source path escape')
        need(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'source bytes/hash differs')
    return dict(source_commit=commit,source_manifest=str(manifest),manifest_sha256=sha(manifest),files=len(tracked),source_clean=True)


class _MemoryText(io.StringIO):
    def __init__(self,commit,encoding):super().__init__(newline='\n');self.commit=commit;self.encoding_name=encoding
    def close(self):
        if not self.closed:self.commit(self.getvalue().encode(self.encoding_name))
        super().close()


class _MemoryBinary(io.BytesIO):
    def __init__(self,commit):super().__init__();self.commit=commit
    def close(self):
        if not self.closed:self.commit(self.getvalue())
        super().close()


class MemoryPath:
    """Path-like RAM output sink with an unchanged POSIX 8TB destination label.

    No local directory/temp file is created. Root persists zip_bytes() directly
    to the predeclared experiment disk; the actual execution environment stays
    Windows in ENVIRONMENT.json, not relabelled as a Linux execution.
    """
    def __init__(self,label,*,_state=None,_relative=''):
        root=PurePosixPath(str(label))
        need(root.is_absolute() and str(root).startswith('/media/'),'RAM stream destination must be predeclared POSIX experiment-disk path')
        self.label=str(root);self.relative=_relative;self.state=_state if _state is not None else dict(files={},dirs=set())
    def __str__(self):return self.label+('/'+self.relative if self.relative else '')
    def __truediv__(self,name):
        name=str(name);part=PurePosixPath(name)
        need(not part.is_absolute() and '..' not in part.parts and '\\' not in name,'RAM output member path escaped')
        relative=str(PurePosixPath(self.relative)/part) if self.relative else str(part)
        return MemoryPath(self.label,_state=self.state,_relative=relative)
    def exists(self):return self.relative in self.state['files'] or self.relative in self.state['dirs']
    def mkdir(self,parents=False,exist_ok=False):
        need(exist_ok or not self.exists(),'RAM output path already exists');self.state['dirs'].add(self.relative)
    def open(self,mode='r',encoding=None,newline=None):
        files=self.state['files'];key=self.relative
        if mode in {'rb','r'}:
            if key not in files:raise FileNotFoundError(str(self))
            return io.BytesIO(files[key]) if mode=='rb' else io.StringIO(files[key].decode(encoding or 'utf8'))
        need(mode in {'x','w','xb','wb'},'unsupported RAM stream mode')
        if mode.startswith('x') and key in files:raise FileExistsError(str(self))
        def commit(raw):files[key]=raw
        return _MemoryBinary(commit) if 'b' in mode else _MemoryText(commit,encoding or 'utf8')
    def read_bytes(self):
        with self.open('rb') as stream:return stream.read()
    def read_text(self,encoding='utf8'):return self.read_bytes().decode(encoding)
    def zip_bytes(self):
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,body in sorted(self.state['files'].items()):
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100444<<16
                archive.writestr(info,body)
        return raw.getvalue()

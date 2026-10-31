"""Fail-closed CPU source identity, bounded immutable raw inputs and outputs."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE = Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')

def need(ok, message):
    if not ok:raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def read(path):return json.loads(Path(path).read_bytes())

def put(path, value):
    with Path(path).open('x',encoding='utf8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')

def disk(path):
    p=Path(path)
    need(p.is_absolute() and p.resolve().is_relative_to(BASE.resolve()), 'outside designated 8TB: '+str(path))
    need(not p.is_symlink(),'symlink path forbidden: '+str(p))
    return p

def control_hashes(paths):
    return {str(disk(p).resolve()):dict(bytes=Path(p).stat().st_size,sha256=sha(p)) for p in paths}

def verify_controls_unchanged(paths, before):
    after=control_hashes(paths)
    need(after==before,'frozen config/environment/root gate/manifest changed during analysis')
    return after

def source_gate(root, manifest, expected_manifest_sha, expected_commit):
    root=Path(root).resolve();manifest=Path(manifest)
    need(sha(manifest)==expected_manifest_sha,'source manifest changed')
    m=read(manifest);need(m['source_commit']==m['code_commit']==expected_commit,'source manifest identity')
    git=lambda *args:subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
    need(Path(git('rev-parse','--show-toplevel')).resolve()==root,'source is not independent checkout')
    need(git('rev-parse','HEAD')==expected_commit and git('cat-file','-t',expected_commit)=='commit','source full commit not HEAD')
    need(not git('status','--porcelain','--untracked-files=all'),'dirty source')
    rows=m['files'];names={x['path'] for x in rows}
    need(len(rows)==len(names) and set(git('ls-files').splitlines())==names,'complete source manifest differs')
    for item in rows:
        p=root/item['path'];need(p.resolve().is_relative_to(root) and not p.is_symlink(),'source path escape')
        need(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],'source bytes changed: '+item['path'])
    deps=read(root/'DEPENDENCIES.json')
    for item in deps['files']:
        p=root/item['vendored_path'];need(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],'vendored dependency changed')
    return dict(source_root=str(root),source_manifest=str(manifest),code_commit=expected_commit,source_manifest_sha256=expected_manifest_sha,files_verified=len(rows),clean=True)

class Inputs:
    def __init__(self, items, max_bytes):
        self.items={str(disk(r['path']).resolve()):r for r in items};self.accessed=set()
        need(len(items)==len(self.items),'duplicate input path')
        need(sum(r['bytes'] for r in items)<=max_bytes,'input budget exceeded')
    def verify_all(self):
        verified={}
        for key,r in self.items.items():
            p=disk(key);need(p.is_file() and p.stat().st_size==r['bytes'],'input missing/size changed: '+key)
            h=sha(p);need(h==r['sha256'],'immutable input hash changed: '+key)
            verified[key]=dict(bytes=r['bytes'],sha256=h)
        return verified
    def path(self,path):
        p=disk(path).resolve();need(str(p) in self.items,'unfrozen input access: '+str(p));self.accessed.add(str(p));return p
    def json(self,path):return read(self.path(path))
    def lines(self,path):return [json.loads(b) for b in self.path(path).read_bytes().splitlines() if b.strip()]

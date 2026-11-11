"""Freeze complete pilot/reference controller, preserving all runtime identities."""
import hashlib,json,pathlib,subprocess
E=pathlib.Path(__file__).resolve().parents[1];ROOT=E.parents[1];SRC=E/'pilot_driver_source_v1';PACK=E/'packages'
OLD=ROOT/'experiments/dsn_native_confirmation_20261102/confirmation/driver_source_v2'
def git(p,*a):return subprocess.check_output(['git','-C',str(p),*a],stderr=subprocess.STDOUT).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
    current=ROOT/'experiments/repository_identity_20261027/CURRENT.json';before=dict(root_head=git(ROOT,'rev-parse','HEAD'),CURRENT_sha256=sha(current))
    parent=git(OLD,'rev-parse','HEAD');assert parent=='d865af11e9a8d6c451146942d1708a8caed8d1d9'
    assert not git(OLD,'status','--porcelain','--untracked-files=all')
    assert not (SRC/'.git').exists();git(SRC,'init','-b','codex/dsn-v16-pilot-driver-v1');git(SRC,'config','core.autocrlf','false')
    git(SRC,'fetch',str(OLD),'HEAD:refs/parent/confirmation-v2');git(SRC,'update-ref','refs/heads/codex/dsn-v16-pilot-driver-v1',parent);git(SRC,'read-tree',parent)
    git(SRC,'add','--all');git(SRC,'commit','-m','Freeze v16 main and auxiliary pilot with fresh-runtime reference and accounting controls')
    commit=git(SRC,'rev-parse','HEAD');assert git(SRC,'rev-parse','HEAD^')==parent
    assert not git(SRC,'status','--porcelain','--untracked-files=all')
    paths=[p for p in git(SRC,'ls-files','-z').split('\x00') if p]
    manifest=PACK/'PILOT_DRIVER_SOURCE_v1.json'
    put(manifest,dict(source_commit=commit,code_commit=commit,parent_driver_source_commit=parent,actual_NN_source_commit='14ae77ee2f1f0c324be3f40b89fb6011972c35b9',files=[dict(path=p,bytes=(SRC/p).stat().st_size,sha256=sha(SRC/p)) for p in sorted(paths)]))
    bundle=PACK/'PILOT_DRIVER_SOURCE_v1.bundle';assert not bundle.exists();git(SRC,'bundle','create',str(bundle),'--all');git(SRC,'bundle','verify',str(bundle))
    ref='refs/revtrace/execution/dsn-v16-pilot-driver-v1';git(ROOT,'fetch',str(bundle),'refs/heads/codex/dsn-v16-pilot-driver-v1:'+ref)
    assert git(ROOT,'cat-file','-t',commit)=='commit'
    after=dict(root_head=git(ROOT,'rev-parse','HEAD'),CURRENT_sha256=sha(current));assert before==after
    record=dict(status='FROZEN_PILOT_REFERENCE_DRIVER',source_commit=commit,source_root=str(SRC),files=len(paths),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),bundle=str(bundle),bundle_sha256=sha(bundle),root_execution_ref=ref,default_before=before,default_after=after)
    put(PACK/'PILOT_DRIVER_FREEZE_v1.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()

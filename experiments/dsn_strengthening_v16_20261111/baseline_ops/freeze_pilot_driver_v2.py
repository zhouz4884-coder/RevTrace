"""Freeze v3-runtime/full4-reference controller, preserving historical driverv1."""
import hashlib,json,pathlib,subprocess
E=pathlib.Path(__file__).resolve().parents[1];ROOT=E.parents[1];SRC=E/'pilot_driver_source_v2';PACK=E/'packages'
def git(p,*a):return subprocess.check_output(['git','-C',str(p),*a],stderr=subprocess.STDOUT).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
    current=ROOT/'experiments/repository_identity_20261027/CURRENT.json';before=dict(root_head=git(ROOT,'rev-parse','HEAD'),CURRENT_sha256=sha(current))
    old=E/'pilot_driver_source_v1';parent=git(old,'rev-parse','HEAD');assert parent=='2facd9fd954ffbbc0f2165d50789e2292508467b'
    assert not git(old,'status','--porcelain','--untracked-files=all');assert not (SRC/'.git').exists()
    branch='codex/dsn-v16-pilot-driver-v2';git(SRC,'init','-b',branch);git(SRC,'config','core.autocrlf','false')
    git(SRC,'fetch',str(PACK/'PILOT_DRIVER_SOURCE_v1.bundle'),'refs/heads/codex/dsn-v16-pilot-driver-v1:refs/parent/v1')
    git(SRC,'update-ref','refs/heads/'+branch,parent);git(SRC,'read-tree',parent);git(SRC,'add','--all')
    git(SRC,'commit','-m','Bind shared RR runtime and measured full4 references to prespecified pilot2')
    commit=git(SRC,'rev-parse','HEAD');assert git(SRC,'rev-parse','HEAD^')==parent;assert not git(SRC,'status','--porcelain','--untracked-files=all')
    paths=[p for p in git(SRC,'ls-files','-z').split('\x00') if p];manifest=PACK/'PILOT_DRIVER_SOURCE_v2.json'
    put(manifest,dict(source_commit=commit,code_commit=commit,parent_driver_source_commit=parent,actual_NN_source_commit='de0936b2e30179d63aeef6e235cd1af685578c58',files=[dict(path=p,bytes=(SRC/p).stat().st_size,sha256=sha(SRC/p)) for p in sorted(paths)]))
    bundle=PACK/'PILOT_DRIVER_SOURCE_v2.bundle';assert not bundle.exists();git(SRC,'bundle','create',str(bundle),'--all');git(SRC,'bundle','verify',str(bundle))
    ref='refs/revtrace/execution/dsn-v16-pilot-driver-v2';git(ROOT,'fetch',str(bundle),'refs/heads/'+branch+':'+ref);assert git(ROOT,'cat-file','-t',commit)=='commit'
    after=dict(root_head=git(ROOT,'rev-parse','HEAD'),CURRENT_sha256=sha(current));assert before==after
    record=dict(status='FROZEN_V3_RUNTIME_FULL4_PILOT2_DRIVER',source_commit=commit,source_root=str(SRC),files=len(paths),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),bundle=str(bundle),bundle_sha256=sha(bundle),root_execution_ref=ref,default_before=before,default_after=after)
    put(PACK/'PILOT_DRIVER_FREEZE_v2.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()

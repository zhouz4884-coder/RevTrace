"""Freeze UIR/timing runtime as a descendant of immutable v1; never edit CURRENT."""
import hashlib,json,pathlib,subprocess
E=pathlib.Path(__file__).resolve().parents[1];ROOT=E.parents[1]
SRC=E/'baseline_source_v2';PACK=E/'packages'
def git(at,*args):return subprocess.check_output(['git','-C',str(at),*args],stderr=subprocess.STDOUT).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
    pointer=ROOT/'experiments/repository_identity_20261027/CURRENT.json'
    before=dict(root_head=git(ROOT,'rev-parse','HEAD'),current_sha256=sha(pointer))
    parent=json.loads((PACK/'BASELINE_SOURCE_v1.json').read_bytes())['source_commit']
    assert not git(E/'baseline_source_dev','status','--porcelain','--untracked-files=all')
    assert not (SRC/'.git').exists()
    git(SRC,'init','-b','codex/dsn-v16-baseline-runtime-v2');git(SRC,'config','core.autocrlf','false')
    git(SRC,'fetch',str(PACK/'BASELINE_SOURCE_v1.bundle'),'refs/heads/codex/dsn-v16-baseline-runtime-v1:refs/parent/v1')
    git(SRC,'update-ref','refs/heads/codex/dsn-v16-baseline-runtime-v2',parent)
    git(SRC,'read-tree',parent)
    git(SRC,'add','--all');git(SRC,'commit','-m','Add safe unconditional inflight retention and explicit receipt-install ordering')
    commit=git(SRC,'rev-parse','HEAD');assert git(SRC,'rev-parse','HEAD^')==parent
    assert not git(SRC,'status','--porcelain','--untracked-files=all')
    paths=[p for p in git(SRC,'ls-files','-z').split('\x00') if p]
    rows=[dict(path=p,bytes=(SRC/p).stat().st_size,sha256=sha(SRC/p)) for p in sorted(paths)]
    manifest=PACK/'BASELINE_SOURCE_v2.json'
    put(manifest,dict(source_commit=commit,code_commit=commit,predecessor_source_commit=parent,
        derived_from_execution_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',files=rows))
    bundle=PACK/'BASELINE_SOURCE_v2.bundle';assert not bundle.exists()
    git(SRC,'bundle','create',str(bundle),'--all');git(SRC,'bundle','verify',str(bundle))
    target='refs/revtrace/execution/dsn-v16-baseline-v2'
    git(ROOT,'fetch',str(bundle),'refs/heads/codex/dsn-v16-baseline-runtime-v2:'+target)
    assert git(ROOT,'cat-file','-t',commit)=='commit' and git(ROOT,'rev-parse',target)==commit
    after=dict(root_head=git(ROOT,'rev-parse','HEAD'),current_sha256=sha(pointer));assert before==after
    record=dict(status='FROZEN_V2_COMPLETE_SOURCE_IMPORTED',source_root=str(SRC),source_commit=commit,
        predecessor_source_commit=parent,files=len(rows),manifest=str(manifest),manifest_sha256=sha(manifest),
        bundle=str(bundle),bundle_sha256=sha(bundle),root_execution_ref=target,
        preserved_default_before=before,preserved_default_after=after)
    put(PACK/'BASELINE_SOURCE_FREEZE_v2.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()

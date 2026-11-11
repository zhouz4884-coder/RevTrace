"""Freeze the isolated complete runtime without touching CURRENT or old source."""
import hashlib,json,pathlib,subprocess
E=pathlib.Path(__file__).resolve().parents[1]
ROOT=E.parents[1]
SRC=E/'baseline_ops/entry_route_source_v1'
PACK=E/'packages'
def git(at,*args):
    return subprocess.check_output(['git','-C',str(at),*args],stderr=subprocess.STDOUT).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
    PACK.mkdir(exist_ok=True)
    pointer=ROOT/'experiments/repository_identity_20261027/CURRENT.json'
    before=dict(root_head=git(ROOT,'rev-parse','HEAD'),current_sha256=sha(pointer))
    assert not (SRC/'.git').exists(),'source already has independent Git; never silently refreeze'
    git(SRC,'init','-b','codex/dsn-v16-entry-route-v1')
    git(SRC,'config','core.autocrlf','false')
    git(SRC,'add','--all')
    git(SRC,'commit','-m','Freeze exact pilot argv and worker entry route contract')
    commit=git(SRC,'rev-parse','HEAD')
    assert not git(SRC,'status','--porcelain','--untracked-files=all')
    paths=git(SRC,'ls-files','-z').split('\x00')
    # check_output.strip leaves no embedded final NUL ambiguity.
    paths=[p for p in paths if p]
    rows=[dict(path=p,bytes=(SRC/p).stat().st_size,sha256=sha(SRC/p)) for p in sorted(paths)]
    manifest=PACK/'ENTRY_ROUTE_SOURCE_v1.json'
    write(manifest,dict(source_commit=commit,code_commit=commit,
        runtime_under_audit='de0936b2e30179d63aeef6e235cd1af685578c58',
        source_role='analysis helper only, no model execution',files=rows))
    bundle=PACK/'ENTRY_ROUTE_SOURCE_v1.bundle'
    assert not bundle.exists()
    git(SRC,'bundle','create',str(bundle),'--all')
    git(SRC,'bundle','verify',str(bundle))
    target='refs/revtrace/execution/dsn-v16-entry-route-v1'
    git(ROOT,'fetch',str(bundle),'refs/heads/codex/dsn-v16-entry-route-v1:'+target)
    assert git(ROOT,'cat-file','-t',commit)=='commit'
    assert git(ROOT,'rev-parse',target)==commit
    after=dict(root_head=git(ROOT,'rev-parse','HEAD'),current_sha256=sha(pointer))
    assert after==before
    record=dict(status='FROZEN_COMPLETE_SOURCE_AND_BUNDLE_IMPORTED',source_root=str(SRC),
        source_commit=commit,files=len(rows),manifest=str(manifest),manifest_sha256=sha(manifest),
        bundle=str(bundle),bundle_sha256=sha(bundle),root_execution_ref=target,
        preserved_default_before=before,preserved_default_after=after)
    write(PACK/'ENTRY_ROUTE_SOURCE_FREEZE_v1.json',record)
    print(json.dumps(record,indent=2))
if __name__=='__main__':main()

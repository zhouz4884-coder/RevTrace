"""Freeze shared fair dispatcher as descendant; preserve v1/v2 and CURRENT."""
import hashlib,json,pathlib,subprocess
E=pathlib.Path(__file__).resolve().parents[1];ROOT=E.parents[1];SRC=E/'baseline_source_v3';PACK=E/'packages'
def git(p,*a):return subprocess.check_output(['git','-C',str(p),*a],stderr=subprocess.STDOUT).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
    pointer=ROOT/'experiments/repository_identity_20261027/CURRENT.json';before=dict(root_head=git(ROOT,'rev-parse','HEAD'),current_sha256=sha(pointer))
    parent=json.loads((PACK/'BASELINE_SOURCE_v2.json').read_bytes())['source_commit'];assert parent=='14ae77ee2f1f0c324be3f40b89fb6011972c35b9'
    assert not git(E/'baseline_source_v2','status','--porcelain','--untracked-files=all')
    assert not (SRC/'.git').exists();branch='codex/dsn-v16-baseline-runtime-v3'
    git(SRC,'init','-b',branch);git(SRC,'config','core.autocrlf','false')
    git(SRC,'fetch',str(PACK/'BASELINE_SOURCE_v2.bundle'),'refs/heads/codex/dsn-v16-baseline-runtime-v2:refs/parent/v2')
    git(SRC,'update-ref','refs/heads/'+branch,parent);git(SRC,'read-tree',parent);git(SRC,'add','--all')
    git(SRC,'commit','-m','Use common canonical-first round-robin allocation for every native policy')
    commit=git(SRC,'rev-parse','HEAD');assert git(SRC,'rev-parse','HEAD^')==parent;assert not git(SRC,'status','--porcelain','--untracked-files=all')
    paths=[p for p in git(SRC,'ls-files','-z').split('\x00') if p];manifest=PACK/'BASELINE_SOURCE_v3.json'
    put(manifest,dict(source_commit=commit,code_commit=commit,predecessor_source_commit=parent,original_NN4f_ancestor='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',files=[dict(path=p,bytes=(SRC/p).stat().st_size,sha256=sha(SRC/p)) for p in sorted(paths)]))
    bundle=PACK/'BASELINE_SOURCE_v3.bundle';assert not bundle.exists();git(SRC,'bundle','create',str(bundle),'--all');git(SRC,'bundle','verify',str(bundle))
    ref='refs/revtrace/execution/dsn-v16-baseline-v3';git(ROOT,'fetch',str(bundle),'refs/heads/'+branch+':'+ref);assert git(ROOT,'cat-file','-t',commit)=='commit'
    after=dict(root_head=git(ROOT,'rev-parse','HEAD'),current_sha256=sha(pointer));assert before==after
    record=dict(status='FROZEN_V3_SHARED_CANONICAL_FIRST_RR',source_root=str(SRC),source_commit=commit,predecessor_source_commit=parent,files=len(paths),manifest=str(manifest),manifest_sha256=sha(manifest),bundle=str(bundle),bundle_sha256=sha(bundle),root_execution_ref=ref,preserved_before=before,preserved_after=after)
    put(PACK/'BASELINE_SOURCE_FREEZE_v3.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()

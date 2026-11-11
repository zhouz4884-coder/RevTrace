"""Freeze authoring only; CPU validation awaits Root's idle window."""
import hashlib,json,pathlib,subprocess
E=pathlib.Path(__file__).resolve().parents[1];ROOT=E.parents[1];SRC=E/'focused_confirmation_source_v1';PACK=E/'packages'
def git(p,*a):return subprocess.check_output(['git','-C',str(p),*a],stderr=subprocess.STDOUT).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
    current=ROOT/'experiments/repository_identity_20261027/CURRENT.json';before=dict(HEAD=git(ROOT,'rev-parse','HEAD'),CURRENT_sha256=sha(current));assert not (SRC/'.git').exists()
    parent='f367c4e1068a9391a0e99d8537c94995a3388e13';branch='codex/dsn-v16-focused-confirmation-v1';git(SRC,'init','-b',branch);git(SRC,'config','core.autocrlf','false');git(SRC,'fetch',str(PACK/'PILOT_DRIVER_SOURCE_v2.bundle'),'refs/heads/codex/dsn-v16-pilot-driver-v2:refs/parent/pilot-v2');git(SRC,'update-ref','refs/heads/'+branch,parent);git(SRC,'read-tree',parent);git(SRC,'add','--all');git(SRC,'commit','-m','Freeze focused Full Ready confirmation on declared bank slices')
    commit=git(SRC,'rev-parse','HEAD');assert not git(SRC,'status','--porcelain','--untracked-files=all');paths=[p for p in git(SRC,'ls-files','-z').split('\x00') if p]
    manifest=PACK/'FOCUSED_CONFIRMATION_SOURCE_v1.json';put(manifest,dict(source_commit=commit,code_commit=commit,parent_controller=parent,actual_NN_source_commit='de0936b2e30179d63aeef6e235cd1af685578c58',reference_generator_source_commit=parent,files=[dict(path=p,bytes=(SRC/p).stat().st_size,sha256=sha(SRC/p)) for p in sorted(paths)]))
    bundle=PACK/'FOCUSED_CONFIRMATION_SOURCE_v1.bundle';assert not bundle.exists();git(SRC,'bundle','create',str(bundle),'--all');git(SRC,'bundle','verify',str(bundle));ref='refs/revtrace/execution/dsn-v16-focused-confirmation-v1';git(ROOT,'fetch',str(bundle),'refs/heads/'+branch+':'+ref)
    after=dict(HEAD=git(ROOT,'rev-parse','HEAD'),CURRENT_sha256=sha(current));assert before==after
    record=dict(status='FROZEN_AUTHORING_CPU_NOT_RUN_GPU_NOT_RUN',source_commit=commit,source_root=str(SRC),files=len(paths),manifest=str(manifest),manifest_sha256=sha(manifest),bundle=str(bundle),bundle_sha256=sha(bundle),execution_ref=ref,preserved_before=before,preserved_after=after)
    put(PACK/'FOCUSED_CONFIRMATION_FREEZE_v1.json',record);print(json.dumps(record,indent=2))
if __name__=='__main__':main()

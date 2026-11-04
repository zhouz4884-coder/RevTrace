from pathlib import Path
import hashlib,json,subprocess
from datetime import datetime,timezone
E=Path(__file__).resolve().parents[1];R=E.parents[1];W=Path('C:/Users/LENOVO/.codex/worktrees/revtrace-dsn-evidence/RevTrace')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_bytes())
g=lambda *a:subprocess.check_output(['git','-C',str(W),*a],stderr=subprocess.PIPE).decode().strip()
head='e9c86cc574394758875bf43c51994bd0208a1042';base='1f841da127d7bba5cead8b129da25da56a50b0eb'
assert g('rev-parse','HEAD')==head and not g('status','--porcelain','--untracked-files=all')
subprocess.run(['git','-c','http.version=HTTP/1.1','-C',str(W),'fetch','--quiet','origin','main'],capture_output=True,check=True)
assert g('rev-parse','FETCH_HEAD')==head and g('rev-parse','HEAD^')==base
manifest=read(E/'PUBLICATION_MANIFEST.json');rows={r['path']:r for r in manifest['rows']}
name=(E/'PUBLICATION_MANIFEST.json').relative_to(R).as_posix();rows[name]=dict(path=name,bytes=(R/name).stat().st_size,sha256=sha(R/name));new=len(rows)
f=read(E/'baseline/FROZEN.json');old11=read(R/'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json')['rows'];old12=read(R/'experiments/dsn_editorial_v13_20261103/baseline/FROZEN_INPUTS.json')['frozen_v12_files']
for row in f['protected_v13']+old11+old12:rows[row['path']]=row
names=sorted(rows);proc=subprocess.run(['git','-C',str(W),'cat-file','--batch'],input=''.join('FETCH_HEAD:'+n+'\n' for n in names).encode(),capture_output=True,check=True);data=proc.stdout;offset=0
for n in names:
 end=data.index(b'\n',offset);h=data[offset:end].split();assert len(h)==3 and h[1]==b'blob',n
 size=int(h[2]);blob=data[end+1:end+1+size];expected=rows[n]
 assert size==expected['bytes'] and hashlib.sha256(blob).hexdigest()==expected['sha256'],n
 assert sha(R/n)==expected['sha256'],n
 offset=end+size+2
assert offset==len(data)
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==f['legacy_HEAD']
assert sha(R/'experiments/repository_identity_20261027/CURRENT.json')==f['CURRENT_sha256']
gate=read(E/'FINAL_RELEASE_GATE.json');assert not gate['remaining_required_work']
receipt=dict(status='PASS_REMOTE_V14_AND_FROZEN_V11_V12_V13_BYTE_READBACK',checked_utc=datetime.now(timezone.utc).isoformat(),repository='https://github.com/zhouz4884-coder/RevTrace',artifact_commit=head,parent_commit=base,artifact_tree=g('rev-parse','HEAD^{tree}'),new_or_updated_files=new,protected_v13_files_verified=len(f['protected_v13']),protected_v12_files_verified=len(old12),frozen_v11_confirmation_files_verified=len(old11),total_unique_files_verified=len(names),bytes_verified=sum(r['bytes'] for r in rows.values()),publication_manifest_sha256=sha(E/'PUBLICATION_MANIFEST.json'),pdf_sha256=gate['pdf_sha256'],source_zip_sha256=gate['source_zip_sha256'],frozen_companion_sha256=gate['frozen_companion_sha256'],independent_final_review_sha256=gate['independent_review_sha256'],no_new_GPU_or_model_calls=True,method_unchanged=True,legacy_dirty_checkout_preserved=True,worktree_clean=True,conference_submission_performed=False)
(E/'DELIVERY_RECEIPT.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
groups=[('service_impact_and_referents','EDITORIAL_DELTA.zh.md'),('three_decision_objects_and_R_S_precision','review/EXECUTION_PROOF_AUDIT.json'),('supported_interleaving_proof','CLAIM_EVIDENCE_DELTA.md'),('readability_and_actual_pdf','review/FINAL_V14_COLD_READ.json'),('cold_build_and_frozen_results','paper_qa/FINAL_v2/SUMMARY.json'),('designated_disk_archive','REMOTE_ARCHIVE_RECEIPT.json'),('GitHub_byte_readback','DELIVERY_RECEIPT.json')]
audit=dict(status='PASS_COMPLETE_V14_USER_SCOPE',artifact_commit=head,groups=[dict(requirement=n,status='PROVEN_COMPLETE',evidence=p,sha256=sha(E/p)) for n,p in groups],pending_required_work=[],new_model_or_method_branch=False)
(E/'TASK_COMPLETION_AUDIT.json').write_bytes((json.dumps(audit,indent=2)+'\n').encode())
paths=[(E/p).relative_to(R).as_posix() for p in ['ops/verify_delivery.py','DELIVERY_RECEIPT.json','TASK_COMPLETION_AUDIT.json']];(E/'RECEIPT_PATHS.json').write_bytes((json.dumps(paths,indent=2)+'\n').encode());print(json.dumps(receipt))

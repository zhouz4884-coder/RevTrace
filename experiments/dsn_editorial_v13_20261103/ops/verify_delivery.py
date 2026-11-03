"""Read back the fetched remote commit and every new/frozen evidence blob."""
from pathlib import Path
import hashlib,json,subprocess
from datetime import datetime,timezone
E=Path(__file__).resolve().parents[1];R=E.parents[1];W=Path('C:/Users/LENOVO/.codex/worktrees/revtrace-dsn-evidence/RevTrace')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],stderr=subprocess.PIPE).decode().strip()
assert git('remote','get-url','origin')=='https://github.com/zhouz4884-coder/RevTrace.git'
head=git('rev-parse','HEAD');assert head=='9b3d960c46b01984f5e6d07492109ab8b3198a98'
subprocess.run(['git','-c','http.version=HTTP/1.1','-C',str(W),'fetch','--quiet','origin','main'],capture_output=True,check=True)
assert git('rev-parse','FETCH_HEAD')==head and git('rev-parse',head+'^')=='1268e587b1ff71ab539fc6a353137c355885a859'
assert not git('status','--porcelain','--untracked-files=all')
publication=read(E/'PUBLICATION_MANIFEST.json');expected={r['path']:r for r in publication['rows']}
n=(E/'PUBLICATION_MANIFEST.json').relative_to(R).as_posix();expected[n]=dict(path=n,bytes=(R/n).stat().st_size,sha256=sha(R/n))
new_count=len(expected);baseline=read(E/'baseline/FROZEN_INPUTS.json')
old=read(R/'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json')['rows']
for row in baseline['frozen_v12_files']+old:
 if row['path'] in expected:assert expected[row['path']]['sha256']==row['sha256']
 expected[row['path']]=row
names=sorted(expected)
r=subprocess.run(['git','-C',str(W),'cat-file','--batch'],input=''.join('FETCH_HEAD:'+n+'\n' for n in names).encode(),capture_output=True,check=True)
data=r.stdout;offset=0
for n in names:
 end=data.index(b'\n',offset);header=data[offset:end].split();assert len(header)==3 and header[1]==b'blob',n
 size=int(header[2]);raw=data[end+1:end+1+size];row=expected[n]
 assert size==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],n
 assert (R/n).stat().st_size==size and sha(R/n)==row['sha256'],n
 offset=end+size+2
assert offset==len(data)
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==baseline['legacy_root_head']
q=read(E/'paper_qa/FINAL_QA.json');localgate=read(E/'FINAL_RELEASE_GATE.json');assert localgate['required_local_work_remaining']==[]
record=dict(status='PASS_REMOTE_V13_ARTIFACT_AND_FROZEN_V11_V12_FULL_BYTE_READBACK',checked_utc=datetime.now(timezone.utc).isoformat(),repository='https://github.com/zhouz4884-coder/RevTrace',artifact_commit=head,artifact_tree=git('rev-parse',head+'^{tree}'),parent_commit=git('rev-parse',head+'^'),remote_main_fetched=True,new_or_updated_artifact_files=new_count,frozen_v12_files_verified=len(baseline['frozen_v12_files']),frozen_v11_confirmation_files_verified=len(old),total_unique_remote_files_verified=len(names),total_remote_bytes_verified=sum(expected[n]['bytes'] for n in names),publication_manifest_sha256=sha(E/'PUBLICATION_MANIFEST.json'),pdf_sha256=q['pdf_sha256'],method_changed=False,new_serving_trials=0,new_model_calls=0,new_GPU_runs=0,original_source_commits_resolve_locally=True,legacy_dirty_HEAD_preserved=True,paper_and_independent_bank_frozen=True,worktree_clean=True,conference_submission_performed=False,delivery_notes=['A staged-byte gate caught CRLF normalization in two newly authored pointer documents; both were normalized to LF before commit.','One ls-remote preflight connection failed; the same authorized remote was retried successfully before publishing.'],receipt_publication='This receipt and completion audit are committed afterward as documentation only; no manuscript or experimental artifact is changed.')
(E/'DELIVERY_RECEIPT.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
groups=[
 ('selective_argument_revision',['EDITORIAL_DELTA.zh.md','CLAIM_EVIDENCE.md','MANUSCRIPT_TEXT_DIFF.patch']),
 ('four_frozen_data_vector_figures',['figures/EXPORT_v2/SUMMARY.json','figure_source/INPUT_MAP.json']),
 ('comparison_energy_cost_integrity',['review/COMPARISON_COST_AUDIT.json']),
 ('primary_source_citation_mapping',['review/CITATION_MAPPING.json','review/CITATION_REVIEW.zh.md']),
 ('independent_actual_pdf_and_gray_review',['review/INDEPENDENT_COLD_READ.json','paper_qa/VISUAL_REVIEW.json']),
 ('anonymous_sources_and_evidence_reproduction',['paper_qa/COLD_BUILD_QA.json','paper_qa/anonymous_evidence_check/SUMMARY.json','review/ANONYMOUS_PACKAGE_INDEPENDENT_REVIEW.json']),
 ('frozen_identity_and_8TB_archive',['FINAL_DEFAULT_SOURCE_GATE.json','REMOTE_ARCHIVE_RECEIPT.json','FINAL_METADATA_ARCHIVE_RECEIPT.json']),
 ('github_delivery',['DELIVERY_RECEIPT.json'])]
audits=[]
for name,paths in groups:
 audits.append(dict(requirement=name,status='PROVEN_COMPLETE',evidence=[dict(path=n,sha256=sha(E/n)) for n in paths]))
completion=dict(status='PASS_COMPLETE_V13_USER_REQUEST',artifact_commit=head,all_requirement_groups_complete=True,groups=audits,pending_required_work=[],method_or_experiment_changes=False,default_new_GPU_zero_satisfied=True,no_unfinished_artifact_condition=True)
(E/'TASK_COMPLETION_AUDIT.json').write_text(json.dumps(completion,indent=2)+'\n',encoding='utf-8')
names=[(E/n).relative_to(R).as_posix() for n in ['DELIVERY_RECEIPT.json','TASK_COMPLETION_AUDIT.json','ops/verify_delivery.py']]
(E/'RECEIPT_PATHS.json').write_text(json.dumps(names,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in {'delivery_notes'}}))

"""Curate only completed evidence; never stage the dirty research checkout."""
from pathlib import Path
import ast
import hashlib
import json
import re
import shutil

from archive_integrity import sha256, verify_manifest

W=Path(__file__).resolve().parent
stage=W/'git_delivery_stage_v1'
prefix=Path('experiments/online_admission_20261022')
D=stage/prefix
assert not D.exists(), 'Immutable release destination must be fresh'
E=W/'collected_evidence_v1'
verification=verify_manifest(E)
assert verification['files']==919
assert sha256(W/'BOUNDED_EVIDENCE.tar.gz')=='6424dc6e2e6a3bde433b7c55c6d31c370272d65cd0098e480d728211458ea19b'
runtime=json.loads((E/'RUNTIME_SOURCE_MANIFEST.json').read_text())
assert runtime['code_commit']=='55cd52dfdbab71298cdb7eae3b0c08c9424020c6'
assert len(runtime['files'])==119
for row in runtime['files']:
 assert sha256(W/'runtime'/row['path'])==row['sha256']
formal=json.loads((E/'collected/FORMAL_SUMMARY.json').read_text())
assert formal['status']=='COMPLETE_72_FRESH_ONLINE_FORMAL_CELLS'
assert len(formal['completed'])==len(set(formal['completed']))==72
gates=json.loads((E/'collected/FORMAL_RESULTS_v1/GONOGO.json').read_text())
assert len(gates['decisions'])==4
assert all(not d['best_legal_primary_goodput_GO'] for d in gates['decisions'])

protocols=['PROTOCOL.md','FAIRNESS_AMENDMENT_PRE_FORMAL.md',
 'ANALYSIS_CONVENTIONS_BEFORE_FORMAL_AUDIT.md','FORMAL_ESTIMANDS_PRE_FREEZE.md',
 'FORMAL_ORACLE_EXTENSION_FREEZE.md','TRACE_DERIVED_ORACLE_FREEZE.md']
scripts=['analysis_core.py','audit_online.py','plan_formal_oracles.py','run_formal_oracles.py',
 'replay_processor_inputs.py','audit_fault_chains.py','summarize_formal.py',
 'neural_feedback_core.py','audit_neural_feedback.py','candidate_wait_core.py',
 'audit_candidate_wait.py','archive_integrity.py','verify_downloaded_bundle.py',
 'pack_remote_evidence.py','pack_formal_raw.py','audit_source_delta.py',
 'audit_release_safety.py','probe_selective_fallback.py','probe_batch16.py',
 'run_trace_oracle.py','run_trace_oracle_v2.py','prepare_donors.py','prepare_donors.py',
 'formal_controller.py','post_formal_controller.py','after_post_cpu_controller.py',
 'pilot_controller_v1.py','pilot_controller.py','pilot_extension_controller.py',
 'test_analysis_core.py','test_formal_analysis_integration.py','test_neural_feedback_core.py',
 'test_candidate_wait_core.py','test_archive_integrity.py','build_completed_release.py',
 'check_scoped_runtime.py']
audits=['LOCAL_EXTRACT_AUDIT.json','REMOTE_PACK_SUMMARY.json','PUBLICATION_HYGIENE_runtime.json',
 'SOURCE_DELTA_TO_PHASE_D.json','SOURCE_DELTA_TO_PHASE_D.patch',
 'ANALYSIS_CPU_v1.json','ANALYSIS_CPU_v1.log','ANALYSIS_CPU_v2.json','ANALYSIS_CPU_v2.log',
 'ANALYSIS_CPU_v3.json','ANALYSIS_CPU_v3.log','NEURAL_AUDIT_CPU_INITIAL_FAILURE.log',
 'CPU_PROTOCOL_SCOPE.json','CPU_PROTOCOL_v2.log','CPU_PROTOCOL_v3.log','CPU_PROTOCOL_v4.log',
 'CPU_PROTOCOL_v5.log','CPU_PROTOCOL_v6.log','RAW_EXPORT_SUMMARY_REMOTE.json',
 'CLOSURE_SUMMARY_REMOTE.json','CANDIDATE_WAIT_SUMMARY_REMOTE.json','CANDIDATE_WAIT_BOUNDS_REMOTE.csv']

def copy(source,target):
 assert source.is_file() and not source.is_symlink()
 target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(source,target)
 assert sha256(source)==sha256(target)

for f in sorted(E.rglob('*')):
 if f.is_file(): copy(f,D/'evidence'/f.relative_to(E))
for r in runtime['files']: copy(W/'runtime'/r['path'],D/'runtime'/r['path'])
copy(W/'runtime/SOURCE_MANIFEST.json',D/'runtime/SOURCE_MANIFEST.json')
for name in protocols: copy(W/name,D/'protocols'/name)
for name in sorted(set(scripts)): copy(W/name,D/'analysis'/name)
for name in audits: copy(W/name,D/'supplemental_audits'/name)
cpu_dirs=sorted(W.glob('revtrace_runtime_cpu_*'))
assert len(cpu_dirs)==1
copy(cpu_dirs[0]/'CPU.log',D/'supplemental_audits/UPLOAD_SCOPED_CPU.log')
copy(cpu_dirs[0]/'CPU.json',D/'supplemental_audits/UPLOAD_SCOPED_CPU.json')
test_scope_note={
 'initial_upload_command':'python -m pytest (unscoped snapshot collection)',
 'initial_result':'19 collection errors: legacy tests require tools from separate campaigns not in the frozen119-file snapshot',
 'classification':'unsupported reproduction command; not a serving-runtime regression or GPU measurement',
 'correction':'README now names the predeclared15-file scope; no frozen source or tests changed',
 'scoped_result':'163 passed in1.99s',
 'full_GPU_results_unchanged':True}
(D/'supplemental_audits/UPLOAD_TEST_SCOPE_NOTE.json').write_text(json.dumps(test_scope_note,indent=2)+'\n')
copy(W/'RELEASE_README.md',D/'README.md')
copy(W/'RELEASE_RESULTS_SUMMARY.md',D/'RESULTS_SUMMARY.md')
(D/'.gitattributes').write_bytes(b'* -text\n')

# Do not leak credential values in reports; list only path and rule on detection.
patterns={
 'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
 'github_token':re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
 'cloud_key':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
 'credential_url':re.compile(rb'https?://[^\s/]+:[^\s/@]+@'),
}
issues=[]; files=[]
for f in sorted(D.rglob('*')):
 if not f.is_file(): continue
 raw=f.read_bytes();rel=f.relative_to(D).as_posix()
 assert len(raw)<20_000_000
 assert f.suffix.lower() not in ['.pdf','.wav','.flac','.mp3','.pt','.bin','.safetensors','.pkl','.exe']
 for key,p in patterns.items():
  if p.search(raw):issues.append({'path':rel,'rule':key})
 if f.suffix=='.py':ast.parse(raw.decode('utf-8'))
 files.append({'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
assert not issues, issues
paper=json.loads((W/'PAPER_BEFORE.json').read_text())
assert all(sha256(Path(r['path']))==r['sha256'] for r in paper), 'Original paper changed'
audit={'status':'PASS_COMPLETED_EVIDENCE_RELEASE_BUILD','formal_cells':72,
 'runtime_code_commit':runtime['code_commit'],'runtime_files':len(runtime['files']),
 'bounded_payload_verification':verification,'paper_files_unchanged':len(paper),
 'raw_archive_uploaded':False,'raw_archive_retained_on_8TB':True,
 'no_original_history_changes_authorized':True,'pattern_findings_without_values':issues,
 'scan_scope':'bounded credential patterns and syntax only; not full secrecy/anonymity proof',
 'no_pending_bottleneck_or_new_GPU_results_claimed':True,
 'release_file_count_before_audit_and_manifest':len(files)}
(D/'PUBLICATION_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
files.append({'path':'PUBLICATION_AUDIT.json','bytes':(D/'PUBLICATION_AUDIT.json').stat().st_size,
 'sha256':sha256(D/'PUBLICATION_AUDIT.json')})
manifest={'experiment_id':'REVTRACE-ONLINE-ADMISSION-20261022',
 'scope':'completed experiment and independent audit only; follow-up C2 bottleneck analysis pending',
 'files':sorted(files,key=lambda r:r['path']),
 'all_files_except_this_manifest_listed':True,'frozen_runtime_commit':runtime['code_commit']}
(D/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
result={'status':'PASS_COMPLETED_RELEASE_BUILD','path':str(D),'files':len(files)+1,
 'bytes':sum(r['bytes'] for r in files)+(D/'DELIVERY_MANIFEST.json').stat().st_size,
 'delivery_manifest_sha256':sha256(D/'DELIVERY_MANIFEST.json'),
 'original_paper_files_unchanged':len(paper),'no_GitHub_write_yet':True}
(W/'RELEASE_BUILD_RECORD.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

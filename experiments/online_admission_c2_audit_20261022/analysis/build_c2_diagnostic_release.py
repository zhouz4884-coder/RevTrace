"""Publish bounded read-only C2 diagnosis separately from the frozen GPU release."""
from pathlib import Path
import hashlib,json,shutil

W=Path(__file__).resolve().parent
D=W/'git_delivery_stage_v1/experiments/online_admission_c2_audit_20261022'
assert not D.exists()
report=json.loads((W/'C2_BOTTLENECK_v1/INDEPENDENT_VERIFICATION.json').read_text())
assert report['status']=='PASS_C2_DERIVED_AND_RAW_AGREEMENT'
assert report['first_views']==5868 and report['maximum_original_vs_raw_reconstructed_display_difference_s']==0
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(a,b):
 assert a.is_file() and not a.is_symlink()
 b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b);assert sha(a)==sha(b)
for src,dest in [('C2_BOTTLENECK_v1','table_decomposition'),
                 ('C2_RAW_DIAGNOSTIC_v1','raw_visibility'),
                 ('C2_RESIDUAL_OPPORTUNITY_v1','opportunity_screen')]:
 for p in sorted((W/src).iterdir()):
  assert p.is_file() and p.suffix in ['.json','.csv']
  assert p.name!='STOP.json';copy(p,D/dest/p.name)
for name in ['analyze_c2_tables.py','audit_c2_raw.py','audit_c2_rescue_space.py',
             'verify_c2_diagnostics.py','build_c2_diagnostic_release.py']:
 copy(W/name,D/'analysis'/name)
copy(W/'C2_BOTTLENECK_FINDINGS_AND_PLAN.zh.md',D/'README.md')
(D/'.gitattributes').write_bytes(b'* -text\n')
identity={
 'experiment_id':'REVTRACE-ONLINE-ADMISSION-20261022-C2-READONLY-DIAGNOSIS',
 'frozen_runtime_commit':'55cd52dfdbab71298cdb7eae3b0c08c9424020c6',
 'completed_GPU_evidence_release':'b0b7abd4881df2bf7697205eb750585f50b66687',
 'original_raw_index_sha256':sha(W/'collected_evidence_v1/RAW_EVIDENCE_INDEX.json'),
 'existing_common_frontiers':11736,'raw_visibility_cells':36,'raw_visibility_frontiers':5868,
 'new_GPU_model_calls':0,'original_result_bytes_unchanged':True,
 'original_performance_gates':'All four strata remain NO-GO; quality noninferiority not established',
 'new_decision':'GO bounded timestamp/feasibility probe only; NO-GO full new algorithm implementation now',
 'not_a_faster_system_or_completed_repair':True,
 'prior_Elastic_NO_GO_retained':True,
 'root_source':[
  {'path':str(p.relative_to(W/'runtime')),'sha256':sha(p)} for p in [
   W/'runtime/scripts/tc_live_worker.py',W/'runtime/src/revtrace/live_qwen.py',
   W/'runtime/src/revtrace/certified_display.py',W/'runtime/src/revtrace/continuity_proof.py']],
 'prior_elastic_decision_sha256':sha(Path('D:/StreamTxn/outputs/revtrace_elastic_20261022/public_release/C2_UPGRADE_DECISION.md'))}
(D/'IDENTITY_AND_DECISION.json').write_text(json.dumps(identity,indent=2)+'\n')
files=[{'path':p.relative_to(D).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
       for p in sorted(D.rglob('*')) if p.is_file()]
(D/'MANIFEST.json').write_text(json.dumps({'files':files,
 'scope':'Existing GPU evidence read-only diagnosis; proposed mechanisms not implemented/tested'},indent=2)+'\n')
out={'status':'PASS_C2_DIAGNOSTIC_RELEASE_BUILD','files':len(files)+1,'bytes':sum(r['bytes'] for r in files),
 'manifest_sha256':sha(D/'MANIFEST.json'),'path':str(D),'new_GPU_model_calls':0}
(W/'C2_RELEASE_BUILD_RECORD.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

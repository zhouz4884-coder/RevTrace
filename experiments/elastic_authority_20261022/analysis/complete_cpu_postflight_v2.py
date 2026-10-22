"""Resolve generated-manifest self-entry, never alter measured source or results."""
from pathlib import Path
import hashlib,json,subprocess,sys
B=Path(sys.argv[1]);P=B/'projects/revtrace_elastic_20261022';O=B/'results/revtrace/elastic_20261022'
assert json.loads((O/'formal_audit/AUDIT_REPORT.json').read_text())['cells']==24
original=json.loads((O/'FORMAL_DECISION.json').read_text());(O/'FORMAL_DECISION_INITIAL.json').write_text(json.dumps(original,indent=2)+'\n')
subprocess.run([sys.executable,str(P/'analyze_formal_diagnostics.py'),str(B)],check=True)
updated=json.loads((O/'FORMAL_DECISION.json').read_text())
assert {k:v for k,v in updated.items() if k!='simple_dynamic_vs_fixed_diagnostics'}==original,'Frozen main criteria changed'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
sources=[];metadata=[]
for sdk in ['fixed_sdk','stress_sdk','elastic_sdk']:
 m=json.loads((P/sdk/'SOURCE_MANIFEST.json').read_text());checked=0
 for r in m['files']:
  if r['path']=='SOURCE_MANIFEST.json':
   metadata.append({'sdk':sdk,'path':r['path'],'declared_prior_manifest_sha256':r['sha256'],'current_manifest_sha256':sha(P/sdk/r['path']),'scope':'generated metadata self-entry inherited at copy; not executable source; measured archive not rewritten'})
   continue
  assert sha(P/sdk/r['path'])==r['sha256'],sdk+'/'+r['path'];checked+=1
 sources.append({'sdk':sdk,'code_commit':m['code_commit'],'executable_and_auxiliary_source_files_verified':checked,'manifest_sha256':sha(P/sdk/'SOURCE_MANIFEST.json')})
weights=json.loads((O/'FORMAL_FREEZE.json').read_text())['weights_verified_before_GPU']
for r in weights:assert sha(B/'models/Qwen3-ASR-1.7B'/r['file'])==r['sha256']
resource=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True)
out={'status':'PASS_COMPLETE_ELASTIC_FORMAL_AND_INDEPENDENT_ANALYSIS','sources_verified':sources,'generated_manifest_self_entry_annotation':metadata,'all_executable_hashes_match':True,'main_statistics_unchanged_by_added_diagnostics':True,'model_weights_match_before_after':True,'GPU_compute_processes_at_check':resource,'no_more_GPU_work':True,'formal_cells':24,'scout_cells':18,'no_new_C1_C3_fault_campaigns':True}
(O/'POSTFLIGHT.json').write_text(json.dumps(out,indent=2)+'\n');print('POSTFLIGHT_COMPLETE_WITH_GENERATED_METADATA_ANNOTATION',flush=True)

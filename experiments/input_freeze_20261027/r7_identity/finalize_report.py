"""Assemble local bounded provenance receipt; no remote calls or source import."""
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inputs=read('SUMMARY.json');local=read('LOCAL_RECONCILIATION.json');model=read('MODEL_AND_EXECUTOR_IDENTITY.json')
index=read('REMOTE_INDEX.json');base='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
summary=dict(task='R7 historical source/environment/input identity audit',
 old_quality_execution_commit='UNKNOWN',old_quality_execution_environment='UNKNOWN',
 current_observed_CODE_COMMIT=local['current_remote_CODE_COMMIT'],
 current_remote_source_is_mixed_later_snapshot=True,
 observed_source_matches=local['source_files'],executor_source_matches=model['executor_git_matches'],
 raw_input_validation=inputs,
 input_seed_packing_matches_128_of_128=local['seed_recipe_matches']==128,
 original_vs_traced_text_quality_deltas=local['paired_vs_traced_changed_rows'],
 missing_historical_fields=['loaded complete source hashes/commit','quality-run environment record','actual selected model-weight SHA',
   'EFSC complete input P and actual processed input tensors','original concatenated waveform SHA','per-window physical timing'],
 model_current_files=index['roots'][base+'/models/whisper-base.en']['files'],
 current_env_metadata=index['roots'][base+'/envs/streamtxn-cu128']['files'],
 r8_cost_index=[r for r in index['roots'][base+'/results/revtrace/r8_csdr']['files'] if any(x in r['path'] for x in ('snapshot-delta','replay-audit','service-'))],
 decisions=dict(input_reconstruction='GO',new_source_frozen_faithful_replication='GO_AFTER_WEIGHT_ENV_AND_INPUT_LOG_GATES',
    retrospectively_attesting_historical_GPU_execution='NO_GO_MISSING_BINDING',algorithm_claim='OUT_OF_SCOPE_SEPARATE_AUDIT'),
 audit_source_bundle=dict(path='R7_INPUT_AUDIT_SOURCE.bundle',code_commit=inputs['code_commit'],sha256=sha(P/'R7_INPUT_AUDIT_SOURCE.bundle')),
 no_historical_mutation=True,new_GPU_calls=0)
(P/'IDENTITY_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n')
files=[]
for p in sorted(P.rglob('*')):
 if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name!='DELIVERY_MANIFEST.json':
  files.append(dict(path=p.relative_to(P).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
(P/'DELIVERY_MANIFEST.json').write_text(json.dumps(dict(files=files,count=len(files),total_bytes=sum(x['bytes'] for x in files)),indent=2)+'\n')
print(json.dumps(dict(files=len(files),bytes=sum(x['bytes'] for x in files),manifest_sha256=sha(P/'DELIVERY_MANIFEST.json'),
 report_sha256=sha(P/'REPORT.md'),identity_sha256=sha(P/'IDENTITY_AUDIT.json'),bundle_sha256=sha(P/'R7_INPUT_AUDIT_SOURCE.bundle'))))

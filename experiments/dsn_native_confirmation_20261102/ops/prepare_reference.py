from pathlib import Path
import hashlib,json
from remote import Remote,E,B,P,O,PY
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
with Remote() as c:
 for n in ['SOURCE_RECEIPT.json','DATA_MANIFEST.json','GATE.json','SUMMARY.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','ATTEMPTS.json']:
  try:c.get(O+'/audio_acquisition_v2/'+n,E/'selection/ACQUISITION_RESULTS_v2'/n)
  except FileNotFoundError:pass
 actual=E/'confirmation/ASSET_BYTE_GATE_v1.json';asset=json.loads(actual.read_bytes())
 assert asset['gate']=='PASS_DECLARED_MODEL_ASSET_BYTES' and asset['files']==31
 declared=dict(status=asset['gate'],all_asset_bytes_verified=True,files=asset['files'],bytes=asset['bytes'],original_receipt_sha256=sha(actual),source_manifest_sha256=asset['manifest_sha256'],verified_utc=asset['utc'])
 ap=E/'confirmation/ASSET_GATE_BINDING_v1.json';ap.write_text(json.dumps(declared,indent=2)+'\n');c.put(ap,P+'/ASSET_GATE_BINDING_v1.json');c.put(actual,P+'/ASSET_BYTE_GATE_v1.json')
 src=P+'/reference_v2';plan=P+'/REFERENCE_PLAN_v1.json';out=O+'/short_references_v1';pre=P+'/REFERENCE_ENTRY_v1.json'
 template=B+'/results/revtrace/dsn_strengthening_20261031/paired32_v2/cells/SC_PAIRED32_V2_BAC009S0908W0369_final_fullcall_r0/CONFIG.json'
 env=B+'/projects/revtrace_dsn_strengthening_20261031/ENVIRONMENT_v2_FROZEN.json'
 args=[PY,'-B',src+'/make_reference_plan.py','--template',template,'--selection-receipt',O+'/audio_acquisition_v2/SOURCE_RECEIPT.json','--environment',env,'--base-source',B+'/projects/revtrace_dsn_native_resilience_20261030/source_v2','--base-manifest',B+'/projects/revtrace_dsn_native_resilience_20261030/SOURCE_v2.json','--asset-byte-gate',P+'/ASSET_GATE_BINDING_v1.json','--gpu','0','--gpu-uuid','GPU-ef01d441-985f-50b3-6e64-5d4c3e2def3a','--cache-root',B+'/cache/revtrace_dsn_native_confirmation_20261102','--raw-out',out,'--out',plan]
 print(c.python('import subprocess\nsubprocess.run('+repr(args)+',check=True)\n').decode())
 lp=E/'confirmation/REFERENCE_PLAN_v1.json';c.get(plan,lp)
 m=E/'packages/REFERENCE_V2_SOURCE.json';identity=json.loads(m.read_bytes())
 job=dict(tag='REFERENCE_RUN_V1',experiment_id='REVTRACE-FROZEN-NEW-SPEAKER-SHORT-REFERENCE-20261102-V1',code_commit=identity['code_commit'],local_source=str((E/'confirmation/reference_source_v2').relative_to(E.parents[1])),local_manifest=str(m.relative_to(E.parents[1])),remote_source=src,out=out,command=[PY,'-B',src+'/run_reference.py','--plan',plan,'--manifest',P+'/REFERENCE_V2_SOURCE.json','--prelaunch',pre],frozen_input_files={plan:sha(lp)},entry_prelaunch_file=pre,entry_config_sha256=sha(lp),entry_prelaunch_extra=dict(exclusive_GPU_window_authorized_by_root=True))
 jp=E/'confirmation/REFERENCE_JOB_v1.json';assert not jp.exists();jp.write_text(json.dumps(job,indent=2)+'\n');print(json.dumps(dict(job=str(jp),expected_sources=8)))

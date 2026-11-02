from pathlib import Path
import hashlib,json
from remote import Remote,E,B,P,O,PY
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
with Remote() as c:
 for n in ['REFERENCE_RECEIPT.json','GATE.json','SUMMARY.json','GENESIS.json','RUN_RECORD.json','ENVIRONMENT.json']:
  try:c.get(O+'/short_references_v1/'+n,E/'confirmation/REFERENCE_RESULTS_v1'/n)
  except FileNotFoundError:
   if n in ('REFERENCE_RECEIPT.json','GATE.json','SUMMARY.json'):raise
 receipt=json.loads((E/'confirmation/REFERENCE_RESULTS_v1/REFERENCE_RECEIPT.json').read_bytes())
 assert receipt['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES'
 src=P+'/confirmation_v2';plan=P+'/SERVICE_PLAN_v1.json';out=O+'/service_confirmation_v1';pre=P+'/SERVICE_ENTRY_v1.json'
 old=B+'/projects/revtrace_dsn_strengthening_20261031';nn=B+'/projects/revtrace_dsn_native_resilience_20261030'
 args=[PY,'-B',src+'/make_service_plan.py','--manifest',P+'/CONFIRMATION_V2_SOURCE.json','--selection-receipt',O+'/audio_acquisition_v2/SOURCE_RECEIPT.json','--reference-receipt',O+'/short_references_v1/REFERENCE_RECEIPT.json','--template',old+'/paired32_v2_configs/SC_PAIRED32_V2_BAC009S0908W0369_final_fullcall_r0.json','--environment',old+'/ENVIRONMENT_v2_FROZEN.json','--base-source',nn+'/source_v2','--base-manifest',nn+'/SOURCE_v2.json','--support-source',old+'/paired_resident_source_v2','--support-manifest',old+'/PAIRED_RESIDENT_SOURCE_v2.json','--expected-sources','8','--config-dir',P+'/service_configs_v1','--raw-root',out,'--out',plan]
 print(c.python('import subprocess\nsubprocess.run('+repr(args)+',check=True)\n').decode())
 lp=E/'confirmation/SERVICE_PLAN_v1.json';c.get(plan,lp);j=json.loads(lp.read_bytes());assert len(j['cells'])==32
 for cell in j['cells']:c.get(cell['config'],E/'confirmation/service_configs_v1'/Path(cell['config']).name)
 asset=json.loads((E/'confirmation/ASSET_GATE_BINDING_v1.json').read_bytes());actual=json.loads((E/'confirmation/ASSET_BYTE_GATE_v1.json').read_bytes());asset['asset_manifest_sha256']=actual['manifest_sha256']
 ap=E/'confirmation/SERVICE_ASSET_GATE_v1.json';ap.write_text(json.dumps(asset,indent=2)+'\n');c.put(ap,P+'/SERVICE_ASSET_GATE_v1.json')
 m=E/'packages/CONFIRMATION_V2_SOURCE.json';ident=json.loads(m.read_bytes())
 job=dict(tag='SERVICE_RUN_V1',experiment_id=j['experiment_id'],code_commit=ident['code_commit'],local_source=str((E/'confirmation/driver_source_v2').relative_to(E.parents[1])),local_manifest=str(m.relative_to(E.parents[1])),remote_source=src,out=out,command=[PY,'-B',src+'/run_confirmation.py','--plan',plan,'--manifest',P+'/CONFIRMATION_V2_SOURCE.json','--prelaunch',pre,'--out',out],frozen_input_files={plan:sha(lp)},entry_prelaunch_file=pre,entry_config_sha256=sha(lp),entry_prelaunch_extra=dict(plan_sha256=sha(lp),exclusive_GPU_window_authorized_by_root=True,asset_byte_gate=dict(path=P+'/SERVICE_ASSET_GATE_v1.json',sha256=sha(ap))))
 jp=E/'confirmation/SERVICE_JOB_v1.json';assert not jp.exists();jp.write_text(json.dumps(job,indent=2)+'\n');print(json.dumps(dict(job=str(jp),cells=32)))

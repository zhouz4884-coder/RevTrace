import hashlib,json
from remote import Remote,E,B,P,O,PY
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with Remote() as c:
 for n in ['SUMMARY.json','GATE.json','RUN_RECORD.json','ROOT_ACTUAL_TRACE_RECHECK_ENTRY.json']:
  c.get(O+'/service_confirmation_v1/'+n,E/'confirmation/SERVICE_RESULTS_v1'/n)
 root=E/'confirmation/SERVICE_RESULTS_v1';summary=json.loads((root/'SUMMARY.json').read_bytes());assert summary['completed_trials']==32 and summary['status']=='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS'
 closure=json.loads((E/'confirmation/SERVICE_RUN_V1_RESOURCE_CLOSURE.json').read_bytes());assert closure['gate'].startswith('PASS') and closure['cells']==32
 manifest=E/'packages/CONFIRMATION_C4_V1_SOURCE.json';m=json.loads(manifest.read_bytes());dep=B+'/projects/revtrace_dsn_continuity_cost_20261102';depmanifest=E.parents[1]/'experiments/dsn_native_refinement_20261030/packages/TRACE_SOURCE_v2.json'
 src=P+'/confirmation_c4_v1';out=O+'/actual_c4_closure_v1';pre=P+'/C4_CLOSURE_ENTRY_v1.json';plan=E/'confirmation/SERVICE_PLAN_v1.json'
 extra=dict(plan_sha256=sha(plan),service_summary_sha256=sha(root/'SUMMARY.json'),service_gate_sha256=sha(root/'GATE.json'),service_run_record_sha256=sha(root/'RUN_RECORD.json'),controller_manifest_sha256=sha(manifest),checker_manifest_sha256=sha(depmanifest),checker_timeout_seconds=120,NN32_complete_and_exclusive_window_released=True)
 cmd=[PY,'-B',src+'/run_c4_campaign.py','--plan',P+'/SERVICE_PLAN_v1.json','--manifest',P+'/CONFIRMATION_C4_V1_SOURCE.json','--checker-source',dep+'/original_c4_source','--checker-manifest',dep+'/ORIGINAL_C4_SOURCE_v2.json','--prelaunch',pre,'--service-summary',O+'/service_confirmation_v1/SUMMARY.json','--service-gate',O+'/service_confirmation_v1/GATE.json','--service-run-record',O+'/service_confirmation_v1/RUN_RECORD.json','--out',out]
 job=dict(tag='C4_CLOSURE_V1',experiment_id='REVTRACE-CONFIRM32-ORIGINAL-C4-CLOSURE-20261102',code_commit=m['code_commit'],local_source=str((E/'confirmation/c4_driver_dev').relative_to(E.parents[1])),local_manifest=str(manifest.relative_to(E.parents[1])),remote_source=src,out=out,command=cmd,entry_config_sha256=sha(plan),entry_prelaunch_file=pre,entry_prelaunch_extra=extra)
 p=E/'confirmation/C4_CLOSURE_JOB_v1.json';assert not p.exists();p.write_text(json.dumps(job,indent=2)+'\n');print(p)

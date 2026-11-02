from pathlib import Path
import argparse,hashlib,json
from remote import Remote,E,B,P,O,PY
p=argparse.ArgumentParser();p.add_argument('--version',type=int,choices=(1,3),default=3);a=p.parse_args();v=str(a.version)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=E/('packages/TRACE_V'+v+'_SOURCE.json');ident=json.loads(m.read_bytes());out=O+'/trace_accounting_v'+v;src=P+'/trace_v'+v;cf=P+'/TRACE_CONFIG_v'+v+'.json';pre=P+'/TRACE_ENTRY_v'+v+'.json'
with Remote() as c:
 script='S='+repr(src)+'\n'+r'''
import json,os,sys
os.environ.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,S)
from trace_common import current_environment
print(json.dumps(current_environment()))
'''
 raw=c.python(script);env=E/('baseline/TRACE_ENVIRONMENT_v'+v+'.json');env.write_bytes(raw);c.put(env,P+'/TRACE_ENVIRONMENT_v'+v+'.json')
 report=E.parents[1]/'experiments/dsn_native_confirmation_20261102/confirmation/FINAL_REPORT/PAPER_DATA.json'
 cfg=dict(experiment_id='REVTRACE_FROZEN_V11_ORIGINAL32_RECORDED_EVENT_ACCOUNTING_20261102_V1',mode='analysis',analysis_source=dict(source_root=src,source_manifest=P+'/TRACE_V1_SOURCE.json',source_commit=ident['code_commit'],source_manifest_sha256=sha(m)),actual_NN=dict(source_root=B+'/projects/revtrace_dsn_native_resilience_20261030/source_v2',source_manifest=B+'/projects/revtrace_dsn_native_resilience_20261030/SOURCE_v2.json',source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',source_manifest_sha256='60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457'),environment_record=P+'/TRACE_ENVIRONMENT_v1.json',environment_record_sha256=sha(env),raw_index=dict(path=P+'/RAW_INDEX_v1.json',sha256=sha(E/'baseline/RAW_INDEX_v1.json')),verified_report=dict(path=B+'/results/revtrace/dsn_native_confirmation_20261102/report_v2/PAPER_DATA.json',bytes=report.stat().st_size,sha256=sha(report)),raw_base=B+'/results/revtrace/dsn_native_confirmation_20261102/service_confirmation_v1/cells',lease_path=O+'/trace_accounting_v1.lease',raw_result_location=out,aggregate_summary_location=out+'/SUMMARY.json',gate_decision_location=out+'/GATE.json',stdout_location=O+'/trace_run_v1.log',stderr_location=O+'/trace_run_v1.log',stderr_scope='merged by outer launcher into stdout log',minimum_free_bytes=536870912,max_input_bytes=268435456,max_output_bytes=16777216,max_elapsed_seconds=300)
 cfg.update(experiment_id='REVTRACE_FROZEN_V11_ORIGINAL32_RECORDED_EVENT_ACCOUNTING_20261102_V'+v,analysis_source=dict(source_root=src,source_manifest=P+'/TRACE_V'+v+'_SOURCE.json',source_commit=ident['code_commit'],source_manifest_sha256=sha(m)),environment_record=P+'/TRACE_ENVIRONMENT_v'+v+'.json',lease_path=O+'/trace_accounting_v'+v+'.lease',stdout_location=O+'/trace_run_v'+v+'.log',stderr_location=O+'/trace_run_v'+v+'.log')
 lc=E/('TRACE_CONFIG_v'+v+'.json');lc.write_bytes((json.dumps(cfg,indent=2)+'\n').encode());c.put(lc,cf)
 job=dict(tag='TRACE_RUN_V'+v,experiment_id=cfg['experiment_id'],code_commit=ident['code_commit'],local_source=str((E/('trace_source_dev' if v=='1' else 'trace_source_v'+v)).relative_to(E.parents[1])),local_manifest=str(m.relative_to(E.parents[1])),remote_source=src,out=out,command=[PY,'-B',src+'/run_trace.py','--config',cf,'--manifest',P+'/TRACE_V'+v+'_SOURCE.json','--prelaunch',pre,'--out',out],entry_prelaunch_file=pre,entry_config_sha256=sha(lc),frozen_input_files={cf:sha(lc),P+'/RAW_INDEX_v1.json':sha(E/'baseline/RAW_INDEX_v1.json'),P+'/TRACE_ENVIRONMENT_v'+v+'.json':sha(env)})
 p=E/('TRACE_JOB_v'+v+'.json');assert not p.exists();p.write_bytes((json.dumps(job,indent=2)+'\n').encode());print(p)

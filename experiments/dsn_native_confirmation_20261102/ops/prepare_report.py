import argparse,hashlib,json
from remote import Remote,E,P,O,PY
p=argparse.ArgumentParser();p.add_argument('--version',type=int,choices=(1,2),default=2);a=p.parse_args();v=str(a.version)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with Remote() as c:
 for n in ['SUMMARY.json','GATE.json','ROOT_ACTUAL_TRACE_RECHECK_CLOSURE.json','RUN_RECORD.json','ENVIRONMENT.json']:
  c.get(O+'/actual_c4_closure_v1/'+n,E/'confirmation/FINAL_C4_CLOSURE'/n)
 src=P+'/report_v'+v;out=O+'/report_v'+v;cfg=P+'/REPORT_CONFIG_v'+v+'.json';pre=P+'/REPORT_ENTRY_v'+v+'.json'
 cmd=[PY,'-B',src+'/make_report_config.py','--service-plan',P+'/SERVICE_PLAN_v1.json','--campaign',O+'/service_confirmation_v1','--c4-summary',O+'/actual_c4_closure_v1/SUMMARY.json','--c4-gate',O+'/actual_c4_closure_v1/GATE.json','--raw-out',out,'--out',cfg]
 print(c.python('import subprocess\nsubprocess.run('+repr(cmd)+',check=True)\n').decode())
 lc=E/('confirmation/REPORT_CONFIG_v'+v+'.json');c.get(cfg,lc);manifest=E/('packages/REPORT_V'+v+'_SOURCE.json');m=json.loads(manifest.read_bytes())
 job=dict(tag='REPORT_RUN_V'+v,experiment_id=json.loads(lc.read_bytes())['experiment_id'],code_commit=m['code_commit'],local_source=str((E/('confirmation/report_source_dev' if v=='1' else 'confirmation/report_source_v2')).relative_to(E.parents[1])),local_manifest=str(manifest.relative_to(E.parents[1])),remote_source=src,out=out,command=[PY,'-B',src+'/report_confirmation.py','--config',cfg,'--manifest',P+'/REPORT_V'+v+'_SOURCE.json','--prelaunch',pre],entry_config_sha256=sha(lc),entry_prelaunch_file=pre,frozen_input_files={cfg:sha(lc)})
 p=E/('confirmation/REPORT_JOB_v'+v+'.json');assert not p.exists();p.write_text(json.dumps(job,indent=2)+'\n');print(p)

import pathlib,json
O=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028')
r={}
for rel in ['cpu_environment_pipeline_v6/STATUS.json','CPU_ENV_PREPARATION_v6.json','cpu_native_v6/GATE.json','AUTHOR_DEPENDENCY_GATE_v6.json','NATIVE_INTERFACE_CPU_GATE_v6.json','FROZEN_CAMPAIGN_IDENTITY.json']:
 p=O/rel
 if p.exists():r[rel]=json.loads(p.read_text())
log=O/'cpu_environment_pipeline_v6.log'
r['safe_log_tail']=log.read_text()[-6000:] if log.exists() else None
print(json.dumps(r,indent=2))

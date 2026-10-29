"""Only bounded prepared configurations, receipts and CPU logs; no weights/audio."""
import pathlib,json,hashlib,sys,datetime
T=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_20261028';O=B+'/results/revtrace/dsn_streamcorrect_20261028'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client();out=T/'ready_cpu_evidence_v6';out.mkdir(exist_ok=False);records=[]
try:
 s=c.open_sftp()
 paths=[(O+'/'+name,name) for name in ['assets_v1/GATE.json','assets_v1/ASSET_MANIFEST.json','CPU_ENV_PREPARATION_v6.json','ENV_PREPARATION.json','AUTHOR_DEPENDENCY_GATE_v6.json','NATIVE_INTERFACE_CPU_GATE_v6.json','FROZEN_CAMPAIGN_IDENTITY.json','ENVIRONMENT_COMPLETE_v6.json','cpu_environment_pipeline_v6/STATUS.json']]
 paths.append((P+'/NATIVE_CAMPAIGN_v6_FROZEN.json','NATIVE_CAMPAIGN_v6_FROZEN.json'))
 for remote,relative in [(O+'/cpu_native_v6','cpu_native_v6'),(P+'/native_campaign_v6_configs','native_campaign_v6_configs')]:
  for a in s.listdir_attr(remote):
   assert a.filename.endswith(('.json','.log')) and a.st_size<250000
   paths.append((remote+'/'+a.filename,relative+'/'+a.filename))
 for remote,relative in paths:
  assert s.stat(remote).st_size<250000
  with s.open(remote,'rb') as f:b=f.read(250001)
  assert len(b)<=250000
  p=out/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);records.append(dict(remote=remote,path=relative,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
 s.close()
 r=dict(status='PASS_BOUNDED_NATIVE_READINESS_EVIDENCE_COLLECTED_NO_NEURAL_CALLS',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=records,total_bytes=sum(x['bytes'] for x in records),native_neural_calls=0)
 (out/'COLLECTION_MANIFEST.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='files'},indent=2))
 state=T/'CURRENT_STATUS.json';x=json.loads(state.read_text());x.update(status='READY_NATIVE_ENV_AND_FROZEN14_WAITING_CORE_GPU_SEQUENCE',heavy_io_started=True,asset_acquisition='PASS_EXACT_NATIVE_ASSETS_ACQUIRED',native_cpu_readiness='PASS',native_campaign_plan_sha256='ba1f52462534b8ee5286bcaed1f9b5f97042f9b4ac1e8ce9dbedd9d325c9b780',current_phase='exact assets and isolated native environment ready; waiting independent fullSHA read IO then authorized f0joint24',updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());state.write_text(json.dumps(x,indent=2))
finally:c.close()

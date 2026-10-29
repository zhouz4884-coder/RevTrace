import pathlib,json,hashlib,sys
T=pathlib.Path(__file__).resolve().parents[1];E=T/'final_native_v8_evidence';O='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028';P='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_20261028'
primary=json.loads((E/'native_postanalyses_v8/primary_quantiles/SUMMARY.json').read_text(encoding='utf-8'));jobs=[(O+'/native_campaign_v8_cells/'+x['cell_id']+'/ENERGY.json','energy/'+x['cell_id']+'.json') for x in primary['cells']]
jobs.extend([(P+'/NATIVE_CAMPAIGN_v8_FROZEN.json','NATIVE_CAMPAIGN_v8_FROZEN.json'),(P+'/native_campaign_v8_configs/FROZEN_ENVIRONMENT.json','FROZEN_ENVIRONMENT_v8.json')])
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client();records=[]
try:
 s=c.open_sftp()
 for remote,rel in jobs:
  with s.open(remote,'rb') as f:b=f.read(250001)
  assert len(b)<=250000;p=E/rel;p.parent.mkdir(parents=True,exist_ok=True)
  if p.exists():assert p.read_bytes()==b
  else:p.write_bytes(b)
  records.append(dict(remote=remote,path=rel,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
 s.close()
finally:c.close()
(E/'ENERGY_COLLECTION_MANIFEST.json').write_text(json.dumps(dict(files=records,total_bytes=sum(x['bytes'] for x in records)),indent=2),encoding='utf-8')
print(json.dumps(dict(files=len(records),total_bytes=sum(x['bytes'] for x in records),sample=json.loads((E/records[0]['path']).read_text(encoding='utf-8'))),indent=2))

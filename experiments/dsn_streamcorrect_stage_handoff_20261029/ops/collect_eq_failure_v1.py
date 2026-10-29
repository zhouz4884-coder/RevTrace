import pathlib,json,sys,hashlib
T=pathlib.Path(__file__).resolve().parents[1];O='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_stage_handoff_20261029/equivalence_v1';out=T/'EQ_FAILURE_v1';out.mkdir(exist_ok=False)
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client();rows=[]
try:
 s=c.open_sftp()
 for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','READY.json','DETAILS.json','PROGRESS.json','GATE.json','failure.txt']:
  p=out/name;s.get(O+'/'+name,str(p));data=p.read_bytes();assert len(data)<2_000_000
  with s.open(O+'/'+name,'rb') as f:assert f.read()==data
  rows.append(dict(path=name,remote=O+'/'+name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 s.close()
finally:c.close()
(out/'COLLECTION_MANIFEST.json').write_text(json.dumps(dict(files=rows,total_bytes=sum(r['bytes'] for r in rows),all_bytes_equal=True,scope='failed real gate preserved; original models warmed; one early/no-model input completed; not a semantic handoff success'),indent=2),encoding='utf-8');print(json.dumps(rows[-2:],indent=2))

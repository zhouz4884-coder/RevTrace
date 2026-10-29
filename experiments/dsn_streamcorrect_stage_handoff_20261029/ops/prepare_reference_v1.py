import pathlib,sys,shlex,json,hashlib
T=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
code=r'''import pathlib,json,hashlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');p=B/'projects/revtrace_dsn_streamcorrect_20261028/NATIVE_CAMPAIGN_v8_FROZEN.json';n=json.loads(p.read_text());cell=next(c for c in n['cells'] if c['stage']=='formal' and c['cohort']=='A' and c['arm']=='sequential' and c['repeat']==0);cfgpath=pathlib.Path(cell['config']);cfg=json.loads(cfgpath.read_text());histpath=pathlib.Path(cell['out'])/'CANONICAL_HISTORIES.json';h=json.loads(histpath.read_text())[n['sources'][0]['source_id']];r=next(r for r in h if r['F']==24000)
print(json.dumps(dict(original_native_plan=str(p),original_native_plan_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),config_path=str(cfgpath),config_sha256=hashlib.sha256(cfgpath.read_bytes()).hexdigest(),original_histories_path=str(histpath),original_histories_sha256=hashlib.sha256(histpath.read_bytes()).hexdigest(),backend=cfg['settings']['backend'],sources=n['sources'],warmup=dict(source_id=n['sources'][0]['source_id'],original_reference_start_state=r['state'],original_reference_start_state_sha256=r['state_sha256'],fixed_start=24000,fixed_end=32000,discard_output=True,reset_service_genesis=True)),ensure_ascii=False))
'''
c=ssh_client()
try:
 i,o,e=c.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revtrace-streamcorrect-20261028/bin/python -B -',timeout=30);i.write(code);i.flush();i.channel.shutdown_write();data=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();r=json.loads(data);dest=T/'ORIGINAL_FIXED_REFERENCES_v1.json';assert not dest.exists();dest.write_bytes(json.dumps(r,ensure_ascii=False,indent=2).encode('utf-8'));print(json.dumps(dict(path=str(dest),bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())))
finally:c.close()

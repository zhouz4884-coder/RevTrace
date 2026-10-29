import pathlib,json,subprocess,sys,os,hashlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';S=P/'auditfix_source_v1'
bundle=P/'AUDITFIX_SOURCE_v1.bundle';assert hashlib.sha256(bundle.read_bytes()).hexdigest()=='1840248962d7ea1b9e0842d20581a96b02ce4da870da890fe5358ea6781be8dc'
if not S.exists():
 subprocess.run(['git','clone','--no-hardlinks',str(bundle),str(S)],check=True)
 subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(S),'checkout','--detach','a0652a81a205483ba2091dfd345b85be72ee8b19'],check=True)
out=O/'witness_recount_auditfix_v1';assert not out.exists()
r=subprocess.run([sys.executable,'-B',str(S/'auditfix_recount_and_continue.py'),'--mode','recount','--plan',str(P/'NATIVE_CAMPAIGN_v8_FROZEN.json'),'--manifest',str(P/'AUDITFIX_SOURCE_v1.json'),'--out',str(out)],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
print(json.dumps(dict(returncode=r.returncode,gate=json.loads((out/'GATE.json').read_text()) if (out/'GATE.json').exists() else None,witness_gate=json.loads((out/'WITNESS_GATE.json').read_text()) if (out/'WITNESS_GATE.json').exists() else None),indent=2));raise SystemExit(r.returncode)

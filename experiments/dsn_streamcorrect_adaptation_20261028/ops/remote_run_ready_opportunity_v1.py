import pathlib,json,subprocess,sys,os,hashlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028';S=P/'ready_opportunity_source_v1'
mf=P/'READY_OPPORTUNITY_SOURCE_v1.json';m=json.loads(mf.read_text())
if not S.exists():
 subprocess.run(['git','clone','--no-hardlinks',str(P/'READY_OPPORTUNITY_SOURCE_v1.bundle'),str(S)],check=True)
 subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(S),'checkout','--detach',m['source_commit']],check=True)
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==m['source_commit']
for row in m['files']:
 b=(S/row['path']).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
out=O/'ready_opportunity_v1';assert not out.exists()
r=subprocess.run([sys.executable,'-B',str(S/'analyze_ready_opportunities.py'),'--plan',str(P/'NATIVE_CAMPAIGN_v8_FROZEN.json'),'--out',str(out)],env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
raise SystemExit(r.returncode)

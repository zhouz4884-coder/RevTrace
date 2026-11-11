"""Freeze a second implementation only after primary CPU29 gate passes."""
from pathlib import Path
import ast,hashlib,importlib.util,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
original=json.loads((H/'PRELAUNCH_v1.json').read_bytes());originalP=original['remote_source'].rsplit('/',1)[0]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111/history_independent_v1'
O=B+'/results/revtrace/dsn_strengthening_v16_20261111/history_independent_v1'
code='O='+repr(original['raw_result_location'])+'\nP='+repr(originalP)+'\n'+r'''
from pathlib import Path
import hashlib,json
O=Path(O);P=Path(P);gate=O/'GATE.json'
if not gate.exists():print(json.dumps(dict(ready=False)));raise SystemExit()
assert json.loads(gate.read_bytes())['status']=='PASS_ALL_INPUT_BYTES_AND_EDIT_CONSERVATION'
cfg=json.loads((P/'CONFIG_v1.json').read_bytes())
paths=[P/'CONFIG_v1.json',P/'SOURCE_v1.json',O/'GATE.json',O/'SUMMARY.json',O/'RUN_RECORD.json',O/'SOURCE_SUMMARIES.json',
 O/'H3_ALL110_PAIRED_RECOUNT.json',O/'NEW8_EXACT_PAIRED_AND_LEAVE_OUT.json']
paths += [Path(c['consumer_path']) for c in cfg['cells']]+[Path(x['path']) for x in cfg['metadata_inputs'].values()]
paths += list((O/'cells').glob('*/*.json'))
print(json.dumps(dict(ready=True,bound_files=[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths])))
'''
with m.Remote() as c:raw=c.python(code,timeout=60)
inventory=json.loads(raw)
if not inventory['ready']:print('Primary CPU gate pending; audit not frozen or launched.');raise SystemExit()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def run(a):return subprocess.check_output(a,text=True,stderr=subprocess.STDOUT).strip()
rootgate=H/'AUDIT_ROOT_DEFAULT_PREFLIGHT_v1.json'
pointer=R/'experiments/repository_identity_20261027/CURRENT.json';pointer_before=sha(pointer)
run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(rootgate)])
S=H/'audit_source_v1';S.mkdir(exist_ok=False)
for name in ('independent_verify.py','run_independent.py','test_independent.py'):
 p=E/'history_source'/name;ast.parse(p.read_text(encoding='utf8'));shutil.copyfile(p,S/name)
(S/'PROTOCOL.md').write_text('Independent offline proof checker for all29 original Consumer inputs, minimum edit distance, operation/identity/lifetime ledger, all220 metadata contrasts,22 factorials and256 eight-speaker swaps. No model calls. Does not import primary metric modules or independently enumerate all optimal paths.\n',encoding='utf8')
(S/'.gitattributes').write_text('* -text\n',encoding='utf8');(S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
run(['git','-C',str(S),'init']);run(['git','-C',str(S),'config','core.autocrlf','false']);run(['git','-C',str(S),'checkout','-b','codex/v16-history-independent-v1'])
run(['git','-C',str(S),'add','.']);run(['git','-C',str(S),'commit','-m','Freeze independent historical Consumer edit proof checker'])
commit=run(['git','-C',str(S),'rev-parse','HEAD']);files=run(['git','-C',str(S),'ls-files']).splitlines()
manifest=dict(code_commit=commit,files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in files])
mp=H/'AUDIT_SOURCE_v1.json';put(mp,manifest);bundle=H/'AUDIT_SOURCE_v1.bundle'
run(['git','-C',str(S),'bundle','create',str(bundle),'HEAD']);run(['git','-C',str(R),'bundle','verify',str(bundle)])
run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/heads/codex/v16-history-independent-v1'])
run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str(S),'--manifest',str(mp),'--output',str(H/'AUDIT_EXPLICIT_SOURCE_PREFLIGHT_v1.json')])
cfg=dict(experiment_id='REVTRACE-V16-HISTORICAL-INDEPENDENT-PROOF-20261111-V1',designated_experiment_disk_prefix=B,
 primary_config=originalP+'/CONFIG_v1.json',primary_results=original['raw_result_location'],bound_files=inventory['bound_files'],new_model_calls=0)
cp=H/'AUDIT_CONFIG_v1.json';put(cp,cfg);ep=H/'AUDIT_ENVIRONMENT_v1.json';shutil.copyfile(H/'ENVIRONMENT_v1.json',ep)
pre=dict(experiment_id=cfg['experiment_id'],code_commit=commit,source_manifest_sha256=sha(mp),source_bundle_sha256=sha(bundle),
 frozen_config_sha256=sha(cp),environment_sha256=sha(ep),root_preflight_path=P+'/AUDIT_ROOT_DEFAULT_PREFLIGHT_v1.json',root_preflight_sha256=sha(rootgate),
 raw_result_location=O,aggregate_summary_location=O+'/SUMMARY.json',gate_decision_location=O+'/GATE.json',remote_source=P+'/source_v1',
 local_resolvable_ref='refs/heads/codex/v16-history-independent-v1')
pp=H/'AUDIT_PRELAUNCH_v1.json';put(pp,pre)
assert sha(pointer)==pointer_before
with m.Remote() as c:
 c.python('from pathlib import Path\nPath('+repr(P)+').mkdir(parents=True,exist_ok=False)\n')
 for path in (mp,bundle,cp,ep,pp,rootgate):c.put(path,P+'/'+path.name)
 code='P='+repr(P)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
P=Path(P);pre=json.loads((P/'AUDIT_PRELAUNCH_v1.json').read_bytes());S=Path(pre['remote_source']);O=Path(pre['raw_result_location'])
assert hashlib.sha256((P/'AUDIT_SOURCE_v1.bundle').read_bytes()).hexdigest()==pre['source_bundle_sha256']
subprocess.run(['git','clone','-c','core.autocrlf=false','--quiet',str(P/'AUDIT_SOURCE_v1.bundle'),str(S)],check=True)
subprocess.run(['git','-C',str(S),'bundle','verify',str(P/'AUDIT_SOURCE_v1.bundle')],check=True,capture_output=True)
assert not O.exists();O.parent.mkdir(parents=True,exist_ok=True);log=O.parent/'history_independent_v1_PROCESS.log'
args=[sys.executable,'-B',str(S/'run_independent.py'),'--config',str(P/'AUDIT_CONFIG_v1.json'),'--manifest',str(P/'AUDIT_SOURCE_v1.json'),
 '--environment',str(P/'AUDIT_ENVIRONMENT_v1.json'),'--prelaunch',str(P/'AUDIT_PRELAUNCH_v1.json'),'--out',str(O)]
with log.open('x') as f:child=subprocess.Popen(args,cwd=S,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21]
record=dict(pre,pid=child.pid,start_ticks=ticks,argv=args,log=str(log),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0)
(P/'AUDIT_PROCESS_LAUNCH_v1.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
'''
 raw=c.python(code,timeout=60)
(H/'AUDIT_PROCESS_LAUNCH_v1.json').write_bytes(raw+b'\n');print(raw.decode())

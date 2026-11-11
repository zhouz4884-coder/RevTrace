"""Preregister and launch the separately frozen old16 full-job CPU audit."""
from pathlib import Path
import ast,hashlib,importlib.util,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1];H=E/'history_ops';stem='ledger_v2'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111/'+stem
O=B+'/results/revtrace/dsn_strengthening_v16_20261111/'+stem
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def run(a):return subprocess.check_output(a,text=True,stderr=subprocess.STDOUT).strip()
bank=R/'experiments/dsn_streamcorrect_independent_20261029/SERVICE_RESULTS_v1'
archive=json.loads((bank/'COLLECTION_MANIFEST.json').read_bytes());by_remote={r['remote']:r for r in archive['files']}
cells=[];bound=[]
for local in sorted(bank.glob('SC_*')):
 if not local.is_dir():continue
 c=json.loads((local/'CONFIG.json').read_bytes());rr=json.loads((local/'RUN_RECORD.json').read_bytes());assert rr['code_commit']=='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
 names=dict(config='CONFIG.json',events='events.jsonl',native_jobs='native_jobs.jsonl',summary='SUMMARY.json',gate='GATE.json',dispatches='DISPATCHES.json',canonical_histories='CANONICAL_HISTORIES.json',run_record='RUN_RECORD.json')
 if c['arm']=='two_full_spec_early':names['ledger']='FULLSPEC_LEDGER.json'
 files={}
 for name,filename in names.items():
  rp=rr['raw_result_location']+'/'+filename;record=by_remote[rp]
  assert sha(local/filename)==record['sha256'] and (local/filename).stat().st_size==record['bytes']
  spec=dict(path=rp,sha256=record['sha256'],bytes=record['bytes']);files[name]=spec;bound.append(spec)
 cells.append(dict(cell_id=c['cell_id'],arm=c['arm'],repeat=c['repeat'],source_id=c['settings']['sources'][0]['source_id'],files=files))
assert len(cells)==16
rootgate=H/'LEDGER_ROOT_PREFLIGHT_v2.json';run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--output',str(rootgate)])
S=H/'ledger_source_v2';S.mkdir(exist_ok=False)
for p in sorted((H/'ledger_dev_v1').glob('*.py')):ast.parse(p.read_text(encoding='utf8'));shutil.copyfile(p,S/p.name)
(S/'PROTOCOL.md').write_bytes((H/'LEDGER_READONLY_FINDINGS.zh.md').read_bytes())
(S/'.gitattributes').write_text('* -text\n',encoding='utf8');(S/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf8')
run(['git','-C',str(S),'init']);run(['git','-C',str(S),'config','core.autocrlf','false']);run(['git','-C',str(S),'checkout','-b','codex/v16-ledger-v2']);run(['git','-C',str(S),'add','.']);run(['git','-C',str(S),'commit','-m','Freeze full job conservation and actual-parent overlap bounds CPU audit'])
commit=run(['git','-C',str(S),'rev-parse','HEAD']);files=run(['git','-C',str(S),'ls-files']).splitlines()
manifest=dict(code_commit=commit,files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in files]);mp=H/'LEDGER_SOURCE_v2.json';put(mp,manifest)
bundle=H/'LEDGER_SOURCE_v2.bundle';run(['git','-C',str(S),'bundle','create',str(bundle),'HEAD']);run(['git','-C',str(R),'bundle','verify',str(bundle)]);run(['git','-C',str(R),'fetch',str(bundle),'HEAD:refs/heads/codex/v16-ledger-v2'])
run(['python','-B',str(R/'experiments/repository_identity_20261027/preflight.py'),'--source',str(S),'--manifest',str(mp),'--output',str(H/'LEDGER_EXPLICIT_PREFLIGHT_v2.json')])
cfg=dict(experiment_id='REVTRACE-V16-FULL-JOB-LEDGER-20261111-V2',analysis_module='ledger_core',expected_controls=6,designated_experiment_disk_prefix=B,
 measured_neural_commit='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',cells=cells,bound_files=bound,
 estimands='Declared in PROTOCOL.md before launch: complete-call composition, received-to-install interval overlap bounds, missing ASR infer timer, restart proxy, full terminal conservation, late-disproof checkpoint availability; no causal saved-latency claim',new_model_calls=0)
cp=H/'LEDGER_CONFIG_v2.json';put(cp,cfg);ep=H/'LEDGER_ENVIRONMENT_v2.json';shutil.copyfile(H/'ENVIRONMENT_v1.json',ep)
pre=dict(experiment_id=cfg['experiment_id'],code_commit=commit,source_manifest_sha256=sha(mp),source_bundle_sha256=sha(bundle),frozen_config_sha256=sha(cp),environment_sha256=sha(ep),
 root_preflight_path=P+'/'+rootgate.name,root_preflight_sha256=sha(rootgate),raw_result_location=O,aggregate_summary_location=O+'/SUMMARY.json',gate_decision_location=O+'/GATE.json',remote_source=P+'/source_v1')
pp=H/'LEDGER_PRELAUNCH_v2.json';put(pp,pre)
with m.Remote() as c:
 c.python('from pathlib import Path\nPath('+repr(P)+').mkdir(parents=True,exist_ok=False)\n')
 for path in (mp,bundle,cp,ep,pp,rootgate):c.put(path,P+'/'+path.name)
 script='P='+repr(P)+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,os,platform,subprocess,sys
P=Path(P);pre=json.loads((P/'LEDGER_PRELAUNCH_v2.json').read_bytes());S=Path(pre['remote_source']);O=Path(pre['raw_result_location'])
assert hashlib.sha256((P/'LEDGER_SOURCE_v2.bundle').read_bytes()).hexdigest()==pre['source_bundle_sha256']
subprocess.run(['git','clone','-c','core.autocrlf=false','--quiet',str(P/'LEDGER_SOURCE_v2.bundle'),str(S)],check=True)
subprocess.run(['git','-C',str(S),'bundle','verify',str(P/'LEDGER_SOURCE_v2.bundle')],check=True,capture_output=True)
O.parent.mkdir(parents=True,exist_ok=True);log=O.parent/'ledger_v2_PROCESS.log';assert not O.exists()
args=[sys.executable,'-B',str(S/'run_task.py'),'--config',str(P/'LEDGER_CONFIG_v2.json'),'--manifest',str(P/'LEDGER_SOURCE_v2.json'),'--environment',str(P/'LEDGER_ENVIRONMENT_v2.json'),'--prelaunch',str(P/'LEDGER_PRELAUNCH_v2.json'),'--out',str(O)]
with log.open('x') as f:child=subprocess.Popen(args,cwd=S,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21];record=dict(pre,pid=child.pid,start_ticks=ticks,argv=args,log=str(log),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0)
(P/'PROCESS_LAUNCH.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
'''
 raw=c.python(script,timeout=60)
(H/'LEDGER_PROCESS_LAUNCH_v2.json').write_bytes(raw+b'\n');print(raw.decode())

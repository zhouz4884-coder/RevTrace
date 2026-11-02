"""Freeze existing original32 records on8TB, bound back to completed C4 inputs."""
from pathlib import Path
import json
from remote import Remote,E,B,P,O
old=B+'/results/revtrace/dsn_native_confirmation_20261102'
local_old=E.parents[1]/'experiments/dsn_native_confirmation_20261102'
old_gate=json.loads((local_old/'confirmation/FINAL_REPORT/PAPER_DATA.json').read_bytes())
script='C='+repr(dict(old=old,P=P,O=O,plan=B+'/projects/revtrace_dsn_native_confirmation_20261102/SERVICE_PLAN_v1.json',expected_c4_summary_sha=old_gate['C4']['source_summary_sha256']))+'\n'+r'''
from pathlib import Path
import datetime,hashlib,json,platform,subprocess,sys
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def inv(p):p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def put(p,x):
 with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
plan=read(C['plan']);closurepath=Path(C['old'])/'actual_c4_closure_v1/SUMMARY.json'
assert sha(closurepath)==C['expected_c4_summary_sha'];closure=read(closurepath);assert closure['passed_cells']==32
summ=Path(C['old'])/'service_confirmation_v1/SUMMARY.json';ss=read(summ);assert ss['completed_trials']==32
passed={c['cell_id']:c for c in closure['cells']};cells=[];files={};c4rows=[]
for cell in plan['cells']:
 root=Path(cell['out']);prior=passed[cell['cell_id']];cfgpath=Path(prior['frozen_config']);assert sha(cfgpath)==prior['frozen_config_sha256'];cfg=read(cfgpath)
 for path,meta in cfg['inputs'].items():
  assert Path(path).stat().st_size==meta['bytes'] and sha(path)==meta['sha256'],path
 c4rows.append(dict(cell_id=cell['cell_id'],config=inv(cfgpath),original_core_raw_files=len(cfg['inputs']),all_current_core_bytes_equal_original_completed_C4=True))
 owners=sorted(root.glob('owner_e*'),key=lambda p:int(p.name[7:]));assert owners
 required=[root/n for n in ['CONFIG.json','ORIGIN.json','SUMMARY.json','GATE.json','consumer.jsonl','publications.jsonl','facts.wal','ingress.jsonl','supervisor.jsonl']]
 for owner in owners:required += [owner/n for n in ['dispatch.jsonl','worker_results.jsonl','owner_events.jsonl','policy_audit.jsonl']]
 for p in required:
  assert p.is_file() and not p.is_symlink();files[str(p)]=inv(p)
 cfgactual=read(root/'CONFIG.json');assert cfgactual['settings']['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
 cells.append(dict(cell_id=cell['cell_id'],source_id=cell['source_id'],speaker_id=cell['speaker_id'],policy=cell['strategy'],repeat=cell['repeat'],raw_root=str(root),owner_directories=[str(p) for p in owners],frames=cfgactual['settings']['sources'][0]['frames']))
for path in [C['plan'],str(summ),str(closurepath)]:files[path]=inv(path)
for name in ['P','O']:Path(C[name]).mkdir(parents=True,exist_ok=True)
env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),CUDA_compute_owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),scope='Fresh administrative input freeze from existing records only; no model, no new serving run')
receipt=dict(status='FROZEN_COMPLETE_ORIGINAL32_EVENT_INPUTS_NOT_ANALYSIS_RESULT',source_producer='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',original_service_driver='d865af11e9a8d6c451146942d1708a8caed8d1d9',cells=cells,inputs=files,prior_C4_bindings=c4rows,prior_C4_summary=inv(closurepath),original_service_summary=inv(summ),environment=env,new_model_calls=0,new_serving_runs=0)
put(Path(C['P'])/'RAW_INDEX_v1.json',receipt);put(Path(C['P'])/'INPUT_FREEZE_ENVIRONMENT_v1.json',env)
print(json.dumps(dict(status=receipt['status'],cells=len(cells),files=len(files),bytes=sum(x['bytes'] for x in files.values()),prior_C4_original_core_bytes_verified=True,new_model_calls=0)))
'''
with Remote() as c:
 print(c.python(script,timeout=60).decode())
 for name in ['RAW_INDEX_v1.json','INPUT_FREEZE_ENVIRONMENT_v1.json']:c.get(P+'/'+name,E/'baseline'/name)

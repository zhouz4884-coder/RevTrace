"""Post-completion bounded audit evidence, large raw traces remain on8TB."""
from pathlib import Path
import gzip,hashlib,json,os,tarfile,time
import sys
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/ces_20261023';D=O/'bounded_evidence_v1';assert not D.exists()
assert json.loads((O/'POST_SUMMARY.json').read_text())['status']=='ALL_FORMAL_CPU_AUDITS_AND_STATISTICS_COMPLETE'
D.mkdir();files=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def copy(p,rel):
 import shutil
 q=D/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def tree(root,rel):
 if not root.exists():return
 for p in sorted(root.rglob('*')):
  if p.is_file() and not p.name.endswith('.lock'):copy(p,rel+'/'+p.relative_to(root).as_posix())
for name in ['FORMAL_RELEASE.json','FORMAL_FREEZE.json','FORMAL_PID.json','FORMAL_EXECUTION_SUMMARY.json','POST_SUMMARY.json','CPU_LINUX_v1.log','CPU_LINUX_v2.log','CPU_LINUX_v3.log','CPU_LINUX_v4.log']:
 copy(O/name,'provenance/'+name)
for name in ['FORMAL_RESULTS_v1','formal_v1_independent_audit_final','formal_v1_processor_replay_v1','consumer_commit_addendum_v1','formal_diagnosis_v1','CPU_SIGKILL_v4','ROW_WAL_CPU_v4']:
 tree(O/name,'evidence/'+name)
for version in range(1,5):
 for rootname in [f'pilot_v{version}',f'pilot_v{version}_independent_audit_final' if version>=3 else f'pilot_v{version}_independent_audit_v{2 if version==1 else 3}']:
  root=O/rootname
  if rootname.startswith('pilot_') and '_independent_' in rootname:tree(root,'pilots/'+rootname)
  elif root.exists():
   for p in sorted(root.iterdir()):
    if p.is_file() and p.suffix in ['.json','.log','.txt']:copy(p,'pilots/'+rootname+'/'+p.name)
for root in sorted(O.glob('calibration_v*')):tree(root,'calibration/'+root.name)
# Complete Canonical-transition witnesses, not all large raw model/IPC traces.
for C in sorted((O/'formal_v1').iterdir()):
 if not C.is_dir() or not (C/'result.json').exists():continue
 out=D/'canonical_witnesses'/(C.name+'.jsonl.gz');out.parent.mkdir(exist_ok=True)
 records=[json.loads(l) for l in (C/'worker_records.jsonl').read_text().splitlines()]
 rawsha=sha(C/'worker_records.jsonl')
 events=[json.loads(l) for l in (C/'events.jsonl').read_text().splitlines()]
 commits={e['job_id']:e for e in events if e['kind']=='commit'}
 with gzip.open(out,'wt',encoding='utf-8') as f:
  for x in records:
   j,r=x['job'],x['result']
   if j['role']!='authority':continue
   witness={'job':j,'selected':{k:r.get(k) for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit','model_input_audit','execution_context_audit','text_binding','_row_receipt','ces_operation']},
      'verification':r.get('online_verification'),'actual_commit_event':commits.get(j['job_id']),
      'source_raw_sha256':rawsha,'scope':'derived compact full Canonical evidence, not a byte copy of full row/IPC raw'}
   f.write(json.dumps(witness,allow_nan=False)+'\n')
 wal=Path(json.loads((C/'provenance.json').read_text())['durable_journal_path'])
 target=D/'journals'/(C.name+'.wal.gz');target.parent.mkdir(exist_ok=True)
 with gzip.open(target,'wb') as z:z.write(wal.read_bytes())
 for name in ['config.json','provenance.json','sessions.json','initial_states.json','result.json','workers.json']:
  p=C/name;out=D/'cell_metadata'/(C.name+'-'+name+'.gz');out.parent.mkdir(exist_ok=True)
  with gzip.open(out,'wb') as z:z.write(p.read_bytes())
for p in sorted(D.rglob('*')):
 if p.is_file():files.append({'path':p.relative_to(D).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
(D/'MANIFEST.json').write_text(json.dumps({'status':'BOUNDED_AUDITED_FORMAL_AND_PILOT_EVIDENCE','formal_cells':180,'files':files,'raw_traces_retained_on_8TB':True},indent=2)+'\n')
A=O/'bounded_evidence_v1.tar.gz'
with tarfile.open(A,'w:gz') as tf:
 for p in sorted(D.rglob('*')):
  if p.is_file():tf.add(p,arcname=p.relative_to(D).as_posix(),recursive=False)
(O/'BOUNDED_ARCHIVE_v1.json').write_text(json.dumps({'path':str(A),'bytes':A.stat().st_size,'sha256':sha(A),'files':len(files)+1},indent=2)+'\n')
print(json.dumps({'bytes':A.stat().st_size,'files':len(files)+1,'sha256':sha(A)}))

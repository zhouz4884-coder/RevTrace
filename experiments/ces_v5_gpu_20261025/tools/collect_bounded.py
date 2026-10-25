"""Post-run CPU collection; raw model inputs and large logs stay on8TB."""
from pathlib import Path
import gzip,hashlib,json,shutil,tarfile,time

B=Path(__import__('sys').argv[1]);O=B/'results/revtrace/ces_v5_20261025';P=B/'projects/revtrace_ces_v5_20261025'
D=O/'bounded_evidence_v1';assert not D.exists();D.mkdir()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def copy(p,rel):
 q=D/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def zipped(p,rel):
 q=D/rel;q.parent.mkdir(parents=True,exist_ok=True)
 with p.open('rb') as src,gzip.open(q,'wb') as out:shutil.copyfileobj(src,out)
summary=read(O/'SUMMARY.json');assert summary['status']=='COMPLETE_BOUNDED_V5_GPU_PILOT_AND_AUDIT'
assert read(O/'pilot_v1_audit/SUMMARY.json')['cells']==48
for n in ['FREEZE.json','ENVIRONMENT.json','GPU_STARTED.json','CONTROLLER_PID.json','PROGRESS.json','SUMMARY.json','OPERATOR_ROW_TIMING.json','LINUX_CPU_PREFLIGHT.log']:
 copy(O/n,n)
for folder in ['operation_probe_v1','oracle_v1_audit','pilot_v1_audit','pilot_v1_audit_corrected','pilot_v1_summary','diagnosis_v1','pilot_v1_processor_replay_v1']:
 for p in sorted((O/folder).rglob('*')):
  if p.is_file():copy(p,folder+'/'+p.relative_to(O/folder).as_posix())
for n in ['POST_CPU_SUMMARY.json','AUDIT_METADATA_CORRECTION.json','POST_CPU_STARTED.json']:
 copy(O/n,n)
for stage in ['oracle_v1','pilot_v1']:
 copy(O/(stage+'_EXPECTED.json'),stage+'_EXPECTED.json')
 for C in sorted((O/stage).iterdir()):
  if not C.is_dir() or not (C/'result.json').exists():continue
  for n in ['config.json','provenance.json','initial_states.json','sessions.json','workers.json','result.json','OWNED_WORKER_HANDLES.json','power_samples.json']:
   if (C/n).exists():zipped(C/n,'cell_metadata/'+stage+'-'+C.name+'-'+n+'.gz')
  for n in ['events.jsonl','consumer.jsonl','worker_batch_accounting.jsonl']:
   zipped(C/n,'traces/'+stage+'-'+C.name+'-'+n+'.gz')
  out=D/'canonical_witnesses'/(stage+'-'+C.name+'.jsonl.gz');out.parent.mkdir(exist_ok=True)
  worker_records_sha256=sha(C/'worker_records.jsonl')
  with (C/'worker_records.jsonl').open() as f,gzip.open(out,'wt') as dst:
   for line in f:
    x=json.loads(line);j,r=x['job'],x['result']
    if j['role']!='authority':continue
    selected={k:r[k] for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit','execution_context_audit','text_binding','_row_receipt','ces_operation'] if k in r}
    selected['model_input_audit_sha256']=hashlib.sha256(json.dumps(r['model_input_audit'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    dst.write(json.dumps({'job':j,'selected':selected,'verification':r.get('online_verification'),
      'raw_worker_records_sha256':worker_records_sha256,'scope':'actual canonical selections; full model-input arrays retained in indexed8TB raw file'})+'\n')
  for suffix in ['.log','.COMMAND.json','.CPU_IO.txt']:
   p=O/stage/(C.name+suffix)
   if p.exists():copy(p,'cell_logs/'+stage+'-'+p.name)
 for wal in (O/stage/'journals').glob('*.wal'):zipped(wal,'journals/'+stage+'-'+wal.name+'.gz')

handles=[]
for p in O.glob('*/*/OWNED_WORKER_HANDLES.json'):
 for h in read(p):
  proc=Path('/proc')/str(h['pid']);same=False
  if proc.exists():
   try:same=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==h['linux_start_ticks']
   except (FileNotFoundError,ProcessLookupError):pass
  handles.append({'cell':p.parent.name,'pid':h['pid'],'same_original_process_alive':same})
assert not any(h['same_original_process_alive'] for h in handles)
controller=read(O/'CONTROLLER_PID.json')['pid'];cp=Path('/proc')/str(controller)
controller_same=cp.exists() and str(P/'run_stage.py').encode() in cp.joinpath('cmdline').read_bytes()
assert not controller_same
import subprocess
current_gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)
resource={'controller_original_command_alive':controller_same,'worker_handles_checked':len(handles),'handles':handles,
 'current_GPU_processes':current_gpu,'all_this_task_workers_released':True,'foreign_processes_not_touched':True}
(O/'RESOURCE_RELEASE.json').write_text(json.dumps(resource,indent=2)+'\n');copy(O/'RESOURCE_RELEASE.json','RESOURCE_RELEASE.json')
index=[]
for p in sorted(O.rglob('*')):
 if p.is_file() and D not in p.parents and p.name not in ['RAW_INDEX.json','BOUNDED_INDEX.json','bounded_evidence_v1.tar.gz','POST_CONTROLLER.log']:
  index.append({'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
(O/'RAW_INDEX.json').write_text(json.dumps({'files':index,'scope':'actual raw result files, excluding derived collection and self-index'},indent=2)+'\n')
copy(O/'RAW_INDEX.json','RAW_INDEX.json')
manifest=[{'path':p.relative_to(D).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(D.rglob('*')) if p.is_file()]
(D/'MANIFEST.json').write_text(json.dumps({'experiment_id':'REVTRACE-CES-V5-GPU-20261025','files':manifest,'raw_index_sha256':sha(O/'RAW_INDEX.json')},indent=2)+'\n')
archive=O/'bounded_evidence_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tf:
 for p in sorted(D.rglob('*')):
  if p.is_file():tf.add(p,arcname=p.relative_to(D).as_posix(),recursive=False)
record={'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'files':len(manifest)+1,
 'raw_files':len(index),'raw_bytes':sum(x['bytes'] for x in index),'raw_index_sha256':sha(O/'RAW_INDEX.json')}
assert record['bytes']<95_000_000
(O/'BOUNDED_INDEX.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))

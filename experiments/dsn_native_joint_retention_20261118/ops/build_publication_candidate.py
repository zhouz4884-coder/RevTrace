"""Hash a bounded local publication candidate; never copy/stage/push Git files."""
from pathlib import Path
import argparse,hashlib,json,re

SOURCE_MAP=(('RUNTIME_SOURCE_V1','runtime_source',67),('CAMPAIGN_SOURCE_V1','campaign_source',22),('AUDIT_SOURCE_V1','audit_source',20),('READINESS_SOURCE','baseline/readiness_source',3),('ANALYSIS_SOURCE_V1','analysis_source',3),('ANALYSIS_SOURCE_V2','analysis_source_v2',3),('PRODUCTION_SUPPORT_SOURCE','baseline/production_support_source',18))
CELL_NAMES={'CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','ORIGIN.json','GENESIS.json','SERVICE_END.json','SUMMARY.json','GATE.json','EXTERNAL_FACTORIAL_AUDIT.json','INDEPENDENT_VIEW_AUDIT.json','WORKER_TIMER_LEDGER.json','JOB_ACCOUNTING.json','SAMPLED_ENERGY_OWNERSHIP.json'}
VIEW_NAMES={'SUMMARY.json','GATE.json','CANONICAL_SUPPORT_EVENTS.json','OBSERVED_LOSS_WINDOWS.json'}
ROOT_NAMES={'.gitattributes','EXECUTION_CHECKPOINT.zh.md','MANUSCRIPT_READONLY_SNAPSHOT.json','WORKING_STATE.json','COLLECTION_REQUESTS.json','RAW_HASH_INDEX.json','FINAL_REPORT.zh.md','FINAL_SUMMARY.json','FINAL_PER_SOURCE.csv','RESOURCE_CLOSURE.json','COLLECTION_INDEX.json','COLLECTION_INDEX_V2.json','MANUSCRIPT_READONLY_FINAL_CHECK.json','README.md','SCIENTIFIC_DECISION.json'}
DENIED_SUFFIX={'.jsonl','.wal','.wav','.safetensors','.pt','.pth','.bin','.npy','.npz','.ckpt','.tar','.gz','.zip','.pdf','.png','.jpg','.parquet'}
SAFE_OPS=('collect_closed.py','launch_service.py','poll.py','prepare_reference.py','prepare_service.py','relaunch_reference_v2.py','relaunch_reference_v3.py','stage_and_cpu.py','stage_final_sources.py','prepare_collection_requests.py','build_publication_candidate.py')

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as stream:
  for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
 return h.hexdigest()

def manuscript_check(root):
 snapshot=root/'MANUSCRIPT_READONLY_SNAPSHOT.json';old=json.loads(snapshot.read_bytes());paper=root.parents[1]/'Paper_DSN/revisions/20261112_dsn2027_release_v18';changes=[]
 for row in old['files']:
  p=paper/row['path']
  if not p.is_file():changes.append(dict(path=row['path'],status='missing'));continue
  if p.stat().st_size!=row['bytes']or sha(p)!=row['sha256']:changes.append(dict(path=row['path'],status='bytes_changed'))
 expected={row['path']for row in old['files']}
 actual={p.relative_to(paper).as_posix()for p in paper.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
 for name in sorted(actual-expected):changes.append(dict(path=name,status='unexpected_new_file'))
 return dict(status='PASS_ALL230_READONLY_MANUSCRIPT_FILES_BYTE_UNCHANGED'if len(old['files'])==230 and not changes else'READONLY_MANUSCRIPT_SNAPSHOT_DIFFERENCE_REQUIRES_REVIEW',snapshot_sha256=sha(snapshot),snapshot_files=len(old['files']),changed_files=changes,manuscript_edited_by_this_helper=False)

def build(root,require_complete=False):
 root=Path(root).resolve();chosen=set();pending=[]
 def add(p):
  p=Path(p)
  if not p.is_file()or p.is_symlink()or not p.resolve().is_relative_to(root)or'.git'in p.relative_to(root).parts:raise ValueError('Unsafe publication path: '+str(p))
  if p.suffix.lower()in DENIED_SUFFIX:raise ValueError('Bulk/model/paper payload forbidden: '+str(p))
  chosen.add(p)
 for name in ROOT_NAMES:
  p=root/name
  if p.is_file():add(p)
 for name in SAFE_OPS:
  p=root/'ops'/name
  if p.is_file():add(p)
 for folder in('plans','packages','launch_ops','baseline','review','frozen_configs','raw_hash_indices','preserved_premodel_failures'):
  d=root/folder
  if not d.exists():continue
  for p in d.rglob('*'):
   if not p.is_file()or'.git'in p.relative_to(d).parts or'__pycache__'in p.parts:continue
   if p.suffix.lower()in DENIED_SUFFIX:raise ValueError('Unexpected bulk payload in metadata folder: '+str(p))
   if folder=='review'and p.name=='continuity_final_interpretation.py':add(p);continue
   if p.suffix.lower()not in {'.json','.md','.csv','.log','.bundle','.txt'}and p.name!='.gitattributes':continue
   add(p)
 for tag,folder,count in SOURCE_MAP:
  m=root/'packages'/(tag+'.json');bundle=root/'packages'/(tag+'.bundle')
  data=json.loads(m.read_bytes())
  if len(data['files'])!=count or not bundle.is_file():raise ValueError('Complete source package missing: '+tag)
  add(m);add(bundle)
  for row in data['files']:
   p=root/folder/row['path']
   if p.stat().st_size!=row['bytes']or sha(p)!=row['sha256']:raise ValueError('Frozen source member changed')
   add(p)
 complete_cells=0
 for phase in('REFERENCE8_V3','PILOT20_V1','CONFIRM60_V1'):
  d=root/'gpu_results'/phase
  if not d.exists():pending.append(phase);continue
  for p in d.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(d);parts=rel.parts
   if len(parts)==1 and p.name in CELL_NAMES|{'REFERENCE_RECEIPT.json','REFERENCE_DETAILS.json','REFERENCE_ENERGY.json','MODEL_READY.json','PARTIAL_RESULTS.json','PROGRESS.json','ROOT_RESOURCE_CLOSURE.json','COLLECTION_RESOURCE_CLOSURE.json'}:add(p)
   elif len(parts)==3 and parts[0]=='cells'and p.name in CELL_NAMES:add(p)
   elif len(parts)==4 and parts[0]=='cells'and parts[2]=='view_audit'and p.name in VIEW_NAMES:add(p)
   elif len(parts)==2 and parts[0]=='records'and p.suffix=='.json':add(p)
  if phase!='REFERENCE8_V3':
   plan=json.loads((root/'plans'/(phase+'_PLAN.json')).read_bytes())
   for name in('SUMMARY.json','GATE.json'):
    p=d/name
    if not p.is_file():pending.append(phase+'/'+name);continue
    value=json.loads(p.read_bytes())
    if not value.get('status','').startswith('COMPLETE'):pending.append(phase+'/'+name+':not_complete')
   for cell in plan['cells']:
    c=d/'cells'/cell['cell_id'];required=[c/name for name in CELL_NAMES]+[c/'view_audit'/name for name in VIEW_NAMES]
    if all(p.is_file()for p in required)and json.loads((c/'GATE.json').read_bytes()).get('status','').startswith('PASS'):complete_cells+=1
    else:pending.append(cell['cell_id'])
 manuscript=manuscript_check(root)
 if require_complete:
  if complete_cells!=80 or pending:raise ValueError('Cannot publish a complete80 claim from incomplete local collection')
  if not manuscript['status'].startswith('PASS'):raise ValueError('Paper readonly identity changed')
  ref=root/'gpu_results/REFERENCE8_V3';receipt=json.loads((ref/'REFERENCE_RECEIPT.json').read_bytes());gate=json.loads((ref/'GATE.json').read_bytes())
  if not receipt['status'].startswith('PASS')or gate['status']!=receipt['status']or gate.get('all_original_full_state_C_IDs_equal')is not True:raise ValueError('Complete reference gate missing')
  for key,name in(('reference_details','REFERENCE_DETAILS.json'),('reference_gate','GATE.json'),('genesis','GENESIS.json')):
   if sha(ref/name)!=receipt[key]['sha256']:raise ValueError('Measured reference binding changed: '+name)
  for phase in('PILOT20_V1','CONFIRM60_V1'):
   handle=json.loads((root/'launch_ops'/phase/'HANDLE.json').read_bytes())
   closures=[root/'launch_ops'/phase/n for n in('COLLECTION_RESOURCE_CLOSURE.json','RESOURCE_CLOSURE.json')]
   valid=[]
   for p in closures:
    if p.is_file():
     c=json.loads(p.read_bytes())
     if c.get('status','').startswith('PASS')and c.get('pid')==handle['pid']and c.get('start_ticks')==handle['start_ticks']:valid.append(c)
   if not valid:raise ValueError('Generation-bound process closure missing: '+phase)
   indices=[root/'raw_hash_indices'/(phase+suffix)for suffix in('.collection_v2.json','.json')]
   index_path=next((p for p in indices if p.is_file()),None)
   if index_path is None:raise ValueError('Raw provenance hash index missing: '+phase)
   rows=json.loads(index_path.read_bytes())['files'];plan=json.loads((root/'plans'/(phase+'_PLAN.json')).read_bytes())
   if {r['cell_id']for r in rows}!={c['cell_id']for c in plan['cells']}:raise ValueError('Raw index source extent differs: '+phase)
   for cell in plan['cells']:
    own={r['path']for r in rows if r['cell_id']==cell['cell_id']};expected={cell['out']+'/'+n for n in('facts.wal','consumer.jsonl','publications.jsonl')}
    expected.update((cell['log'],cell['external_power']))
    if not expected<=own:raise ValueError('Core raw provenance fields missing: '+cell['cell_id'])
  for phase in('REFERENCE8_V1','REFERENCE8_V2'):
   if not(root/'preserved_premodel_failures'/phase/'process.log').is_file():raise ValueError('Premodel failure log missing: '+phase)
 rows=[]
 for p in sorted(chosen):
  rel=p.relative_to(root).as_posix();size=p.stat().st_size
  if size>8_000_000:raise ValueError('Needs explicit bounded-payload review: '+rel)
  if p.suffix!='.bundle':
   text=p.read_bytes().decode('utf-8-sig')
   for pattern in(r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{30,}',r'hf_[A-Za-z0-9]{25,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----'):
    if re.search(pattern,text):raise ValueError('Possible credential pattern: '+rel)
  rows.append(dict(path=rel,bytes=size,sha256=sha(p)))
 total=sum(r['bytes']for r in rows)
 if total>128_000_000:raise ValueError('Publication candidate exceeds hard byte bound')
 return dict(record_type='LOCAL_PUBLICATION_CANDIDATE_NOT_A_PUSH',file_count=len(rows),bytes=total,files=rows,collected_complete_serving_cells=complete_cells,planned_serving_cells=80,pending=pending,manuscript_readonly=manuscript,status='READY_FOR_ROOT_FINAL_REVIEW'if require_complete else'PARTIAL_LOCAL_INVENTORY_NO_COMPLETENESS_CLAIM',soft_budget_exceeded=total>96_000_000,Git_written_or_staged=False,source_execution_commits_are_distinct_from_archive_commit=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);p.add_argument('--require-complete',action='store_true');a=p.parse_args()
 result=build(a.root,a.require_complete);out=a.out or a.root/'PUBLICATION_CANDIDATE.json';out.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in result.items()if k not in('files','pending')}))

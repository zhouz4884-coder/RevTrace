"""Collect all twelve accepted midpoint results, including negative witnesses."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
H=Path(__file__).resolve().parent;B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/physical_retirement_20261028';A=O+'/dsn_midpoint_analysis_v1'
files=['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','GATE.json','SUMMARY.json','RUNS.json',
    'TIMELY_LOSS_WINDOWS.json','ALL_ROLLBACK_EVENTS.json','SECONDARY_INPUT_HASHES.json','STRONG_WITNESS_DECISION.json',
    'core/CONFIG.json','core/ENVIRONMENT.json','core/RUN_RECORD.json','core/GATE.json','core/SUMMARY.json']
tables={'aggregate':['SUMMARY','ANALYSIS_RECORD','COVERAGE','BLOCK_COVERAGE','RUNS','SOURCE_METRICS','FACTORIAL_EFFECTS','SOURCE_FACTORIAL_EFFECTS','PAIRED_EFFECTS','SOURCE_PAIRED_EFFECTS','FRONTIER_PAIRED_EFFECTS','CANONICAL_HISTORY_GROUPS','SOURCE_REGISTRY'],
 'usefulness':['SUMMARY','ANALYSIS_RECORD','COVERAGE','RUNS','FACTORIAL_EFFECTS','SOURCE_FACTORIAL_EFFECTS'],
 'opportunities':['ANALYSIS_RECORD','COVERAGE','STRATIFIED_RATES','SOURCE_OPPORTUNITIES','UPDATES','SAME_CANONICAL_HISTORY_GROUPS'],
 'critical_path':['SUMMARY','RUNS','FRONTIER_PATHS','ANALYSIS_RECORD']}
files.extend('core/'+component+'/'+name+'.json' for component,names in tables.items() for name in names)
targets=[A+'/'+n for n in files]+[O+'/dsn_midpoint_controller_v1/'+n for n in ['GATE.json','SUMMARY.json','RUN_RECORD.json','ENVIRONMENT.json','PROGRESS.json']]
c=ssh_client()
try:
 script="import hashlib,json\nfrom pathlib import Path\nA=Path("+repr(A)+")\nassert json.loads((A/'GATE.json').read_text())['gate']=='PASS_ALL_12_MIDPOINT_RECOUNTS'\npaths="+repr(targets)+"\nprint(json.dumps([dict(path=p,bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for p in paths]))\n"
 i,o,e=c.exec_command('python3 -B -',timeout=45);i.write(script);i.flush();i.channel.shutdown_write();raw=o.read();err=e.read();assert o.channel.recv_exit_status()==0,err.decode();manifest=json.loads(raw)
 assert max(r['bytes'] for r in manifest)<30_000_000 and sum(r['bytes'] for r in manifest)<65_000_000
 D=H/'RESULTS_v1';D.mkdir(exist_ok=False);s=c.open_sftp()
 try:
  for r in manifest:
   rel=r['path'][len(A)+1:] if r['path'].startswith(A+'/') else 'controller/'+r['path'].rsplit('/',1)[-1]
   p=D/rel;p.parent.mkdir(parents=True,exist_ok=True);s.get(r['path'],str(p))
   assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 finally:s.close()
 with (D/'DOWNLOAD_VERIFICATION.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2);f.write('\n')
 print(json.dumps(dict(output=str(D),files=len(manifest),bytes=sum(r['bytes'] for r in manifest),all_SHA256_matched=True,strong_witness=json.loads((D/'STRONG_WITNESS_DECISION.json').read_text()))))
finally:c.close()

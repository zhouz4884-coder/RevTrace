"""After all GPU/CPU checks: immutable raw index + bounded lossless archive."""
from pathlib import Path
import gzip,hashlib,json,shutil,subprocess,sys,tarfile
B=Path(sys.argv[1]);P=B/'projects/revtrace_elastic_20261022';O=B/'results/revtrace/elastic_20261022'
assert json.loads((O/'POSTFLIGHT.json').read_text())['status']=='PASS_COMPLETE_ELASTIC_FORMAL_AND_INDEPENDENT_ANALYSIS'
assert len(json.loads((O/'FORMAL_SUMMARY.json').read_text())['completed'])==24
assert json.loads((O/'formal_audit/AUDIT_REPORT.json').read_text())['cells']==24
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
meta=O/'metadata';meta.mkdir(exist_ok=True)
for tag,p in [('source16',B/'datasets/revtrace/phaseD_20261021/manifest.json'),('source32',B/'datasets/revtrace/elastic_20261022_32/manifest.json')]:shutil.copy2(p,meta/(tag+'_manifest.json'))
files=[]
for p in sorted(O.rglob('*')):
 if not p.is_file() or p.name in ['RAW_EVIDENCE_INDEX.json','BOUNDED_EVIDENCE.tar.gz','EVIDENCE_FREEZE.json'] or p.name.startswith('POSTFLIGHT_CONTROLLER'):continue
 files.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
sources=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(P.glob('*')) if p.is_file()]
(O/'RAW_EVIDENCE_INDEX.json').write_text(json.dumps({'files':files,'actual_root_scripts':sources,'all_raw_on_8TB':True,'all42_run_configs_and_hashes':True,'large_neural_records_not_publicly_copied':True},indent=2)+'\n')
for p in list(O.rglob('*.csv')):
 if p.stat().st_size>1_500_000:
  with gzip.open(p.with_suffix('.csv.gz'),'wb') as f:f.write(p.read_bytes())
paths=[]
for p in sorted(O.rglob('*')):
 if not p.is_file() or p.name in ['events.jsonl','worker_records.jsonl','consumer.jsonl','power_samples.json','BOUNDED_EVIDENCE.tar.gz'] or p.name.startswith('POSTFLIGHT_CONTROLLER'):continue
 if p.suffix=='.wal' or p.stat().st_size>2_000_000:continue
 paths.append(p)
with tarfile.open(O/'BOUNDED_EVIDENCE.tar.gz','w:gz') as t:
 for p in paths:t.add(p,arcname=p.relative_to(O).as_posix())
result={'status':'FROZEN_42_GPU_CELLS_AND_CPU_ANALYSIS','raw_files':len(files),'bounded_files':len(paths),'archive_bytes':(O/'BOUNDED_EVIDENCE.tar.gz').stat().st_size,'archive_sha256':sha(O/'BOUNDED_EVIDENCE.tar.gz'),'raw_index_sha256':sha(O/'RAW_EVIDENCE_INDEX.json'),'root_sources':len(sources),'GPU_at_check':subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True),'no_more_GPU_work':True}
(O/'EVIDENCE_FREEZE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

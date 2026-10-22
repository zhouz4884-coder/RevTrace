"""Hash closed scientific evidence, not open monitoring/self-referential files."""
from pathlib import Path
import hashlib,json,sys,time
B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'closed_raw_index_v1'
assert not D.exists()
required=['FORMAL_ROW_SUMMARY_v1.json','formal_row_v1_processor_replay_v1/SUMMARY.json',
 'validation_row_v1_processor_replay_v1/SUMMARY.json','row_timing_v1/SUMMARY.json','ROW_FORMAL_RESULTS_v1/GONOGO.json']
for name in required:assert (O/name).exists(),name
D.mkdir();rows=[];excluded=[]
for p in sorted(O.rglob('*')):
    if not p.is_file():continue
    assert not p.is_symlink() and p.resolve().is_relative_to(O.resolve())
    rel=p.relative_to(O).as_posix()
    if rel.startswith(('tmp_','closed_raw_index_v1/','POST_ROW_CPU_')):
        excluded.append({'path':rel,'reason':'ephemeral CPU fixture or open postanalysis monitor/self-index'});continue
    before=p.stat()
    with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    after=p.stat();assert before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns,'changed during hash: '+rel
    rows.append({'path':rel,'bytes':before.st_size,'sha256':sha})
data={'status':'CLOSED_SCIENTIFIC_RAW_INDEX_WITH_EXPLICIT_EXCLUSIONS','files':rows,'excluded':excluded,
 'remote_root':str(O),'all_measurements_and_negative_results_retained':True,'new_model_calls':0,
 'scope':'scientific observations,configurations,WALs,outputs and closed analysis;not a hash of live monitor state',
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'time_unix':time.time()}
(D/'RAW_EVIDENCE_INDEX.json').write_text(json.dumps(data,indent=2)+'\n')
summary={k:v for k,v in data.items() if k not in ['files','excluded']};summary.update(files=len(rows),bytes=sum(r['bytes'] for r in rows),
 exclusions=len(excluded),index_sha256=hashlib.sha256((D/'RAW_EVIDENCE_INDEX.json').read_bytes()).hexdigest())
(D/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))

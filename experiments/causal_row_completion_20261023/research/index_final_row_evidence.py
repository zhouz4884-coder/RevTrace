"""Final closed measurement union, after the conditional cost route closes."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023';D=O/'FINAL_CLOSED_EVIDENCE_v1'
assert not D.exists();D.mkdir()
def read(p):return json.loads(p.read_text())
required=['FORMAL_ROW_SUMMARY_v1.json','POST_ROW_CPU_SUMMARY_v1.json','EXTRA_ROW_CPU_SUMMARY_v1.json',
 'F2_EXPOSURE_CPU_SUMMARY_v1.json','MATRIX_CONSISTENCY_CPU_SUMMARY_v1.json','rescue_cost_independent_v1/SUMMARY.json']
for name in required:assert (O/name).exists(),name
assert read(O/'FORMAL_ROW_SUMMARY_v1.json')['status']=='COMPLETE_ALL150_INDEPENDENT_AUDITS_PASS'
assert read(O/'rescue_cost_independent_v1/SUMMARY.json')['decision']=='NO_GO_INTEGRATED_RESCUE_NO_STRONG_TARGET_REGIME_OPPORTUNITY'
handles=['FORMAL_ROW_PID_v1.json','POST_ROW_CPU_PID_v1.json','EXTRA_ROW_CPU_PID_v1.json','F2_EXPOSURE_CPU_PID_v1.json','MATRIX_CONSISTENCY_CPU_PID_v1.json','RESCUE_COST_PID_v1.json']
closed=[]
for name in handles:
    h=read(O/name);p=Path('/proc')/str(h['pid'])/'cmdline'
    command=p.read_bytes() if p.exists() else b''
    assert h['command'].encode() not in command,'own controller still running: '+name
    closed.append({'handle':name,'original_pid':h['pid'],'original_command_not_running':True})
files=[];excluded=[]
for p in sorted(O.rglob('*')):
    if not p.is_file():continue
    assert not p.is_symlink() and p.resolve().is_relative_to(O.resolve())
    rel=p.relative_to(O).as_posix()
    if rel.startswith(('tmp_','FINAL_CLOSED_EVIDENCE_v1/')):
        excluded.append({'path':rel,'reason':'ephemeral CPU fixture or self-referential final-index files'});continue
    before=p.stat()
    with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    after=p.stat();assert before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
    files.append({'path':rel,'bytes':before.st_size,'sha256':sha})
index={'status':'PASS_FINAL_CLOSED_UNION_RAW_HASH_INDEX','files':files,'excluded':excluded,
 'remote_root':str(O),'includes_all_closed_GPU_CPU_negative_results_and_monitor_logs':True,'new_model_calls':0,
 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'time_unix':time.time()}
(D/'RAW_EVIDENCE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True)
out={'status':'PASS_FINAL_CLOSED_UNION_AND_TASK_RELEASE','files':len(files),'bytes':sum(r['bytes'] for r in files),
 'exclusions':len(excluded),'index_sha256':hashlib.sha256((D/'RAW_EVIDENCE_INDEX.json').read_bytes()).hexdigest(),
 'own_controllers_closed':closed,'current_GPU_compute_apps':gpu,'GPU_observed_idle':not gpu.strip(),
 'foreign_tasks_not_terminated_or_modified':True,'no_more_GPU_issuance':True,'no_integrated_Rescue':True}
(D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

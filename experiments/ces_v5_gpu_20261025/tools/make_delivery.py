"""Freeze bounded evidence and final diagnosis, without editing runtime/paper."""
from pathlib import Path
import ast,gzip,hashlib,json,re,shutil,tarfile,time
W=Path(__file__).resolve().parent;D=W/'delivery';assert not D.exists()
R=W/'collected';A=W/'local_review'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
assert read(R/'SUMMARY.json')['online_cells']==48
assert read(R/'POST_CPU_SUMMARY.json')['status']=='PASS_INDEPENDENT_V5_DIAGNOSIS_INPUT_REPLAY_AND_METADATA_CORRECTION'
assert read(A/'SUMMARY.json')['status']=='PASS_SEPARATE_LOCAL_EVENT_AND_DENOMINATOR_RECOMPUTATION'
assert read(R/'RESOURCE_RELEASE.json')['all_this_task_workers_released']
assert '<testsuite ' in (W/'CPU_RECHECK.xml').read_text() and 'failures="0"' in (W/'CPU_RECHECK.xml').read_text()
for name in ['RESEARCH_REPORT.zh.md','CONTRIBUTION_EVIDENCE_MATRIX.md','DECISION.json','README.md']:
    assert (W/name).is_file(),name
assert read(W/'DECISION.json')['experiment_id']=='REVTRACE-CES-V5-GPU-20261025'
D.mkdir();shutil.copytree(R,D/'evidence');shutil.copytree(A,D/'analysis')
names=['RESEARCH_REPORT.zh.md','CONTRIBUTION_EVIDENCE_MATRIX.md','DECISION.json','README.md',
       'PROTOCOL.md','DIAGNOSIS_PLAN.md','CPU_RECHECK.xml','BUNDLE.json','SOURCE_AND_CONTROLLERS_v1.tar.gz',
       'INDEPENDENT_CPU_CAUSE_REVIEW.md','CPU_CAUSE_COUNTEREXAMPLES.json','CPU_CAUSE_COUNTEREXAMPLES_v2.json',
       'CPU_CAUSE_COUNTEREXAMPLES_root_repeat.json','ANALYSIS_REPAIRS.md','ACTUAL_TRACE_SPOT_AUDIT.md',
       'ACTUAL_TRACE_SPOT_AUDIT_FINAL.json']
for name in names:shutil.copyfile(W/name,D/name)
scripts=['run_stage.py','operation_probe.py','audit_v5.py','audit_v5_metadata_fixed.py','summarize_v5.py',
    'diagnose_actual.py','replay_actual_inputs.py','post_cpu.py','collect_bounded.py','post_when_complete.py',
    'local_review.py','audit_selected_rows.py','audit_selected_rows_failed_v1.py','cpu_cause_probe.py',
    'interpret_diagnosis.py','late_commit_audit.py','audit_actual_spot.py','make_delivery.py','publish_gpu.py']
(D/'tools').mkdir()
for name in scripts:
    ast.parse((W/name).read_text(encoding='utf8'));shutil.copyfile(W/name,D/'tools'/name)
(D/'.gitattributes').write_text('* -text\n',encoding='utf8')
bad=re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_[A-Za-z0-9_]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{24,}')
findings=[]
def scan(stream,label):
    tail=b''
    while True:
        part=stream.read(1024*1024)
        if not part:return
        if bad.search(tail+part):findings.append(label);return
        tail=part[-160:]
for p in D.rglob('*'):
    if not p.is_file():continue
    label=p.relative_to(D).as_posix()
    if p.name.endswith('.tar.gz'):
        with tarfile.open(p,'r:gz') as tf:
            for member in tf.getmembers():
                if member.isfile():
                    with tf.extractfile(member) as f:scan(f,label+'!'+member.name)
    elif p.suffix=='.gz':
        with gzip.open(p,'rb') as f:scan(f,label)
    else:
        with p.open('rb') as f:scan(f,label)
assert not findings,findings
files=[{'path':p.relative_to(D).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in sorted(D.rglob('*')) if p.is_file()]
assert max(x['bytes'] for x in files)<100_000_000
manifest={'status':'COMPLETE_AUDITED_BOUNDED_V5_GPU_STAGE','experiment_id':'REVTRACE-CES-V5-GPU-20261025',
    'source_commit':'126dc815962e8f726b0cbdf214a19318b28a3629','online_cells':48,'oracle_cells':2,
    'operator_physical_batches':6,'GPU_queue_closed':True,'larger_formal_matrix':False,
    'reused_sources_not_independent_confirmation':True,'manuscript_edits':False,
    'secret_pattern_scan':'No recognized credential patterns in plain files or decompressed gzip/tar members; not a universal secret detector',
    'total_bytes':sum(x['bytes'] for x in files),'files':files,'time_unix':time.time()}
(D/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
state=read(W/'ACTIVE_STATE.json');state.update(phase='COMPLETE_AUDITED_BOUNDED_V5_GPU_STAGE_GITHUB_PENDING',
    GPU_queue_closed=True,completed_online_cells=48,completed_oracle_cells=2,
    algorithm_decision=read(W/'DECISION.json')['algorithm_upgrade'],
    local_independent_audit='PASS',delivery_manifest_sha256=hashlib.sha256((D/'MANIFEST.json').read_bytes()).hexdigest(),
    remote_raw_index_sha256=read(W/'BOUNDED_INDEX.json')['raw_index_sha256'],manuscript_edits=False)
(W/'ACTIVE_STATE.json').write_text(json.dumps(state,indent=2)+'\n',encoding='utf8')
print(json.dumps({'files':len(files)+1,'bytes':manifest['total_bytes'],
    'manifest_sha256':state['delivery_manifest_sha256'],'algorithm_upgrade':state['algorithm_decision']}))

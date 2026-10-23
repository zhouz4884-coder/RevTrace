"""Freeze the local CPU stage and build an additive, bounded review snapshot."""
from pathlib import Path
import csv,hashlib,json,re,shutil,subprocess,time

W=Path(__file__).resolve().parent
S=W/'runtime'
D=W/'delivery_cpu'
BASE='e0aeae1b418644c378dde331c59b55fc5948b40f'
def git(*args):return subprocess.check_output(['git','-C',str(S),*args])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert read(W/'cpu_validation_v2/SUMMARY.json')['status']=='PASS'
assert not git('status','--porcelain').strip()
commit=git('rev-parse','HEAD').decode().strip()
files=[]
for name in git('ls-files').decode().splitlines():
    raw=(S/name).read_bytes()
    assert raw==git('show','HEAD:'+name),name
    files.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
source={'code_commit':commit,'base_source':BASE,'execution_scope':'CPU tested; zero V5 GPU calls','files':files}
(S/'SOURCE_MANIFEST.json').write_text(json.dumps(source,indent=2)+'\n')
protected=['src/revtrace/live_qwen.py','src/revtrace/dgft.py','src/revtrace/durable_journal.py',
 'src/revtrace/continuity_proof.py','src/revtrace/standard_safe_async.py',
 'src/revtrace/sequence_verifier.py','src/revtrace/online_admission.py',
 'src/revtrace/row_lifecycle.py','src/revtrace/row_stream.py','scripts/online_selection_worker.py']
for name in protected:assert (S/name).read_bytes()==git('show',BASE+':'+name),name
v2=read(W/'calibration_v2/CALIBRATION.json');v3=read(W/'calibration_v3/CALIBRATION.json')
restored=json.loads(json.dumps(v3));restored['schema']=v2['schema']
del restored['v5_risk_model']['owner_delivery_seconds'];del restored['v5_risk_model']['delivery_calibration']
assert restored==v2,'Only the measured common delivery allowance changes v3'
delivery=read(W/'calibration_v3/SUMMARY.json')
assert delivery['anomalies']==0 and delivery['rows']==14670
assert delivery['calibration_sha256']==sha(W/'calibration_v3/CALIBRATION.json')
for k in ['maximum_row_clock_crosscheck_error_s','maximum_install_crosscheck_error_s','maximum_t0_crosscheck_error_s']:assert delivery[k]==0
final={'status':'COMPLETE_CPU_STAGE_GPU_DEFERRED_BY_USER','experiment_id':'REVTRACE-CES-V5-CPU-20261023',
 'source_commit':commit,'initial_prototype_commit':'fdf9243','pre_vectorization_commit':'0cc42df',
 'baseline_public_commit':'01f6e04aa88cf704c129242e6bbdaf42de159525',
 'GPU_calls':0,'runtime_tests':279,'independent_math_tests':56,'random_vector_equivalence_cases':240,
 'pruning_equivalence_cases':160,'protected_source_files_identical':protected,
 'calibration_sha256':sha(W/'calibration_v3/CALIBRATION.json'),
 'historical_authority_batches_audited':3750,'historical_delivery_transitions':14670,
 'system_performance_improvement':'NOT_MEASURED_V5_GPU_DEFERRED',
 'CPU_prototype':'PASS','mathematical_repairs':'PASS','finite_model_oracle':'PASS_CONDITIONAL_MODEL_ONLY',
 'full_online_predecessor_lookahead':'NOT_IMPLEMENTED_SYMBOLIC_CPU_MODEL_ONLY',
 'no_manuscript_edits':True,'time_unix':time.time()}
(W/'FINAL_CPU_AUDIT.json').write_text(json.dumps(final,indent=2)+'\n')
state=read(W/'ACTIVE_STATE.json');state.update(phase=final['status'],CPU_complete=True,source_commit=commit,
 GPU_started=False,GPU_queue_closed=True,GitHub_delivery='PENDING_ADDITIVE_CPU_SNAPSHOT')
(W/'ACTIVE_STATE.json').write_text(json.dumps(state,indent=2)+'\n')
matrix=[
 ['Actual legal-display progress feedback','Executable CPU runtime and inherited safety tests','PASS_CPU','Consumer telemetry chooses work; does not authorize writes'],
 ['Residual joint deadline objective and row CDF','Same-input counterexamples plus 279 runtime and 56 mathematical tests','PASS_CPU','No V5 serving Goodput measured'],
 ['Same-contract homogeneous sub-batch search','Shared action family and complete-cut tests','PASS_CPU','Actual new batch outputs and GPU costs pending'],
 ['Predecessor deadline inheritance','Released-obligation symbolic model and finite exhaustive oracle','PASS_MODEL','Not yet integrated with actual unknown-parent online rollout'],
 ['Efficient statistical planner','Scalar/vector equivalence and local host-cost fixture','PASS_CPU_BENCH','Windows constructed inputs; not GPU speedup'],
 ['Empirical physical cost and delivery model','2000 development batches, 3750 audited batches, 14670 development delivery rows','CALIBRATED_WITH_LIMITATIONS','Verification P90 coverage on old validation is 86.45%; compressed-tail approximation'],
 ['New C2 system-performance contribution','Requires actual matched GPU pilot and new independent confirmation','PENDING','No positive or negative V5 GPU result fabricated']]
with (W/'CONTRIBUTION_EVIDENCE_MATRIX.csv').open('w',encoding='utf-8',newline='') as f:
 writer=csv.writer(f);writer.writerow(['claim','evidence','decision','boundary']);writer.writerows(matrix)
assert not D.exists();D.mkdir()
def copy(p,rel):
    q=D/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def tree(p,rel):
    for f in sorted(p.rglob('*')):
        if f.is_file():copy(f,rel+'/'+f.relative_to(p).as_posix())
for r in files:copy(S/r['path'],'runtime/'+r['path'])
copy(S/'SOURCE_MANIFEST.json','runtime/SOURCE_MANIFEST.json')
for p in W.glob('*.md'):copy(p,p.name)
for p in W.glob('*.py'):
    if p.name not in ['remote_ops.py']:copy(p,p.name)
for p in W.glob('*.json'):
    if not p.name.startswith('GITHUB_'):copy(p,p.name)
copy(W/'CONTRIBUTION_EVIDENCE_MATRIX.csv','CONTRIBUTION_EVIDENCE_MATRIX.csv')
for name in ['calibration_v1','calibration_v2','calibration_v3','calibration_v2_predictor_audit','cpu_validation_v1','cpu_validation_v2']:
    tree(W/name,name)
for p in (W.parent/'ces_progress_design_20261023').glob('*.md'):copy(p,'design_basis/'+p.name)
(D/'.gitattributes').write_text('* -text\n')
ref=D/'reference_source/ces_v5_policy_0cc42df.py';ref.parent.mkdir();ref.write_bytes(git('show','0cc42dfa18e291a84b1b89e20fdd04f08fa15c37:src/revtrace/ces_v5_policy.py'))
bundle=W/'CPU_SOURCE_HISTORY.bundle';assert not bundle.exists()
subprocess.check_call(['git','-C',str(S),'bundle','create',str(bundle),'--all'])
copy(bundle,'source_bundles/CPU_SOURCE_HISTORY.bundle')
pattern=re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----')
manifest=[]
for p in sorted(D.rglob('*')):
 if not p.is_file():continue
 raw=p.read_bytes();rel=p.relative_to(D).as_posix()
 assert p.suffix not in ['.pyc','.wav','.flac','.safetensors','.pt','.bin'] and '.git' not in p.parts
 assert len(raw)<20_000_000 and not pattern.search(raw),rel
 manifest.append({'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
meta=dict(final,files=manifest,scope='CPU research snapshot; no newly executed GPU evidence')
(D/'MANIFEST.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'status':final['status'],'source_commit':commit,'files':len(manifest)+1,
 'bytes':sum(r['bytes'] for r in manifest),'manifest_sha256':sha(D/'MANIFEST.json')},indent=2))

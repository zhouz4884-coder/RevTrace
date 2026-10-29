"""CPU-only reuse of frozen fde usefulness plus fixed 96-row quality checks.

Never change original credit, infer unavailable same-F text, truncate a longer
snapshot, or turn retrospective selected-model agreement into certification.
"""
from pathlib import Path
from collections import defaultdict
import argparse,csv,hashlib,importlib.util,json,os,platform,subprocess,sys,traceback

INPUTS={}
BASELINE={}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(value,message):
    if not value:raise ValueError(message)
def read(path,lines=False):
    path=Path(path);raw=path.read_bytes();key=str(path.resolve());identity=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    if key in BASELINE:need(identity==BASELINE[key],'prior actual-input bytes changed: '+key)
    INPUTS[key]=identity
    return [json.loads(line) for line in raw.decode('utf8').splitlines() if line] if lines else json.loads(raw)
def put(path,value):
    with Path(path).open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def verify_checkout(root,manifest):
    root=Path(root);manifest=read(manifest)
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
    need(Path(git('rev-parse','--show-toplevel')).resolve()==root.resolve(),'source checkout root changed')
    need(git('rev-parse','HEAD')==manifest['code_commit'],'source commit changed')
    need(not git('status','--porcelain','--untracked-files=all'),'source checkout dirty')
    need(set(git('ls-files').splitlines())=={r['path'] for r in manifest['files']},'source manifest is not complete')
    for row in manifest['files']:
        path=root/row['path'];need(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],'source bytes changed')
    return manifest['code_commit']
def load_usefulness(source):
    spec=importlib.util.spec_from_file_location('frozen_usefulness',Path(source)/'canonical_usefulness_v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def partition_first_credit(rows):
    """Preserve original first credit; unknown remains a separate category."""
    answer=dict(offered_frontiers=len(rows),offered_audio_seconds=sum(r['audio_seconds'] for r in rows),
                original_dual_credited_audio_seconds=sum(r['audio_seconds'] for r in rows if r['dual_timely']))
    for kind in ('raw','normalized'):
        buckets=dict(first_certified=0.,first_ahead_equal=0.,first_ahead_different=0.,unknown=0.)
        counts={k:0 for k in buckets}
        for row in rows:
            if not row['dual_timely']:continue
            if row['same_F_status']=='NOT_AHEAD':category='first_certified'
            elif row['ahead'] and row[kind+'_equal'] is True:category='first_ahead_equal'
            elif row['ahead'] and row[kind+'_equal'] is False:category='first_ahead_different'
            else:category='unknown'
            if row['raw_equal'] is True:need(row['normalized_equal'] is True,'raw identity cannot normalize differently')
            buckets[category]+=row['audio_seconds'];counts[category]+=1
        need(abs(sum(buckets.values())-answer['original_dual_credited_audio_seconds'])<1e-7,'support partition changed original credit')
        answer[kind]=dict(audio_seconds=buckets,frontiers=counts,
                          first_certified_or_same_F_agreeing_audio_seconds=buckets['first_certified']+buckets['first_ahead_equal'])
    return answer

def first_actual_view(consumers,sid,target):
    return next((r for r in consumers if r['session_id']==sid and r['valid_visible_frontier']>=target),None)

def worker_fault_identity(job,result):
    context=result.get('execution_context_audit');model=result.get('model_input_audit')
    need(isinstance(context,dict) and isinstance(model,dict),'actual worker input audit missing')
    need({'fault_override','executed_prompt_tokens','executed_prompt_digest','actual_audio_sha256'}<=set(context),'actual worker prompt/fault fields missing')
    actual=job.get('fault_actual_prompt_tokens',job['prompt_tokens'])
    need(context['executed_prompt_tokens']==actual,'actual executed prompt differs from frozen job')
    need(context['executed_prompt_digest']==hashlib.sha256(','.join(map(str,actual)).encode()).hexdigest(),'actual executed prompt digest differs')
    need(context['fault_override']==('fault_actual_prompt_tokens' in job),'fault flag differs from actual job override')
    need(context['actual_audio_sha256']==job['prefix_audio_sha256']==model['waveform_sha256'],'actual waveform identity differs')
    need(model['declared_prompt_tokens']==job['prompt_tokens'],'declared prompt differs from model input audit')
    return dict(actual_fault_override=context['fault_override'],actual_executed_prompt_equals_declared=actual==job['prompt_tokens'],
                actual_executed_prompt_sha256=context['executed_prompt_digest'],actual_audio_sha256=context['actual_audio_sha256'],
                actual_processed_input_audit_sha256=hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':')).encode()).hexdigest())

def targeted_rows(targets,cells,module):
    by_cell=defaultdict(list)
    for target in targets:by_cell[target['b']].append(target)
    need(len(targets)==96 and len(by_cell)==6,'fixed six-batch 96-row selection changed')
    answer=[]
    for cell_id,items in by_cell.items():
        need(len(items)==16,'one fixed sync batch no longer has 16 rows')
        cell=cells[cell_id];directory=Path(cell['output']);attempt=directory/'attempt0'
        consumers=read(attempt/'consumer.jsonl',True);events=read(attempt/'events.jsonl',True);workers=read(attempt/'worker_records.jsonl',True)
        frontiers=read(directory/'audit/FRONTIERS.json');canonical=module.canonical_snapshots(events,workers,consumers)
        by_job={row['job']['job_id']:row for row in workers};need(len(by_job)==len(workers),'duplicate actual worker job')
        for target in items:
            sid,F,jid=target['session_id'],target['target_F'],target['b_job'];worker=by_job[jid]
            job,result=worker['job'],worker['result'];need(job['role']=='proposal' and job['session_id']==sid and job['audio_end_sample']==F,'fixed target worker identity changed')
            actual=first_actual_view(consumers,sid,F);need(actual is not None,'fixed target has no actual first view')
            owners=[e for e in events if e['kind']=='display' and e['job_id']==jid];need(len(owners)==1,'fixed target publication ambiguous')
            owner=owners[0]
            need(actual['source_kind']=='display' and actual['server_time']==owner['displayed'],'fixed target is not the first actual complete display')
            need(actual['valid_visible_frontier']==F and actual['visible_text']==owner['text']==result['text'],'fixed complete visible text/frontier changed')
            audited=next(r for r in frontiers if r['session_id']==sid and r['frontier']==F)
            need(abs(actual['observed_perf']-audited['first_actual_visible_perf'])<1e-7,'first target visibility differs from original frontier audit')
            need(audited['dual_credit']==target['b_dual_credit'],'original target credit changed')
            need(abs(audited['display_latency']-target['b_display_latency'])<1e-7 and abs(audited['commit_view_latency']-target['b_commit_view_latency'])<1e-7,'original D2/C8 values changed')
            comparison=module.compare_view(actual,canonical)
            answer.append(dict(cell_id=cell_id,arm=cell['arm'],arrival=cell['arrival'],repeat=cell['repeat'],
                               source_id=target['source_id'],session_id=sid,job_id=jid,target_F=F,audio_seconds=audited['audio_seconds'],
                               original_credit_class=target['credit_class'],original_K1_dual_credit=audited['dual_credit'],
                               original_K1_display_latency=audited['display_latency'],original_K1_commit_view_latency=audited['commit_view_latency'],
                               exact_first_full_actual_display=True,**comparison,**worker_fault_identity(job,result)))
    return answer

def secondary_summaries(rows):
    answer=[]
    for cell_id in sorted({r['cell_id'] for r in rows}):
        group=[r for r in rows if r['cell_id']==cell_id];gained=[r for r in group if r['original_credit_class']=='miss_to_hit']
        summary=dict(cell_id=cell_id,arm=group[0]['arm'],repeat=group[0]['repeat'],fixed_rows=len(group),miss_to_hit_rows=len(gained),
                     actual_fault_overrides=sum(r['actual_fault_override'] is True for r in group))
        for label,subset in [('all',group),('miss_to_hit',gained)]:
            for kind in ('raw','normalized'):
                summary[label+'_'+kind+'_equal_rows']=sum(r[kind+'_equal'] is True for r in subset)
                summary[label+'_'+kind+'_different_rows']=sum(r[kind+'_equal'] is False for r in subset)
                summary[label+'_'+kind+'_unknown_rows']=sum(r[kind+'_equal'] is None for r in subset)
                summary[label+'_'+kind+'_equal_audio_seconds']=sum(r['audio_seconds'] for r in subset if r[kind+'_equal'] is True)
        answer.append(summary)
    return answer

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--source-manifest',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    source=Path(__file__).resolve().parent;own_commit=verify_checkout(source,args.source_manifest)
    plan_path=args.inputs/'PLAN_v1.json';need(sha(plan_path)==args.plan_sha256,'frozen quality plan changed');plan=read(plan_path);q=plan['quality_recount']
    original=read(args.inputs/'NEURAL_PLAN_v1.json');need(sha(args.inputs/'NEURAL_PLAN_v1.json')==plan['original_neural_plan_sha256'],'original neural plan bytes changed')
    need(plan['cells']==original['cells'] and len(plan['cells'])==24,'quality scope changed the frozen execution cells')
    need(not args.out.exists(),'quality output must be new')
    primary=Path(q['primary_source']);primary_manifest=Path(q['primary_source_manifest'])
    need(sha(primary_manifest)==q['primary_source_manifest_sha256'],'primary source manifest changed')
    need(verify_checkout(primary,primary_manifest)==q['primary_analysis_commit'],'wrong reused analysis source')
    gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    need(not gpu,'CPU/IO quality window may not overlap GPU work')
    args.out.mkdir(parents=True,exist_ok=False)
    environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node(),CUDA_VISIBLE_DEVICES='',GPU_processes=gpu)
    put(args.out/'ENVIRONMENT.json',environment)
    put(args.out/'CONFIG.json',dict(experiment_id=plan['experiment_id'],plan=str(plan_path),plan_sha256=args.plan_sha256,
        fixed_cells=24,primary_analysis_commit=q['primary_analysis_commit'],primary_source_manifest_sha256=sha(primary_manifest),secondary_fixed_rows=96,original_D2_C8_and_first_credit_unchanged=True,new_GPU_calls=0))
    put(args.out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],orchestration_source_commit=own_commit,primary_analysis_commit=q['primary_analysis_commit'],
        source_manifest_sha256=sha(args.source_manifest),frozen_config=str(args.out/'CONFIG.json'),frozen_config_sha256=sha(args.out/'CONFIG.json'),
        environment_record=str(args.out/'ENVIRONMENT.json'),environment_sha256=sha(args.out/'ENVIRONMENT.json'),
        raw_result_location=[c['output'] for c in plan['cells']],aggregate_summary_location=str(args.out/'SUMMARY.json'),gate_decision_location=str(args.out/'GATE.json'),
        intended_primary_argv=[sys.executable,'-B',str(primary/'run_analysis.py'),'--plan',str(plan_path),'--plan-sha256',args.plan_sha256,'--source-manifest',str(primary_manifest),'--output',str(args.out/'primary'),'--components','usefulness']))
    try:
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',REVTRACE_USEFULNESS_SOURCE=str(primary))
        with (args.out/'synthetic_controls.log').open('x') as stream:
            subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(source),'-p','test*.py'],env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
        argv=read(args.out/'RUN_RECORD.json')['intended_primary_argv']
        with (args.out/'primary.log').open('x') as stream:subprocess.run(argv,cwd=primary,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
        need(read(args.out/'primary/GATE.json')['gate']=='PASS_CPU_RECOUNTS','reused primary recount failed')
        use=args.out/'primary/usefulness';summary=read(use/'SUMMARY.json')
        need(summary['recounted_cells']==summary['formally_source_revalidated_cells']==24,'primary quality scope incomplete')
        previous=read(args.inputs/'PRIOR_INPUT_RECORD_v1.json');current=read(use/'ANALYSIS_RECORD.json')
        global BASELINE
        BASELINE=previous['inputs'];common=set(BASELINE)&set(current['inputs'])
        for path in common:need(BASELINE[path]==current['inputs'][path],'prior actual-input hash differs from primary recount: '+path)
        required={str(Path(c['output'])/name) for c in plan['cells'] for name in ['attempt0/consumer.jsonl','attempt0/events.jsonl','attempt0/worker_records.jsonl','attempt0/config.json','audit/FRONTIERS.json','audit/SUMMARY.json','FREEZE.json','RUN_RECORD.json','GATE.json']}
        need(required<=common,'prior raw-input baseline coverage incomplete')
        put(args.out/'INPUT_BASELINE_REVALIDATION.json',dict(gate='PASS_PRIOR_ACTUAL_INPUT_HASHES',common_inputs=len(common),required_core_inputs=len(required),all_common_byte_hashes_equal=True,prior_input_record_sha256=sha(args.inputs/'PRIOR_INPUT_RECORD_v1.json')))
        offered=read(use/'OFFERED_FRONTIERS.json');runs=read(use/'RUNS.json');cells={c['cell_id']:c for c in plan['cells']}
        partitions=[]
        for run in runs:
            rows=[r for r in offered if r['cell_id']==run['cell_id']];partition=partition_first_credit(rows)
            expected=read(Path(cells[run['cell_id']]['output'])/'audit/FRONTIERS.json')
            need(abs(partition['original_dual_credited_audio_seconds']-sum(r['audio_seconds'] for r in expected if r['dual_credit']))<1e-7,'original first credit changed')
            partitions.append(dict(cell_id=run['cell_id'],arm=run['arm'],arrival=run['arrival'],repeat=run['repeat'],**partition))
        need(len(partitions)==24,'support partition scope incomplete')
        module=load_usefulness(primary);need(module.NORMALIZATION==q['normalizer'],'frozen normalizer changed')
        targets=read(args.inputs/'TARGET_BATCHES_v1.json');secondary=targeted_rows(targets,cells,module)
        put(args.out/'ALL24_SUPPORT_PARTITIONS.json',partitions);put(args.out/'SYNC96_COMPLETE_VIEW_SUPPORT.json',secondary)
        put(args.out/'SYNC96_SUMMARY.json',secondary_summaries(secondary))
        with (args.out/'SYNC96_COMPLETE_VIEW_SUPPORT.csv').open('x',encoding='utf8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(k for r in secondary for k in r)));writer.writeheader();writer.writerows(secondary)
        need(verify_checkout(primary,primary_manifest)==q['primary_analysis_commit'],'reused source changed during recount')
        need(verify_checkout(source,args.source_manifest)==own_commit,'orchestration source changed')
        result=dict(status='COMPLETE_ALL24_RETROSPECTIVE_SAME_F_SUPPORT',cells=24,original_first_credit_unchanged=True,
                    fixed_secondary_rows=96,interpretation=q['interpretation'],unknowns_preserved=True,new_GPU_calls=0,
                    primary_analysis_commit=q['primary_analysis_commit'],orchestration_source_commit=own_commit)
        put(args.out/'SUMMARY.json',result);put(args.out/'SUPPLEMENT_INPUTS.json',INPUTS)
        put(args.out/'GATE.json',dict(gate='PASS_ALL24_SAME_F_SUPPORT_RECOUNT',scientific_agreement='Reported from actual results; not inferred from execution PASS',new_GPU_calls=0))
        print(json.dumps(result))
    except Exception as error:
        put(args.out/'STOP.json',dict(error=repr(error),traceback=traceback.format_exc(),new_GPU_calls=0))
        put(args.out/'GATE.json',dict(gate='FAIL_PRESERVED',reason=repr(error),new_GPU_calls=0))
        raise

if __name__=='__main__':main()

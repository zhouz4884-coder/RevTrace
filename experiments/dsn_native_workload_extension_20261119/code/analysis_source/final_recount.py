"""Complete three-policy workload recount, including actual D2 read points.

No runtime/audit/controller or neural imports. No R x S interaction is
estimated: this extension contains only R1/S0, R1/S1 and Conservative/S1.
"""
from __future__ import annotations
import argparse,hashlib,json,math,pathlib,platform,subprocess,sys,traceback
from collections import Counter,defaultdict
import base_recount as B
from continuity_readpoints import (CLASSES,aggregate_readpoints,credited_readpoints,
    duration_statistics,high_watermark_gap,union_area,validate_rows,validate_windows)
from quality_recount import SCOPE as QUALITY_SCOPE, pool_quality,verify_quality

E=pathlib.Path(__file__).resolve().parents[1]
CONDITIONS=('conservative_s1','r1s0','r1s1')
COMPLETE='COMPLETE_NATIVE_WORKLOAD_EXTENSION_TASK_AND_ENDPOINTS'
NN='11453433c154aeffbff703c4c8dc9697421430e1'
VIEW_AUDIT='0571d51d85542e1eaf000be8082585a66e5978be'
need=B.need;read=B.read;close=B.close

def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def source_gate(manifest_path):
    root=pathlib.Path(__file__).resolve().parent;m=json.loads(pathlib.Path(manifest_path).read_bytes())
    def git(*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
    need(pathlib.Path(git('rev-parse','--show-toplevel')).resolve()==root,'analysis is not an independent source checkout')
    need(git('rev-parse','HEAD')==m['source_commit']and not git('status','--porcelain','--untracked-files=all'),'analysis source identity/clean gate failed')
    tracked=set(git('ls-files','-z').split('\0'))-{''}
    need(tracked=={x['path']for x in m['files']},'incomplete analysis source manifest')
    for row in m['files']:
        raw=(root/row['path']).read_bytes();need(len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'],'analysis source changed: '+row['path'])
    return m

def load_reference(folder,expected_nn,expected_n):
    receipt=read(folder/'REFERENCE_RECEIPT.json');gate=read(folder/'GATE.json');summary=read(folder/'SUMMARY.json')
    for obj in(receipt,gate,summary):
        need(obj['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES','reference did not pass')
        need(obj['actual_NN_source_commit']==expected_nn and obj['reference_only']is True and obj['actual_serving_runs']==0,'reference execution/cost role differs')
    need(gate['all_original_full_state_C_IDs_equal']is True,'reference state/C/IDs mismatch')
    sources={s['source_id']:s for s in receipt['sources']}
    need(len(sources)==len(receipt['sources'])==expected_n and len({s['speaker_id']for s in sources.values()})==expected_n,'reference actual source/speaker count differs')
    steps=sum((s['frames']+7999)//8000 for s in sources.values())
    need(gate['expected_sources']==gate['completed_sources']==expected_n and gate['expected_original_steps']==steps,'reference is incomplete')
    need(receipt['original_continuous_no_between_step_restore']is True and receipt['restored_repeats_per_edge']==2,'original/restore reference path differs')
    need(receipt['ledger']['continuous_original_step_completed']==steps and receipt['ledger']['restored_original_input_full_step_completed']==2*steps,'reference paid-step ledger differs')
    for key,filename in [('reference_details','REFERENCE_DETAILS.json'),('reference_gate','GATE.json'),('genesis','GENESIS.json')]:
        read(folder/filename);need(B.INPUTS[str(folder/filename)]['sha256']==receipt[key]['sha256'],'reference bytes differ: '+key)
    details=read(folder/'REFERENCE_DETAILS.json');genesis=read(folder/'GENESIS.json')
    need(len(details)==steps and len({(d['source_id'],d['end'])for d in details})==steps,'reference detail denominator/unique identity differs')
    for sid,source in sources.items():
        close(source['frames']/16000,source['duration'],'original source duration')
        need(12.<=source['duration']<=20.,'metadata length stratum changed')
        own=sorted((r for r in details if r['source_id']==sid),key=lambda r:r['end'])
        need([r['end']for r in own]==list(range(8000,source['frames'],8000))+[source['frames']],'reference source cadence differs')
        previous=genesis[sid];need(previous['frontier']==0,'reference genesis frontier differs')
        for row in own:
            need(row['original_full_start_cut']==previous and row['continuous_original_no_between_step_restore']is True,'reference original chain/restore mode differs')
            for state in(row['original_full_start_cut'],row['original_full_cut']):
                need(state['contract']['stage_execution']['source_commit']==expected_nn and state['contract']['source_sha']==source['audio_sha256'],'reference source marker/audio differs')
            previous=row['original_full_cut']
    return receipt,sources,genesis

def raw_consumer(root,view,source,origin,end,retain,max_bytes):
    path=root/'consumer.jsonl'
    if not path.is_file():raise B.NotReady('Required actual Consumer mirror missing: '+str(path))
    raw=path.read_bytes();need(len(raw)<=max_bytes,'bounded Consumer mirror exceeds declared limit')
    B.INPUTS[str(path)]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    bindings={x['path']:x for x in view['input_files']};need('consumer.jsonl'in bindings,'actual Consumer missing original audit binding')
    need(bindings['consumer.jsonl']['sha256']==B.INPUTS[str(path)]['sha256']and bindings['consumer.jsonl']['bytes']==len(raw),'actual Consumer bytes differ from independent audit')
    rows=[json.loads(line)for line in raw.splitlines()if line.strip()]
    need(len(rows)==view['continuity']['actual_consumer_rows'],'actual row count differs')
    validate_rows(rows,source['source_id'],origin,end,retain)
    return rows

def recount_windows(windows,continuity):
    need(len(windows)==continuity['total_withdrawals'],'loss-window count differs')
    for cls in CLASSES:
        own=[w for w in windows if w['classification']==cls]
        need(len(own)==continuity[cls+'_withdrawals'],'loss class count differs')
        close(sum(w['initial_removed_audio_seconds']for w in own),continuity[cls+'_removed_audio_seconds'],'removed audio '+cls)
        close(union_area([s for w in own for s in w['segments']]),continuity['same_root_'+cls+'_gap_audio_seconds_x_wall_seconds'],'root-bounded union area '+cls)
    close(union_area([s for w in windows for s in w['segments']]),continuity['observed_loss_window_union_area_audio_seconds_x_wall_seconds'],'all loss-window union area')

def raw_endpoint_check(frontiers,rows):
    for f in frontiers:
        for key,field in [('D','visible_frontier'),('C','certified_frontier')]:
            first=next((r['observed']-f['offer']for r in rows if r['source_id']==f['source_id']and r['observed']>=f['offer']and r[field]>=f['frontier']),None)
            need((first is None)==(f[key]is None),'raw actual first '+key+' availability differs')
            if first is not None:close(first,f[key],'raw actual first '+key)

def pooled(rows):
    result=B.total(rows)
    for key in('Owner_admitted_ready_reuse','unique_promoted_jobs','selected_promoted_jobs'):result[key]=sum(r[key]for r in rows)
    result['D2_readpoint']=aggregate_readpoints([r['D2_readpoint']for r in rows])
    result['quality']=pool_quality([r['quality']for r in rows])
    return result

def simple_effects(values):
    return dict(S_at_R1=values['r1s1']-values['r1s0'],full_S1_minus_conservative=values['r1s1']-values['conservative_s1'],full_S0_minus_conservative=values['r1s0']-values['conservative_s1'])

def readpoint_effect(first,second):
    """Difference bounds; each policy retains its own first-credit population."""
    return dict(point_audio_seconds=(None if first['readpoint_censored_frontiers']or second['readpoint_censored_frontiers']else first['observed_missing_audio_seconds']-second['observed_missing_audio_seconds']),
        lower_audio_seconds=first['missing_audio_seconds_lower']-second['missing_audio_seconds_upper'],
        upper_audio_seconds=first['missing_audio_seconds_upper']-second['missing_audio_seconds_lower'],
        population_scope='Policy-specific original first-credit-passing intervals; not a common selected population or a causal estimate.')

def execute(args,out):
    B.INPUTS.clear();B.E=pathlib.Path(args.evidence_root).resolve()
    need(1<=args.expected_sources<=4,'declared actual N must be one to four')
    refdir=pathlib.Path(args.reference).resolve();receipt,refs,refgen=load_reference(refdir,args.expected_nn,args.expected_sources)
    reference_sha=B.INPUTS[str(refdir/'REFERENCE_DETAILS.json')]['sha256']
    original_final_text={sid:next(r['original_full_cut']['transcript']for r in read(refdir/'REFERENCE_DETAILS.json')if r['source_id']==sid and r['end']==s['frames'])for sid,s in refs.items()}
    folder=pathlib.Path(args.campaign).resolve();plan=read(folder/'CONFIG.json');summary=read(folder/'SUMMARY.json');gate=read(folder/'GATE.json');record=read(folder/'RUN_RECORD.json')
    frozen_plan=read(pathlib.Path(args.plan).resolve());need(frozen_plan==plan,'actual campaign differs from frozen plan')
    count=6*args.expected_sources
    if summary.get('completed_trials')!=count or summary.get('planned_trials')!=count or len(summary.get('cells',[]))!=count:raise B.NotReady('Complete three-condition/two-repeat/declared-actual-N data required; no final estimates emitted')
    need(summary['status']==gate['status']==COMPLETE and not summary['failed_attempts'],'campaign technical completion gate failed')
    need(summary['actual_NN_source_commit']==record['actual_NN_source_commit']==plan['actual_NN']['source_commit']==args.expected_nn,'closed campaign runtime identities differ')
    need(record['code_commit']==plan['driver']['source_commit']==receipt['generator_source_commit'],'campaign/generator execution source differs')
    need(record['frozen_config_sha256']==B.INPUTS[str(folder/'CONFIG.json')]['sha256'],'campaign CONFIG binding differs')
    need(plan['actual_NN']['source_commit']==args.expected_nn and plan['expected_trials']==count,'campaign neural source/scope differs')
    need(plan['view_audit']['source_commit']==VIEW_AUDIT,'independent actual-view auditor changed')
    need(plan['reference_details']['sha256']==reference_sha and plan['reference_receipt']['sha256']==B.INPUTS[str(refdir/'REFERENCE_RECEIPT.json')]['sha256'],'campaign reference binding differs')
    cadence=plan['cadence'];need(cadence['sample_rate_hz']==16000 and cadence['input_release_seconds']==.5 and cadence['full_step_samples']==8000,'original cadence changed')
    need(plan['original_D2_seconds']==2. and plan['original_C8_seconds']==8.,'original deadlines changed')
    need(plan['opportunity_nonzero_required']is False and plan['resource_drift_reject_or_retry']is False and
         plan['factorial_interaction_not_estimated']is True,'outcome-based continuation or three-policy contract changed')
    need(summary['no_opportunity_or_tie_is_failure']is False and summary['SLO_failures_retained']is True and
         summary['factorial_interaction_not_estimated']is True,'closed-summary outcome scope changed')
    need(set(plan['gpu_uuids'])=={'0','1'} and len(set(plan['gpu_uuids'].values()))==2,'prespecified physical GPU identities missing')
    sources={s['source_id']:s for s in plan['sources']};need(set(sources)==set(refs)and len(sources)==args.expected_sources,'complete reference/campaign bank differs')
    need(all(sources[s]==refs[s]for s in sources),'frozen source metadata changed')
    selection=read(pathlib.Path(args.selection).resolve());need(B.INPUTS[str(pathlib.Path(args.selection).resolve())]['sha256']==plan['selection_receipt']['sha256'],'metadata selection receipt changed')
    need(selection['status']=='PASS_STRICT_METADATA_SELECTED_ORIGINAL_MAGICDATA_TEST_AUDIO_AVAILABLE'and selection['corpus']=='MAGICDATA68'and selection['split']=='test','original metadata selection is not terminal eligible test bank')
    need(selection['metadata_first']is True and type(selection['model_calls'])is int and selection['model_calls']==0 and
         all(selection[k]is True for k in ('no_concat','no_trim','no_resample')),'metadata-first/unmodified selection contract changed')
    need({s['source_id']:s for s in selection['sources']}==sources,'selected original metadata bank differs from measured service bank')
    planned={c['cell_id']:c for c in plan['cells']};need(len(planned)==count and {c['cell_id']for c in summary['cells']}==set(planned),'planned/completed cell identity differs')
    expected={(sid,rep,c)for sid in sources for rep in(0,1)for c in CONDITIONS};actual={(c['source_id'],c['repeat'],c['condition'])for c in summary['cells']}
    need(actual==expected and len(actual)==count,'complete three-policy matrix differs')
    records=[];all_windows=[];point_details=[];bindings=[]
    for cell in summary['cells']:
        cid=cell['cell_id'];rawroot=folder/'cells'/cid;need(rawroot.resolve().is_relative_to((folder/'cells').resolve()),'cell path escaped mirror')
        row=B.check_cell(folder,cell,planned[cid],sources[cell['source_id']],plan,reference_sha)
        view=read(rawroot/'INDEPENDENT_VIEW_AUDIT.json');windows=read(rawroot/'view_audit/OBSERVED_LOSS_WINDOWS.json');events=read(rawroot/'view_audit/CANONICAL_SUPPORT_EVENTS.json')
        origin=read(rawroot/'ORIGIN.json')['origin_perf'];end=read(rawroot/'SERVICE_END.json')['service_end_perf'];genesis=read(rawroot/'GENESIS.json')
        sid=cell['source_id'];need(genesis=={sid:refgen[sid]},'actual initial state differs from measured reference')
        rows=raw_consumer(rawroot,view,sources[sid],origin,end,cell['consumer_retain_views'],args.max_consumer_bytes)
        validate_windows(rows,events,windows,end);recount_windows(windows,view['continuity']);raw_endpoint_check(cell['primary']['frontiers'],rows)
        close(high_watermark_gap(rows,end),view['continuity']['total_gap_audio_seconds_x_wall_seconds'],'actual-row high-watermark gap')
        rp=credited_readpoints(cell['primary']['frontiers'],rows,windows,source_id=sid,origin=origin,end=end,initial_known=True,initial_visible=0)
        close(rp['summary']['first_credited_audio_seconds'],row['credit_audio_s'],'readpoint credited population vs original A2,8')
        row['D2_readpoint']=rp['summary']
        row['quality']=verify_quality(read(rawroot/'SUMMARY.json')['quality'],sources[sid],original_final_text[sid])
        for k in('Owner_admitted_ready_reuse','unique_promoted_jobs','selected_promoted_jobs'):row[k]=cell['job_accounting'][k]
        records.append(row)
        all_windows.extend(dict(cell_id=cid,condition=cell['condition'],repeat=cell['repeat'],**w)for w in windows)
        point_details.extend(dict(cell_id=cid,condition=cell['condition'],repeat=cell['repeat'],**f)for f in rp['frontiers'])
        bindings.append(dict(cell_id=cid,**{k:row[k]for k in ('service_origin_perf','external_physical_drain_perf','runtime_service_end_perf','runtime_end_minus_external_drain_seconds','last_canonical_application_perf','certified_EOS_consume_perf')}))
    totals={c:pooled([r for r in records if r['condition']==c])for c in CONDITIONS}
    planned_offered=2*math.fsum(s['frames']/16000 for s in sources.values());planned_frontiers=2*sum((s['frames']+7999)//8000 for s in sources.values())
    for c,t in totals.items():
        close(t['offered_audio_s'],planned_offered,'entire offered bank '+c);need(t['trials']==2*args.expected_sources and t['offered_frontiers']==planned_frontiers,'condition source/repeat/frontier scope differs')
        stored=summary['condition_totals'][c]
        for key,field in [('trials','completed_trials'),('offered_audio_s','observed_offered_audio_s'),('credit_audio_s','credit_audio_s'),('worker_seconds','worker_seconds'),('both_board_J','both_board_J'),('whole_run_passes','whole_run_passes')]:close(t[key],stored[field],'campaign scalar '+c+'/'+field)
        for key,value in stored.get('continuity_totals',{}).items():close(t[key],value,'campaign continuity '+c+'/'+key)
    per_source=[];effects=[]
    metrics=('credit_audio_s','worker_seconds','both_board_J','avoidable_withdrawals','necessary_withdrawals','unknown_withdrawals','total_gap_audio_seconds_x_wall_seconds','same_root_avoidable_gap_audio_seconds_x_wall_seconds')
    for sid in sorted(sources):
        values={c:pooled([r for r in records if r['source_id']==sid and r['condition']==c])for c in CONDITIONS}
        per_source.extend(dict(source_id=sid,speaker_id=sources[sid]['speaker_id'],condition=c,**t)for c,t in values.items())
        effects.append(dict(source_id=sid,speaker_id=sources[sid]['speaker_id'],effects={m:simple_effects({c:values[c][m]for c in CONDITIONS})for m in metrics},
            D2_previously_credited_missing_S_at_R1=readpoint_effect(values['r1s1']['D2_readpoint'],values['r1s0']['D2_readpoint'])))
    distribution={}
    for condition in CONDITIONS:
        distribution[condition]={}
        for cls in CLASSES:
            own=[w for w in all_windows if w['condition']==condition and w['classification']==cls]
            distribution[condition][cls]=dict(windows=len(own),actual_restore_duration=duration_statistics([w['observed_duration_seconds']for w in own if w['restored']]),
                all_observed_window_duration=duration_statistics([w['observed_duration_seconds']for w in own]),
                restored=sum(w['restored']for w in own),right_censored=sum(w['right_censored']for w in own),boundary_truncated=sum(w['boundary_truncated']for w in own))
    source_quality=[]
    for sid in sorted(sources):
        own=[r['quality']for r in records if r['source_id']==sid]
        need(len(own)==6 and all(q==own[0]for q in own),'original quality differs across policies/repeats on one source')
        source_quality.append(dict(speaker_id=sources[sid]['speaker_id'],all_six_policy_repeat_outputs_equal=True,**own[0]))
    quality=dict(scope=QUALITY_SCOPE,normalization='Delete each Unicode code point for which str.isspace() is true; no punctuation, case or Unicode-form mapping.',
        per_source=source_quality,pooled_distinct_sources=pool_quality(source_quality),
        per_condition_all_execution_outputs={c:totals[c]['quality']for c in CONDITIONS},
        repeat_scope='Per-condition counts include both timing repeats. Distinct-source pooled CER uses one original output per source; repeats do not add acoustic units.')
    result=dict(status='PASS_COMPLETE_NATURAL_WORKLOAD_THREE_POLICY_RECOUNT',actual_source_clusters=args.expected_sources,trials=count,conditions=list(CONDITIONS),timing_repeats=2,
        actual_NN_source_commit=args.expected_nn,all_offered_audio_seconds_per_condition=planned_offered,original_reference_steps_checked=sum(r['original_reference_steps']for r in records),
        reference_ledger=receipt['ledger'],condition_totals=totals,source_condition_totals=per_source,source_simple_effects=effects,
        original_native_quality=quality,
        pooled_simple_effects={m:simple_effects({c:totals[c][m]for c in CONDITIONS})for m in metrics},observed_restoration_duration_distributions=distribution,
        D2_previously_credited_missing_S_at_R1=readpoint_effect(totals['r1s1']['D2_readpoint'],totals['r1s0']['D2_readpoint']),
        D2_readpoint_scope='First-credit-passing population; actual event-sourced state persists to explicit complete FIFO SERVICE_END. Later reads are NA/censored. Loss-segment/audio-interval unions avoid repeated-credit and overlap double count.',
        complete_RxS_factorial=False,no_RxS_interaction_estimated=True,no_SLO_or_zero_opportunity_filtering=True,
        execution_components={k:plan[k]for k in ('driver','actual_NN','view_audit','production_support')},energy_window_bindings=bindings,input_manifest=B.INPUTS,
        neural_modules_imported=[m for m in('torch','transformers','vllm','whisper','soundfile')if m in sys.modules])
    need(not result['neural_modules_imported'],'analysis imported neural modules')
    write(out/'SUMMARY.json',result);write(out/'D2_READPOINT_DETAILS.json',point_details);write(out/'OBSERVED_LOSS_WINDOWS.json',all_windows);write(out/'QUALITY.json',quality)
    B.write_csv(out/'ALL_CELLS.csv',[{k:v for k,v in r.items()if not isinstance(v,(dict,list))}for r in records])
    B.write_csv(out/'CONDITION_TOTALS.csv',[dict(condition=c,**{k:v for k,v in t.items()if not isinstance(v,(dict,list))})for c,t in totals.items()])
    write(out/'GATE.json',dict(status=result['status'],trials=count,actual_source_clusters=args.expected_sources,all_conditions_complete=True,complete_RxS_factorial=False))
    md=['# 新自然负载：三策略完整重算','',f"{args.expected_sources}个元数据冻结来源，{count}格全部完成；每条件两次fresh重复，全部offered/EOS和SLO miss保留。",'',
        '| 条件 | Credit s | Coverage % | Pass | Worker-s | 两板kJ | 可避免/必要/未知 | 总高水位Gap | 同根可避免Gap | D2读点缺失下/上界audio-s |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for c,t in totals.items():
        rp=t['D2_readpoint'];md.append(f"|{c}|{t['credit_audio_s']:.6f}|{t['coverage_percent']:.3f}|{t['whole_run_passes']}/{t['trials']}|{t['worker_seconds']:.3f}|{t['both_board_J']/1000:.3f}|"+'/'.join(str(t[x+'_withdrawals'])for x in CLASSES)+f"|{t['total_gap_audio_seconds_x_wall_seconds']:.6f}|{t['same_root_avoidable_gap_audio_seconds_x_wall_seconds']:.6f}|{rp['missing_audio_seconds_lower']:.6f}/{rp['missing_audio_seconds_upper']:.6f}|")
    md+=['','D2读点只针对已经满足原first-credit的区间；actual状态按原事件时钟持续到完整FIFO closeout。超出END或缺初始见证保留删失/NA，不默认为零。部分音频尾段按被移除范围与原区间交集计，同读点union不重复计。','',
        '固定R1处的S简单效应与Conservative锚点见JSON。该三策略扩展没有R0两格，因此不估计完整R×S交互。全高水位Gap与同root分类窗口、恢复时长分布分别保留。两板主能量到外部物理drain，原runtime SERVICE_END及其能量对象另行绑定。']
    q=quality['pooled_distinct_sources'];md+=['',f"原native whitespace-only最终任务CER：{q['character_edits']}/{q['reference_characters']}={q['CER']!r}；逐源见QUALITY.json。每源六次策略/重复输出均逐字等于原完整参考末状态transcript；此处去重复来源汇总，不把时序重复增加为语音样本。"]
    (out/'REPORT.zh.md').write_text('\n'.join(md)+'\n',encoding='utf8')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence-root',default=str(E));p.add_argument('--campaign',required=True);p.add_argument('--plan',required=True);p.add_argument('--reference',required=True);p.add_argument('--selection',required=True);p.add_argument('--expected-sources',required=True,type=int);p.add_argument('--expected-nn',default=NN);p.add_argument('--source-manifest',required=True);p.add_argument('--max-consumer-bytes',type=int,default=2_097_152);p.add_argument('--experiment-id',default='REVTRACE_LONG_NATURAL_READPOINT_RECOUNT_20261119');p.add_argument('--out',required=True);args=p.parse_args()
    manifest=source_gate(args.source_manifest);out=pathlib.Path(args.out).resolve();need(not out.exists(),'never overwrite a recount result');out.mkdir(parents=True)
    write(out/'CONFIG.json',vars(args));write(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0))
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    write(out/'RUN_RECORD.json',dict(experiment_id=args.experiment_id,code_commit=manifest['source_commit'],source_manifest_sha256=sha(pathlib.Path(args.source_manifest)),frozen_config_sha256=sha(out/'CONFIG.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=args.campaign,aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),measured_neural_source_commit=args.expected_nn))
    try:
        result=execute(args,out);source_gate(args.source_manifest);print(json.dumps(dict(status=result['status'],trials=result['trials'],out=str(out))))
    except B.NotReady as error:
        write(out/'GATE.json',dict(status='NOT_READY_NO_FINAL_POINT_ESTIMATE',reason=str(error)));print(str(error));sys.exit(2)
    except BaseException:
        write(out/'GATE.json',dict(status='FAIL_DERIVED_RECOUNT_PRESERVED_NOT_GPU_TRIAL_STATUS',failure=traceback.format_exc()));raise

if __name__=='__main__':main()

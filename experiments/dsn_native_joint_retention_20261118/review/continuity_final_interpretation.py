"""Independent read-only arithmetic over the two closed campaign mirrors.

No runtime/controller imports, no original journal repair, no model calls.
The derived V1 drain/SERVICE_END ordering assertion is deliberately not used.
"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, math, statistics

E=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
CONDITIONS=('r0s0','r0s1','r1s0','r1s1','conservative_s1')
inputs={}
def read(p):
    raw=p.read_bytes()
    inputs[p.relative_to(E).as_posix()]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    return json.loads(raw)
def linear(values,p):
    a=sorted(values)
    if not a:return None
    index=(len(a)-1)*p;lo=math.floor(index);hi=math.ceil(index)
    return a[lo]+(a[hi]-a[lo])*(index-lo)
def stats(values):
    return dict(n=len(values),min_seconds=min(values)if values else None,
                median_seconds=statistics.median(values)if values else None,
                mean_seconds=statistics.mean(values)if values else None,
                p95_linear_seconds=linear(values,.95),max_seconds=max(values)if values else None)
def union_area(segments):
    bysource=defaultdict(list)
    for x in segments:
        assert x['end']>=x['start']and x['high']>=x['low']
        bysource[x['source_id']].append(x)
    answer=0.
    for rows in bysource.values():
        times=sorted({t for x in rows for t in (x['start'],x['end'])})
        for begin,end in zip(times,times[1:]):
            intervals=sorted((x['low'],x['high'])for x in rows if x['start']<=begin and x['end']>=end)
            merged=[]
            for low,high in intervals:
                if merged and low<=merged[-1][1]:merged[-1][1]=max(high,merged[-1][1])
                else:merged.append([low,high])
            answer+=(end-begin)*sum(high-low for low,high in merged)/16000
    return answer

cells=[];bycondition=defaultdict(list);bysource=defaultdict(list);allwindows=[];allevents=[]
for tag,expected in [('PILOT20_V1',20),('CONFIRM60_V1',60)]:
    d=read(E/'gpu_results'/tag/'SUMMARY.json')
    assert d['status']=='COMPLETE_NATIVE_FACTORIAL_AND_CONSERVATIVE_TASK_AND_ENDPOINTS'
    assert d['completed_trials']==d['planned_trials']==expected and not d['failed_attempts']
    for c in d['cells']:
        condition=c['condition'];assert condition in CONDITIONS
        expected_retain=condition.endswith('s1')
        assert c['consumer_retain_views'] is expected_retain and c['view_audit']['consumer_retain_views'] is expected_retain
        assert c['strategy']==('ready_only'if condition.startswith('r0')else'fullcall'if condition.startswith('r1')else'conservative')
        root=E/'gpu_results'/tag/'cells'/c['cell_id']/'view_audit'
        windows=read(root/'OBSERVED_LOSS_WINDOWS.json');events=read(root/'CANONICAL_SUPPORT_EVENTS.json')
        continuity=c['view_audit']['continuity']
        assert c['view_audit']['status']=='PASS_NATIVE_VIEW_APPLICATION_AUDIT'
        assert len(events)==continuity['canonical_applications']
        assert all(x['source_id']==c['source_id']and x['metadata_binding_checked']for x in events)
        assert c['semantic']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE'
        assert c['worker_ledger']['status']=='PASS_COMPLETE_WORKER_TERMINAL_TIMER_LEDGER'
        assert c['sampled_energy_ownership']['status']=='PASS_SAMPLED_TWO_BOARD_OWNED_WORKER_WINDOW'
        assert c['job_accounting']['status']=='PASS_DISJOINT_JOB_ACCOUNTING'
        byindex={x['row_index']:x for x in events};assert len(byindex)==len(events)
        counted=Counter();segments=defaultdict(list)
        for w in windows:
            assert abs((w['end']-w['start'])-w['observed_duration_seconds'])<1e-10
            assert abs((w['before_visible_frontier']-w['after_visible_frontier'])/16000-w['initial_removed_audio_seconds'])<1e-10
            event=byindex.get(w['row_index'])
            if event:
                assert event['observed']==w['start']and event['after_visible_frontier']==w['after_visible_frontier']and event['before_visible_frontier']==w['before_visible_frontier']
                expected_class={'compatible_boundary':'avoidable','refuted_boundary':'necessary','missing_boundary':'unknown'}[event['support_status']]
                assert expected_class==w['classification']
            else:assert w['classification']=='unknown'
            counted[w['classification']]+=1
            assert abs(union_area(w['segments'])-w['observed_same_root_area_audio_seconds_x_wall_seconds'])<1e-9
            segments[w['classification']].extend(w['segments'])
            allwindows.append(dict(campaign=tag,cell_id=c['cell_id'],condition=condition,repeat=c['repeat'],**w,support_event=event))
        assert len(windows)==continuity['total_withdrawals']
        for cls in ('avoidable','necessary','unknown'):
            assert counted[cls]==continuity[cls+'_withdrawals']
            assert abs(union_area(segments[cls])-continuity['same_root_'+cls+'_gap_audio_seconds_x_wall_seconds'])<1e-9
        ahead=[x for x in events if x['before_nonempty_visible_ahead']]
        assert len(ahead)==continuity['nonempty_ahead_canonical_applications']
        compatible=[x for x in ahead if x['support_status']=='compatible_boundary']
        assert len(compatible)==continuity['compatible_ahead_applications']
        assert sum(x['preserved_complete_tip']for x in compatible)==continuity['compatible_ahead_preserved']
        allevents.extend(dict(cell_id=c['cell_id'],condition=condition,repeat=c['repeat'],**x)for x in events)
        record=dict(campaign=tag,cell_id=c['cell_id'],source_id=c['source_id'],speaker_id=c['speaker_id'],repeat=c['repeat'],condition=condition,
            offered_audio_seconds=c['primary']['offered_audio_seconds'],credit_audio_seconds=c['primary']['dual_deadline_audio_credit_seconds'],
            pass_whole_run=c['primary']['complete_coverage_and_original_quantile_pass'],
            worker_seconds=c['worker_ledger']['worker_seconds'],
            both_board_service_to_drain_J=c['common_external_energy']['origin_to_confirmed_physical_model_drain']['total_joules'],
            Owner_admitted_ready_reuse=c['job_accounting']['Owner_admitted_ready_reuse'],unique_promoted_jobs=c['job_accounting']['unique_promoted_jobs'],
            selected_promoted_jobs=c['job_accounting']['selected_promoted_jobs'],continuity=continuity)
        cells.append(record);bycondition[condition].append(record);bysource[c['source_id']].append(record)

assert len(cells)==80 and len({c['cell_id']for c in cells})==80 and len(bysource)==8
assert all(len(v)==10 and len({(x['condition'],x['repeat'])for x in v})==10 for v in bysource.values())
totals={};distributions={}
counts=('canonical_applications','nonempty_ahead_canonical_applications','compatible_ahead_applications','compatible_ahead_preserved','compatible_ahead_changed','refuted_ahead_applications','missing_witness_ahead_applications','total_withdrawals','avoidable_withdrawals','necessary_withdrawals','unknown_withdrawals','removed_audio_seconds','avoidable_removed_audio_seconds','necessary_removed_audio_seconds','unknown_removed_audio_seconds','total_gap_audio_seconds_x_wall_seconds','same_root_avoidable_gap_audio_seconds_x_wall_seconds','same_root_necessary_gap_audio_seconds_x_wall_seconds','same_root_unknown_gap_audio_seconds_x_wall_seconds','gap_restored_windows','gap_right_censored_windows','gap_boundary_truncated_windows')
for condition in CONDITIONS:
    cc=bycondition[condition];assert len(cc)==16
    total={name:sum(x['continuity'][name]for x in cc)for name in counts}
    for name in ('offered_audio_seconds','credit_audio_seconds','worker_seconds','both_board_service_to_drain_J','Owner_admitted_ready_reuse','unique_promoted_jobs','selected_promoted_jobs'):total[name]=sum(x[name]for x in cc)
    total['credit_percent']=100*total['credit_audio_seconds']/total['offered_audio_seconds']
    total['whole_run_passes']=sum(x['pass_whole_run']for x in cc);total['runs']=len(cc)
    totals[condition]=total
    distributions[condition]={cls:stats([w['observed_duration_seconds']for w in allwindows if w['condition']==condition and w['classification']==cls])for cls in ('avoidable','necessary','unknown')}
assert max(t['offered_audio_seconds']for t in totals.values())-min(t['offered_audio_seconds']for t in totals.values())<1e-9
source_results=[]
for sid,rows in sorted(bysource.items()):
    record=dict(source_id=sid,speaker_id=rows[0]['speaker_id'],conditions={})
    for condition in CONDITIONS:
        cc=[x for x in rows if x['condition']==condition]
        record['conditions'][condition]={name:sum(x[name]for x in cc)for name in ('credit_audio_seconds','worker_seconds','both_board_service_to_drain_J','Owner_admitted_ready_reuse','unique_promoted_jobs')}
        record['conditions'][condition].update({name:sum(x['continuity'][name]for x in cc)for name in ('compatible_ahead_applications','compatible_ahead_preserved','avoidable_withdrawals','necessary_withdrawals','unknown_withdrawals')})
    source_results.append(record)
zero_any=[x['speaker_id']for x in source_results if sum(x['conditions'][k]['compatible_ahead_applications']for k in CONDITIONS[:4])==0]
zero_full=[x['speaker_id']for x in source_results if sum(x['conditions'][k]['compatible_ahead_applications']for k in ('r1s0','r1s1'))==0]
restoration=Counter(w['stop_reason']for w in allwindows)
witness1=next(w for w in allwindows if w['cell_id']=='RS18_CONFIRM60_V1_BAC009S0907W0440_r1s0_r1'and w['classification']=='avoidable')
witness2=next(w for w in allwindows if w['cell_id']=='RS18_CONFIRM60_V1_BAC009S0902W0343_r1s1_r0'and w['classification']=='necessary')
result=dict(record_type='INDEPENDENT_READ_ONLY_CLOSED_REPORT_INTERPRETATION_NOT_NEW_GPU_EXPERIMENT',date='2026-11-19',
    input_files=inputs,input_count=len(inputs),runtime_commit='11453433c154aeffbff703c4c8dc9697421430e1',
    source_clusters=8,timing_repeats=2,actual_GPU_trials=80,condition_totals=totals,source_results=source_results,
    observed_window_duration_distributions=distributions,loss_windows=allwindows,restoration_stop_reasons=dict(restoration),
    sampled_canonical_events=len(allevents),zero_compatible_opportunity_sources_any_factor_arm=zero_any,zero_compatible_opportunity_sources_fullcall_bothS=zero_full,
    witnessed_cases=[witness1,witness2],
    credit_simple_effect_S_at_R0_seconds=totals['r0s1']['credit_audio_seconds']-totals['r0s0']['credit_audio_seconds'],
    credit_simple_effect_S_at_R1_seconds=totals['r1s1']['credit_audio_seconds']-totals['r1s0']['credit_audio_seconds'],
    credit_factorial_interaction_seconds=totals['r1s1']['credit_audio_seconds']-totals['r1s0']['credit_audio_seconds']-totals['r0s1']['credit_audio_seconds']+totals['r0s0']['credit_audio_seconds'],
    derived_V1_drain_assertion_failure_is_not_GPU_trial_failure=True,
    scope=dict(gap='Total high-water deficit and classified same-root union areas are distinct; classifications/segments independently re-summed.',restoration='All observed stop reasons are restored_within_same_root; with the audited canonical/private row vocabulary this implies restoration by Private application, not a new Canonical fact. The bounded windows do not provide the restoring publication ID or text hash.',promotion='Unique promoted-job counts are actual jobs within each cell, not automatically model-active handovers; job IDs remain cell-qualified.',reference='Campaign semantic checks explicitly report source-marker normalization; no new stricter reference claim is introduced here.'))
(OUT/'NATIVE_CONTINUITY_FINAL_INTERPRETATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def f(x,n=3):return f'{x:.{n}f}'
lines=['# 原生R×S最终连续性解释：80格有界镜像独立核对','',
'本记录直接读取两个已完成campaign SUMMARY，以及80格各自的CANONICAL_SUPPORT_EVENTS和OBSERVED_LOSS_WINDOWS，共162份输入文件；逐文件SHA见同名JSON。没有导入冻结运行时/聚合器，没有GPU调用，没有修改论文或Root最终报告。派生重算V1的GPU-drain/CPU-SERVICE_END先后断言错误不作为神经trial失败：20+60个原神经格均为完成技术门，SLO失败继续留在表中。','',
'## 1. 五臂服务、成本与实际job库存','',
'每臂8个既有speaker×2fresh重复，全部offered为137.864125audio-s。R0=Ready-only、R1=Fullcall；S仅改变实际Consumer的兼容视图保留。Conservative/S1是独立无投机锚点。','',
'| 条件 | 信用s | 覆盖% | whole-run通过 | worker-s | 两板J | admitted ready复用 | unique promoted jobs |',
'|---|---:|---:|---:|---:|---:|---:|---:|']
for k in CONDITIONS:
 t=totals[k];lines.append(f"|{k}|{f(t['credit_audio_seconds'])}|{f(t['credit_percent'])}|{t['whole_run_passes']}/16|{f(t['worker_seconds'])}|{f(t['both_board_service_to_drain_J'])}|{t['Owner_admitted_ready_reuse']}|{t['unique_promoted_jobs']}|")
lines+=['','worker是实际job的host elapsed占用，非GPU-active时间。能量保持service-origin→外部确认physical-model-drain窗口；CPU SERVICE_END可以更晚，不能要求GPU drain必须在它之后。Unique promoted jobs按cell内唯一身份累计，不能自动称为同样多的model-active交接。','',
'Ready-only/S1实际命中1次完整结果库存，位于S0907；Ready-only/S0为0，其余source在Ready/S1也为0。结果证明新运行时的Ready路径确实被实际执行过；零命中格仍是有效策略结果，不以命中为正去选择性重跑。','',
'## 2. 连续性主结果','',
'| 条件 | 兼容ahead机会→保留 | 可避免/必要/unknown撤回 | 移除audio-s | 全体Gap | 同root可避免Gap | 同root必要Gap |',
'|---|---:|---:|---:|---:|---:|---:|']
for k in CONDITIONS:
 t=totals[k];lines.append(f"|{k}|{t['compatible_ahead_applications']}→{t['compatible_ahead_preserved']}|{t['avoidable_withdrawals']}/{t['necessary_withdrawals']}/{t['unknown_withdrawals']}|{f(t['removed_audio_seconds'])}|{f(t['total_gap_audio_seconds_x_wall_seconds'],6)}|{f(t['same_root_avoidable_gap_audio_seconds_x_wall_seconds'],6)}|{f(t['same_root_necessary_gap_audio_seconds_x_wall_seconds'],6)}|")
lines+=['','Gap单位均为audio-s×wall-s。机会是实际更新边界计数，不是去重view身份或自然发生率。两个S模式各自的闭环时序不同，例如Full/S0有10次兼容机会而Full/S1为9次，不能把它们逐事件强行配对。','',
'最直接的原生机制结果是：Full/S0有10次完整支持下的实际清除，Full/S1为0；同时Full/S1仍有2次必要撤回，全部来自S0902的两个重复。这支持“选择性保留仍合法视图”，不支持“R开启后ahead只会被追上、永不会被反驳”或“Joint无任何gap”。Ready/S0也有13次可避免撤回，Ready/S1为0，因此S效果不是R=1独有。','',
'首次信用上的S简单效应为R0处+0.500audio-s、R1处−1.000audio-s；四臂交互I=−1.500audio-s。连续性改善与首次信用小幅反向可以同时成立。不可将本轮说成正的期限信用协同，也不可因I为负抹掉实际10次兼容清除→0的连续性证据。','',
'## 3. 实际恢复时长分布','',
'所有39个下降窗均在同一root内恢复；0右删失、0边界截断。根据独立审计的canonical/private事件词汇，restored_within_same_root意味着实际恢复由Private应用产生，而非又一个Canonical事实。下面是观察到的事件时长，非总体分布/置信区间。','',
'| 条件/分类 | 窗口数 | min ms | median ms | mean ms | P95线性分位 ms | max ms |',
'|---|---:|---:|---:|---:|---:|---:|']
for k in CONDITIONS:
 for cls in ('avoidable','necessary','unknown'):
  d=distributions[k][cls]
  if d['n']:lines.append('|'+k+'/'+cls+'|'+str(d['n'])+'|'+'|'.join(f(d[key]*1000)for key in ('min_seconds','median_seconds','mean_seconds','p95_linear_seconds','max_seconds'))+'|')
lines+=['','S0清除后的可避免窗主要是几十到约百毫秒；这与Owner在Canonical后紧随发布Private snapshot的实际机制相符，不能写成每次都等待新的完整模型推理。前沿恢复不等于逐字文本恢复；有界窗口没有给恢复packet的publication ID或完整text/tip hash，故这里不作更强的消息身份断言。','',
'## 4. 两个具体见证','']
for number,w in enumerate((witness1,witness2),1):
 ev=w['support_event'];lines += [f"### 见证{number}：{w['cell_id']}",'',f"- 分类：{w['classification']}；完整边界：{ev['support_status']}；journal sequence={ev['journal_sequence']}，boundary job={ev['boundary_job_id']}。",f"- Canonical应用时，实际visible frontier由{w['before_visible_frontier']/16000:.3f}s回落到{w['after_visible_frontier']/16000:.3f}s，移除{w['initial_removed_audio_seconds']:.3f}audio-s。",f"- 原观察时刻{w['start']:.9f}→{w['end']:.9f}，在同root的Private应用后恢复覆盖；窗长{w['observed_duration_seconds']*1000:.3f}ms，面积{w['observed_same_root_area_audio_seconds_x_wall_seconds']:.9f}audio-s×wall-s。",f"- before tip SHA `{ev['before_tip_sha']}`；新Canonical SHA `{ev['new_canonical_sha']}`。完整路径绑定由原独立应用审计核验，metadata_binding_checked={ev['metadata_binding_checked']}。",'']
lines+=['见证1是一个真实S0兼容清除：保留计算并未自动保住已显示视图。见证2来自Full/S1：实际新Canonical否证旧预测边界，S1正确撤回，而非无条件维持单调显示。两个重复都在S0902的120000→112000样本位置出现该必要下降。','',
'## 5. 哪些来源有/没有S机会','',
'| Speaker | r0s0机会 | r0s1机会 | r1s0机会 | r1s1机会 | Ready/S0库存命中 | Ready/S1库存命中 |',
'|---|---:|---:|---:|---:|---:|---:|']
for row in source_results:
 t=row['conditions'];lines.append('|'+row['speaker_id']+'|'+'|'.join(str(t[k]['compatible_ahead_applications'])for k in CONDITIONS[:4])+'|'+str(t['r0s0']['Owner_admitted_ready_reuse'])+'|'+str(t['r0s1']['Owner_admitted_ready_reuse'])+'|')
lines+=['',f"四个因子臂合看，零兼容机会来源为{', '.join(zero_any)}；只看Full的两S臂，零机会来源为{', '.join(zero_full)}。这些零值描述本轮既定工作点，不证明策略普遍等价。",'',
'## 6. 对本轮证据价值的解释','',
'本轮确实在同一原生实现、同原任务/资源与现时控制面中同时测到了R和S：R提升首次期限信用，S选择性保留实际兼容ahead进展，必要撤回仍然存在。Conservative的同期信用、worker和能量锚点也全部有了实际测量。它连接了先前core与native分担的机制链。','',
'需要保留的实际权衡是：Full/S1比Full/S0少1audio-s首次信用，却消除10次可避免清除；它仍有两次必要下降。Relative资源比较应分别报告：Full相对Ready可减少重复工作，而相对Conservative会执行额外提前工作；不要把所有资源轴都写成共同严格支配，也不要从8个既有source推广自然发生率。','',
'这份解释不替代Root的最终V2执行/能量窗口重算门。V1错把physical drain要求晚于CPU SERVICE_END，是派生分析假设错误；它不把80次已完成的神经执行变成失败。完整输入SHA与逐事件记录均在同名JSON，供Root交叉复核。','']
(OUT/'NATIVE_CONTINUITY_FINAL_INTERPRETATION.zh.md').write_text('\n'.join(lines),encoding='utf8')
print(json.dumps(dict(status='PASS_INDEPENDENT_CLOSED_REPORT_CONTINUITY_RECOUNT',inputs=len(inputs),cells=len(cells),events=len(allevents),loss_windows=len(allwindows),stop_reasons=dict(restoration),zero_sources=zero_any,condition_totals={k:{x:totals[k][x]for x in ('credit_audio_seconds','avoidable_withdrawals','necessary_withdrawals','unknown_withdrawals','Owner_admitted_ready_reuse','unique_promoted_jobs')}for k in CONDITIONS}),ensure_ascii=False))

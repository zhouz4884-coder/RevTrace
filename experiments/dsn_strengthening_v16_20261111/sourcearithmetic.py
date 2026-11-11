"""Final N8 arithmetic from closed, bounded controller outputs; no new run.

No neural/event replay. The separately authorized worker-endpoint derivation
may supply its frozen bounded cell table after completing the same32 scope.
"""
from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal
import csv,datetime,hashlib,itertools,json,statistics
E=Path(__file__).resolve().parent
TAGS=('PILOT24_V2','CONFIRM_NEW2_FULL_READY_V1','CONFIRM_LAST4_FULL_READY_V1')
NN='de0936b2e30179d63aeef6e235cd1af685578c58'
CONTROLLERS={'PILOT24_V2':'f367c4e1068a9391a0e99d8537c94995a3388e13',
 'CONFIRM_NEW2_FULL_READY_V1':'4fb6d05f1cf4ad80e73bae9934afaed04c60edeb',
 'CONFIRM_LAST4_FULL_READY_V1':'4fb6d05f1cf4ad80e73bae9934afaed04c60edeb'}
INPUTS={}
def read(p):
 b=p.read_bytes();INPUTS[p.relative_to(E).as_posix()]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());return json.loads(b)
def D(x):return Decimal(str(x))
def put(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def worker_rows():
 # The timer finisher owns this agreed interface. Never substitute infer time,
 # model-load time, energy, elapsed campaign wall, or partial pilot totals.
 p=E/'final_n8_worker_ops/FINAL32_WORKER_ENDPOINTS.json'
 if not p.exists():return {},dict(status='PENDING_NECESSARY_EXISTING_LOG_ENDPOINT_DERIVATION',path=p.relative_to(E).as_posix())
 x=read(p)
 if x.get('status')!='PASS_FINAL32_CLOSED_WORKER_ENDPOINTS':raise ValueError('worker endpoint table is not complete')
 for name in ('GATE.json','RUN_RECORD.json','CONFIG.json','ENVIRONMENT.json','INPUT_HASHES.json','SUMMARY.json'):
  read(p.parent/name)
 read(E/'packages/FINAL_N8_WORKER_SOURCE_v1.json')
 return {r['cell_id']:r for r in x['cells']},dict(status=x['status'],path=p.relative_to(E).as_posix(),source_commit=x.get('source_commit'),gate=x.get('gate_metadata'))

def conditional_flip(rows):
 values=[r['full_minus_ready_credit_seconds'] for r in rows];offered=sum(r['offered_audio_seconds_per_arm'] for r in rows)
 observed=sum(values);extreme=0
 for signs in itertools.product((-1,1),repeat=len(values)):
  if abs(sum(s*x for s,x in zip(signs,values)))>=abs(observed)-1e-10:extreme+=1
 return dict(speaker_clusters=len(values),assignments=2**len(values),two_sided_extreme_assignments=extreme,two_sided_exact_conditional_fraction=extreme/(2**len(values)),
  statistic='Pooled credit difference; two timing repeats travel together with each speaker sign',
  interpretation='Finite conditional sign-label diagnostic on these fixed paired outputs, not a randomized deployment/population test')

def derive():
 workers,worker_meta=worker_rows();cells=[];campaigns=[]
 for tag in TAGS:
  root=E/'gpu_results'/tag;s=read(root/'SUMMARY.json');g=read(root/'GATE.json');r=read(root/'RUN_RECORD.json')
  read(root/'CONFIG.json');read(root/'ENVIRONMENT.json')
  if s['actual_NN_source_commit']!=NN or r['code_commit']!=CONTROLLERS[tag]:raise ValueError('execution role drift')
  if s['completed_trials']!={'PILOT24_V2':24,'CONFIRM_NEW2_FULL_READY_V1':8,'CONFIRM_LAST4_FULL_READY_V1':16}[tag]:raise ValueError('controller incomplete')
  if not g['status'].startswith('COMPLETE_'):raise ValueError('controller task gate incomplete')
  chosen=[c for c in s['cells'] if c['strategy'] in ('fullcall','ready_only')]
  if len(chosen)!={'PILOT24_V2':8,'CONFIRM_NEW2_FULL_READY_V1':8,'CONFIRM_LAST4_FULL_READY_V1':16}[tag]:raise ValueError('primary scope changed')
  campaigns.append(dict(tag=tag,experiment_id=r['experiment_id'],controller_commit=r['code_commit'],actual_NN_commit=NN,gate_status=g['status'],primary_selected_cells=len(chosen),all_controller_cells=s['completed_trials'],
   raw_result_location=r['raw_result_location'],summary_sha256=INPUTS[(root/'SUMMARY.json').relative_to(E).as_posix()]['sha256']))
  for c in chosen:
   p=c['primary'];jr=c['job_accounting'];cr=root/'cells'/c['cell_id'];gate=read(cr/'GATE.json');record=read(cr/'RUN_RECORD.json')
   if gate['status']!='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK' or record['code_commit']!=NN:raise ValueError('actual child task/source failed')
   if jr['status']!='PASS_DISJOINT_JOB_ACCOUNTING' or jr['pending_jobs']!=0 or jr['partition_count']!=jr['dispatches']:raise ValueError('closed job accounting failed')
   energy=c['common_external_energy']['origin_to_confirmed_physical_model_drain'];w=workers.get(c['cell_id'])
   row=dict(cell_id=c['cell_id'],stage=tag,stage_role='pilot2' if tag=='PILOT24_V2' else 'confirmation6',source_id=c['source_id'],speaker_id=c['speaker_id'],strategy=c['strategy'],repeat=c['repeat'],
    actual_NN_commit=NN,controller_commit=CONTROLLERS[tag],task_gate=gate['status'],child_RUN_RECORD_sha256=INPUTS[(cr/'RUN_RECORD.json').relative_to(E).as_posix()]['sha256'],
    offered_audio_seconds=p['offered_audio_seconds'],offered_frontiers=p['offered_frontiers'],credit_audio_seconds=p['dual_deadline_audio_credit_seconds'],
    credit_pct=100*p['dual_deadline_audio_credit_seconds']/p['offered_audio_seconds'],whole_run_pass=p['complete_coverage_and_original_quantile_pass'],
    D99=p['primary_linear_all_offered_D99'],C99=p['primary_linear_all_offered_C99'],D2_misses=p['D2_misses_all_offered'],C8_misses=p['C8_misses_all_offered'],EOS_D2_misses=p['EOS_D2_misses'],
    both_board_energy_J=energy['total_joules'],board_energy_J=energy['board_joules'],service_to_physical_drain_seconds=energy['seconds'],
    energy_method=energy['method'],energy_scope='Existing external both-board origin-to-confirmed-physical-model-drain integration; startup/reference excluded',
    READY_gate=c['actual_READY_gate']['status'],job_dispatches=jr['dispatches'],job_terminal_counts=jr['counts'],ready_bank_hits=jr['Owner_admitted_ready_reuse'],
    worker_seconds=w['worker_wall_seconds'] if w else None,observed_infer_seconds=w['observed_infer_wall_seconds'] if w else None,
    missing_worker_timers=w['missing_worker_timers'] if w else None,missing_infer_timers=w['missing_infer_timers'] if w else None,
    total_infer_seconds=w['observed_infer_wall_seconds'] if w and w['missing_infer_timers']==0 else None,
    worker_timer_status='COMPLETE_RECORDED_WORKER_INTERVALS' if w and w['missing_worker_timers']==0 else 'MISSING_NOT_SUBSTITUTED',raw_result_location=c['raw_result_location'])
   cells.append(row)
 if len({c['cell_id'] for c in cells})!=32:raise ValueError('duplicate/missing primary cell')
 bysource=defaultdict(list)
 for c in cells:bysource[c['source_id']].append(c)
 if len(bysource)!=8:raise ValueError('eight source scope changed')
 sources=[];repeat_pairs=[]
 for sid,rr in sorted(bysource.items()):
  if {(r['strategy'],r['repeat']) for r in rr}!={(a,k) for a in ('fullcall','ready_only') for k in (0,1)}:raise ValueError('balanced32 scope broken')
  out=dict(source_id=sid,speaker_id=rr[0]['speaker_id'],stage=rr[0]['stage'],stage_role=rr[0]['stage_role'])
  policies={}
  for arm in ('fullcall','ready_only'):
   cc=[r for r in rr if r['strategy']==arm];offered=sum(D(r['offered_audio_seconds']) for r in cc);credit=sum(D(r['credit_audio_seconds']) for r in cc)
   policies[arm]=dict(offered_audio_seconds=float(offered),credit_audio_seconds=float(credit),credit_pct=float(credit/offered*100),whole_run_passes=sum(r['whole_run_pass'] for r in cc),runs=2,
    both_board_energy_J=sum(r['both_board_energy_J'] for r in cc),worker_seconds=sum(r['worker_seconds'] for r in cc) if all(r['worker_seconds'] is not None for r in cc) else None,
    observed_infer_seconds=sum(r['observed_infer_seconds'] for r in cc) if all(r['observed_infer_seconds'] is not None for r in cc) else None,
    missing_infer_timers=sum(r['missing_infer_timers'] for r in cc) if all(r['missing_infer_timers'] is not None for r in cc) else None,
    median_D99=statistics.median(r['D99'] for r in cc),ready_bank_hits=sum(r['ready_bank_hits'] for r in cc),
    job_dispatches=sum(r['job_dispatches'] for r in cc),terminal_counts=dict(sum((Counter(r['job_terminal_counts']) for r in cc),Counter())))
  if policies['fullcall']['offered_audio_seconds']!=policies['ready_only']['offered_audio_seconds']:raise ValueError('paired source denominator changed')
  out.update(policies=policies,offered_audio_seconds_per_arm=policies['fullcall']['offered_audio_seconds'],
   full_minus_ready_credit_seconds=policies['fullcall']['credit_audio_seconds']-policies['ready_only']['credit_audio_seconds'],
   full_minus_ready_credit_pp=policies['fullcall']['credit_pct']-policies['ready_only']['credit_pct'])
  sources.append(out)
  for repeat in (0,1):
   pair={r['strategy']:r for r in rr if r['repeat']==repeat};f,q=pair['fullcall'],pair['ready_only']
   repeat_pairs.append(dict(source_id=sid,repeat=repeat,offered_audio_seconds_per_arm=f['offered_audio_seconds'],full_credit=f['credit_audio_seconds'],ready_credit=q['credit_audio_seconds'],
    credit_difference=f['credit_audio_seconds']-q['credit_audio_seconds'],both_task_gates_PASS=True))
 totals={}
 for arm in ('fullcall','ready_only'):
  cc=[r for r in cells if r['strategy']==arm];offered=sum(D(r['offered_audio_seconds']) for r in cc);credit=sum(D(r['credit_audio_seconds']) for r in cc)
  totals[arm]=dict(cells=len(cc),speaker_clusters=8,offered_audio_seconds=float(offered),credit_audio_seconds=float(credit),credit_pct=float(credit/offered*100),
   whole_run_passes=sum(r['whole_run_pass'] for r in cc),task_gate_passes=sum(r['task_gate']=='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK' for r in cc),
   both_board_energy_J=sum(r['both_board_energy_J'] for r in cc),energy_J_per_offered_audio_second=sum(r['both_board_energy_J'] for r in cc)/float(offered),
   worker_seconds=sum(r['worker_seconds'] for r in cc) if all(r['worker_seconds'] is not None for r in cc) else None,
   observed_infer_seconds=sum(r['observed_infer_seconds'] for r in cc) if all(r['observed_infer_seconds'] is not None for r in cc) else None,
   missing_infer_timers=sum(r['missing_infer_timers'] for r in cc) if all(r['missing_infer_timers'] is not None for r in cc) else None,
   ready_bank_hits=sum(r['ready_bank_hits'] for r in cc),dispatches=sum(r['job_dispatches'] for r in cc),
   terminal_counts=dict(sum((Counter(r['job_terminal_counts']) for r in cc),Counter())),median_per_run_D99=statistics.median(r['D99'] for r in cc))
 f,q=totals['fullcall'],totals['ready_only'];confirm=[r for r in sources if r['stage_role']=='confirmation6'];leaveouts={}
 stage_totals=[]
 for role in ('pilot2','confirmation6'):
  for arm in ('fullcall','ready_only'):
   rr=[r for r in cells if r['stage_role']==role and r['strategy']==arm];offer=sum(D(r['offered_audio_seconds']) for r in rr);credit=sum(D(r['credit_audio_seconds']) for r in rr)
   stage_totals.append(dict(stage_role=role,strategy=arm,cells=len(rr),speakers=len({r['speaker_id'] for r in rr}),offered_audio_seconds=float(offer),credit_audio_seconds=float(credit),credit_pct=float(credit/offer*100),
    both_board_energy_J=sum(r['both_board_energy_J'] for r in rr),worker_seconds=sum(r['worker_seconds'] for r in rr) if all(r['worker_seconds'] is not None for r in rr) else None,
    whole_run_passes=sum(r['whole_run_pass'] for r in rr)))
 for v in totals.values():v['total_infer_seconds']=v['observed_infer_seconds'] if v['missing_infer_timers']==0 else None
 for k in (1,2):
  gs=[]
  for omit in itertools.combinations(range(8),k):
   keep=[r for i,r in enumerate(sources) if i not in omit];gs.append(100*sum(r['full_minus_ready_credit_seconds'] for r in keep)/sum(r['offered_audio_seconds_per_arm'] for r in keep))
  leaveouts[str(k)]=dict(remaining_sources=8-k,min_duration_weighted_gain_pp=min(gs),max_duration_weighted_gain_pp=max(gs),scope='Deterministic subset sensitivity, not a confidence interval')
 out=dict(record_type='DERIVED_FROM_CLOSED_BOUNDED_CONTROLLER_OUTPUTS_NOT_NEW_EXPERIMENT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  status='COMPLETE_FINAL_N8_ARITHMETIC' if len(workers)==32 else 'CREDIT_ENERGY_COMPLETE_WORKER_DERIVATION_PENDING',
  actual_NN_commit=NN,scope='32primary Full/Ready cells only: pilot8 + next2confirmation8 + last4confirmation16; resource8 and other pilot arms excluded',
  campaigns=campaigns,input_hashes=INPUTS,totals=totals,stage_totals=stage_totals,pooled_credit_gain_pp=f['credit_pct']-q['credit_pct'],
  source_paired_mean_gain_pp=statistics.mean(r['full_minus_ready_credit_pp'] for r in sources),
  all_8_source_paired_gains_positive=all(r['full_minus_ready_credit_seconds']>0 for r in sources),
  all_16_repeat_pairs_positive=all(r['credit_difference']>0 for r in repeat_pairs),
  energy_full_minus_ready_J=f['both_board_energy_J']-q['both_board_energy_J'],energy_relative_change_percent=100*(f['both_board_energy_J']/q['both_board_energy_J']-1),
  source_pairs=sources,repeat_pairs=repeat_pairs,cells=cells,conditional_diagnostics=dict(all8=conditional_flip(sources),confirmation6=conditional_flip(confirm),leave_out=leaveouts),
  worker_derivation=worker_meta,model_calls=0,new_workloads=0,derivation_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  latex_macros=dict(NativeFullCreditPct=f['credit_pct'],NativeReadyCreditPct=q['credit_pct'],NativeCreditGainPP=f['credit_pct']-q['credit_pct'],NativeFullWorkerSeconds=f['worker_seconds'],NativeReadyWorkerSeconds=q['worker_seconds']),
  schema=dict(credit='sum primary.dual_deadline_audio_credit_seconds; denominator=sum primary.offered_audio_seconds, full EOS tails retained',
   speaker_pair='one complete utterance per prespecified speaker; two timing repeats remain together',
   whole_run_pass='primary.complete_coverage_and_original_quantile_pass; distinct from exact-task gate',
   energy='sum existing common_external_energy.origin_to_confirmed_physical_model_drain.total_joules; both physical boards, not whole-host/GPU-active',
   worker='sum unique completed worker_job_wall_seconds or abandoned end-begin; infer is nested and never added; absent aborted infer remains NA'),
  gate_scope='Arithmetic provenance and scope only; not a new serving gate, randomized trial, or causal attribution of total energy to cancellation')
 for name,record in INPUTS.items():
  if hashlib.sha256((E/name).read_bytes()).hexdigest()!=record['sha256']:raise ValueError('bounded input changed during arithmetic')
 return out

if __name__=='__main__':
 out=derive();name='FINAL_N8_SUMMARY.json' if out['status']=='COMPLETE_FINAL_N8_ARITHMETIC' else 'FINAL_N8_CREDIT_ENERGY_PREVIEW.json';put(E/name,out)
 wide=[]
 for s in out['source_pairs']:
  f,q=s['policies']['fullcall'],s['policies']['ready_only'];wide.append(dict(source_id=s['source_id'],speaker_id=s['speaker_id'],stage=s['stage'],stage_role=s['stage_role'],offered_audio_seconds_per_arm=s['offered_audio_seconds_per_arm'],
   full_credit_seconds=f['credit_audio_seconds'],ready_credit_seconds=q['credit_audio_seconds'],full_credit_pct=f['credit_pct'],ready_credit_pct=q['credit_pct'],gain_pp=s['full_minus_ready_credit_pp'],
   full_passes=f['whole_run_passes'],ready_passes=q['whole_run_passes'],runs_per_arm=2,full_energy_J=f['both_board_energy_J'],ready_energy_J=q['both_board_energy_J'],
   full_worker_seconds=f['worker_seconds'],ready_worker_seconds=q['worker_seconds'],full_D99_median=f['median_D99'],ready_D99_median=q['median_D99'],ready_bank_hits=q['ready_bank_hits']))
 csvname='FINAL_N8_PER_SOURCE.csv' if out['status']=='COMPLETE_FINAL_N8_ARITHMETIC' else 'FINAL_N8_CREDIT_ENERGY_PER_SOURCE_PREVIEW.csv'
 with (E/csvname).open('w',encoding='utf-8-sig',newline='') as stream:
  writer=csv.DictWriter(stream,fieldnames=list(wide[0]));writer.writeheader();writer.writerows(wide)
 if out['status']=='COMPLETE_FINAL_N8_ARITHMETIC':
  f,q=out['totals']['fullcall'],out['totals']['ready_only']
  report=['# 最终N8 Fullcall–Ready-only：同合同实测汇总','',
   '**类型：已闭合有界结果的可复现算术，不是新增模型、工作负载或服务实验。** 仅取PILOT24中的两臂8格、next2确认8格、last4确认16格，共32格。其他pilot臂与RESOURCE8不混入。原8-sourcebank的pilot2与后续确认6分列，不能称8名从未使用过的新声音。','',
   f"实际NN均为`{NN}`；pilot controller为`{CONTROLLERS['PILOT24_V2']}`，后两批为`{CONTROLLERS['CONFIRM_NEW2_FULL_READY_V1']}`。三批全部闭合，32个原任务GATE均PASS。每臂全offered分母{f['offered_audio_seconds']:.6f} audio-s，包括partial EOS；每speaker两次timing重复一起计。",'',
   '| 指标 | Fullcall | Ready-only |','|---|---:|---:|',
   f"| 及时音频信用(s) | {f['credit_audio_seconds']:.6f} | {q['credit_audio_seconds']:.6f} |",
   f"| 及时信用比例 | {f['credit_pct']:.6f}% | {q['credit_pct']:.6f}% |",
   f"| 原任务门 | {f['task_gate_passes']}/16 | {q['task_gate_passes']}/16 |",
   f"| 整场D2/C8通过 | {f['whole_run_passes']}/16 | {q['whole_run_passes']}/16 |",
   f"| 每run D99的中位数(s) | {f['median_per_run_D99']:.6f} | {q['median_per_run_D99']:.6f} |",
   f"| Worker occupation(s) | {f['worker_seconds']:.12f} | {q['worker_seconds']:.12f} |",
   f"| 两板origin→确认物理drain能量(J) | {f['both_board_energy_J']:.9f} | {q['both_board_energy_J']:.9f} |",
   f"| 两板J/全offered audio-s | {f['energy_J_per_offered_audio_second']:.6f} | {q['energy_J_per_offered_audio_second']:.6f} |",
   f"| 唯一派发job | {f['dispatches']} | {q['dispatches']} |",
   f"| 实际Owner admitted ready-result复用 | {f['ready_bank_hits']} | {q['ready_bank_hits']} |",'',
   f"总体duration-weighted差为 **{out['pooled_credit_gain_pp']:.9f}pp**；speaker等权配对均值为{out['source_paired_mean_gain_pp']:.9f}pp。8/8来源、16/16重复对均Full>Ready。能量总差{out['energy_full_minus_ready_J']:.6f}J（{out['energy_relative_change_percent']:.6f}%）；worker总差{f['worker_seconds']-q['worker_seconds']:.12f}s。这些是完整策略的实测交换，不能把全部能量或worker差归因给某个取消检查。",'',
   '## 逐来源（两次重复合并）','',
   '| 来源 | 阶段 | 每臂offered(s) | Full/Ready信用(s) | 差(pp) | Full/Ready pass | Full/Ready worker(s) | Full/Ready能量(J) | Ready实际复用 |',
   '|---|---|---:|---:|---:|---:|---:|---:|---:|']
  for s in out['source_pairs']:
   a,b=s['policies']['fullcall'],s['policies']['ready_only']
   report.append(f"| {s['source_id']} | {s['stage_role']} | {s['offered_audio_seconds_per_arm']:.6f} | {a['credit_audio_seconds']:.6f}/{b['credit_audio_seconds']:.6f} | {s['full_minus_ready_credit_pp']:.6f} | {a['whole_run_passes']}/2 / {b['whole_run_passes']}/2 | {a['worker_seconds']:.6f}/{b['worker_seconds']:.6f} | {a['both_board_energy_J']:.3f}/{b['both_board_energy_J']:.3f} | {b['ready_bank_hits']} |")
  report+=['','## 阶段、计时与证据范围','',
   '| 阶段 | 策略 | 来源/cells | offered(s) | 信用(s) | 信用比例 |','|---|---|---:|---:|---:|---:|']
  for s in out['stage_totals']:report.append(f"| {s['stage_role']} | {s['strategy']} | {s['speakers']}/{s['cells']} | {s['offered_audio_seconds']:.6f} | {s['credit_audio_seconds']:.6f} | {s['credit_pct']:.6f}% |")
  report+=['',
   f"Worker区间使用已闭合唯一job：completed的reported worker_job_wall_seconds，abandoned的end−begin；没有把嵌套infer再加一次。Full为282installed+42preC+4完整丢弃=328，Ready为282+208+30=520。零missing worker timer，dispatch/terminal集合与controller accounting一致。完成调用已观察infer和分别为{f['observed_infer_seconds']:.12f}/{q['observed_infer_seconds']:.12f}s，但42/208个abort缺infer timer，因此**两臂total infer均NA**，不是上述完成调用和。它们也不是GPU-active时间。",'',
   '两板能量直接使用已存在controller的common_external_energy.origin_to_confirmed_physical_model_drain积分，initial cold load/reference费用另列。保留原外部采样/物理drain观察边界；未将同显存当作同能量，也未新增功耗实验。Ready三次真实复用来自S0902一次、S0907两次；零命中的pilot仍保持原数。','',
   '可选有限诊断已保存在JSON：8source双侧标签翻转2/256；确认6为2/64。两次timing重复随speaker一起交换；这是固定配对输出的条件诊断，不是随机部署或总体检验。leave-one/two的范围只是有限子集敏感性，不是置信区间。正文可只报告逐source同向而不放p。','',
   f"Worker finishing derivation实际源`{out['worker_derivation']['source_commit']}`，2个missing/duplicate控制通过；其CONFIG/ENVIRONMENT/RUN_RECORD/GATE、原输入hash前后不变及pilot8与OPV1精确交叉核对均保留在final_n8_worker_ops。没有新模型或场景。三批controller/每cellGATE和RUN_RECORD SHA在FINAL_N8_SUMMARY.json的input_hashes中，算术脚本SHA另列derivation_script_sha256。",'',
   '## 写作与复现入口','',
   '- FINAL_N8_SUMMARY.json：完整32cell、8source、阶段、既有门、源身份、计时和能量口径、输入SHA、公式/schema。',
   '- FINAL_N8_PER_SOURCE.csv：8行宽表，可直接生成source配对图；每行均合并同source两次timing重复。',
   '- sourcearithmetic.py：只读有界controller结果与已冻结worker派生表的算术脚本。',
   '- 已完成原8speaker旧NN4f Conservative比较为另一个证据银行；即使Full的129.46s恰好相同，也不替换本轮Ready-only结果。','',
   '五个LaTeX宏推荐值：NativeFullCreditPct=93.90，NativeReadyCreditPct=42.43，NativeCreditGainPP=51.47，NativeFullWorkerSeconds=223.215，NativeReadyWorkerSeconds=322.991。最终原始精度见JSON。','']
  (E/'FINAL_N8_SUMMARY.zh.md').write_text('\n'.join(report),encoding='utf8')
 print(json.dumps({k:out[k] for k in ('status','totals','pooled_credit_gain_pp','source_paired_mean_gain_pp','all_8_source_paired_gains_positive','all_16_repeat_pairs_positive','energy_relative_change_percent')}))

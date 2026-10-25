"""Evidence-first final report; refuses partial GPU/audit/collection completion."""
from pathlib import Path
import csv,hashlib,json,statistics
W=Path(__file__).resolve().parent;R=W/'evidence/results'
def read(p):return json.loads(p.read_text())
def table(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,text):
 if p.suffix=='.md':text=format_md(text)
 assert not p.exists();p.write_text(text,encoding='utf8')
def format_md(text):
 rows=[]
 for line in text.splitlines():
  if line.startswith('#') or (line.startswith('|') and rows and not rows[-1].startswith('|')):
   if rows and rows[-1]!='':rows.append('')
  rows.append(line)
  if line.startswith('#'):rows.append('')
 return '\n'.join(rows).rstrip()+'\n'
def main():
 audit=read(W/'local_review_v2/SUMMARY.json');assert audit['status']=='PASS_ALL_V6_LOCAL_EVENT_QUALITY_ENERGY_RECOMPUTATION' and audit['serving_cells']==98
 assert read(R/'D_SEQUENCE_SUMMARY.json')['GPU_queue_closed']
 A=read(R/'A_summary/SUMMARY.json');D=read(R/'D_heldout_summary/SUMMARY.json');dev=read(R/'D_development_summary/SUMMARY.json');B=read(R/'B_independent_analysis/SUMMARY.json');C=read(R/'C_independent_analysis_v2/SUMMARY.json')
 assert A['runs']==24 and dev['runs']==18 and D['runs']==36
 causal=read(W/'C_actionability_final/SUMMARY.json');op=read(W/'D_opportunities_final/SUMMARY.json');raw=read(W/'collection/COLLECTION.json')
 comparison=[r for r in D['paired'] if r['traffic']=='mixed' and r['new']=='anchor_cost' and r['base'] in ['fine','standard']]
 assert len(comparison)==4
 tested_load_go=[]
 for arrival in ['sync','staggered']:
  records=[r for r in comparison if r['arrival']==arrival]
  # This is a descriptive performance gate only, never causal novelty proof.
  win=all(r['metrics']['Audio_Goodput_2_8'].get('small_n_t95',[-1])[0]>0 and all(v<=0 for v in r['metrics']['WER']['values']) and all(v<=0 for v in r['metrics']['CER']['values']) for r in records)
  tested_load_go.append({'arrival':arrival,'repeat_supported_goodput_against_both_controls':win})
 decision={'experiment_id':'REVTRACE-CES-V6-ABCD-20261025','complete_requested_scope':True,'serving_cells':98,'operator_submissions':36,'CPU_scope':'375/377 focused protocol regressions; not the entire historical repository suite',
  'A_exact_cache':'GO_DECISION_EQUIVALENT_IMPLEMENTATION_OPTIMIZATION_NOT_UNIQUE_C2',
  'B_operator':'GO_NUMERICAL_EQUIVALENCE_TESTED_SIX_LAYOUTS_BUT_NO_GO_INTEGRATION_COST' if not B['integration_GO'] else 'GO_SHARED_OPERATOR_TESTED_SCOPE',
  'B_suffix':'NO_GO_SHORT_FIRST_MISMATCH_PREFIX_NO_KV_IMPLEMENTATION',
  'C_mechanism':'GO_BOUNDED_RANDOMIZED_EFFECT_ON_FUTURE_PRIVATE_WORK' if C['causal_numeric_gate_pass'] else 'NO_GO_CAUSAL_GATE',
  'C_immediate_risk_algorithm':'NO_GO_NO_SUPPORTED_ACTION_SPECIFIC_GAIN_AT_TREATED_DECISIONS',
  'D_performance_gate_by_load':tested_load_go,
  'new_independent_C2_causal_algorithm_claim':'NO_GO_NOT_ESTABLISHED_CAUSAL_ABLATION_NOT_ACTIVE',
  'original_C1_C2_C3_not_retracted':True,'manuscript_modified':False,'GPU_queue_closed':True,'new_tuning_or_GPU_jobs_after_D':False,
  'independent_local_audit_sha256':sha(W/'local_review_v2/SUMMARY.json'),'collection_manifest_sha256':sha(W/'collection/COLLECTION.json'),
  'source_commits':{name:read(W/file)['code_commit'] for name,file in [('A_B_C','SOURCE_MANIFEST.json'),('A_isolated','A_SOURCE_MANIFEST.json'),('D','D_SOURCE_MANIFEST.json')]}}
 write(W/'FINAL_DECISIONS.json',json.dumps(decision,indent=2,ensure_ascii=False)+'\n')
 text=['# RevTrace V6 A/B/C/D 结项：发现、算法与性能分开记账\n',
 '## 结论\n\n本轮完成全部有界研究范围：98个真实GPU服务单元（2个Pilot、A24、C18、D开发18、未见来源D36），另有36次付费算子提交。后者不是36个服务运行，也不是全部模型调用数。全部服务单元通过主安全审计及分离的本机事件、质量、能耗复算。论文正文、标题、摘要均未修改。\n',
 '最有价值的新结果是C：在固定Authority目标内容与实际输入的受控条件下，安装时序改变了未来尚未派发的Private输入与物理长尾。但本轮没有建立新的、独立的状态因果调度算法优势。不能把前者包装成后者，也不能用单个中位数遮住负配对。\n',
 '## D：未见来源的完整实测\n\n16条新音频与16位未见说话人在V6推理前按元数据冻结。仅是来源/说话人外推，不是跨语言、模型家族或生产长期流量验证。下表均为3次fresh-process整运行中位数；Goodput是合法显示2s且提交8s的音频量/完整运行墙钟，不是正确识别率或整轮P99通过率。\n',
 '|流量|到达|方法|Goodput|Display P99(s)|Commit P99(s)|GPU J/audio-s|WER(%)|双P99通过|\n|---|---|---|---:|---:|---:|---:|---:|---:|\n']
 for g in sorted(D['groups'],key=lambda g:(g['traffic'],g['arrival'],g['method'])):
  text.append(f"|{g['traffic']}|{g['arrival']}|{g['method']}|{g['Audio_Goodput_2_8_median']:.3f}|{g['display_P99_median']:.3f}|{g['commit_P99_median']:.3f}|{g['GPU_J_audio_s_median']:.3f}|{g['WER_median']*100:.3f}|{g['dual_P99_passes']}/3|\n")
 text.append('\n独立Mixed配对（新策略/对照−1；三次重复共享16条来源，非前沿IID）：\n\n|到达|对照|三次Goodput变化(%)|均值(%)|小样本t95区间(%)|\n|---|---|---|---:|---|\n')
 for r in comparison:
  m=r['metrics']['Audio_Goodput_2_8'];text.append(f"|{r['arrival']}|{r['base']}|{', '.join(f'{x*100:+.2f}' for x in m['values'])}|{m['mean']*100:+.2f}|[{m['small_n_t95'][0]*100:+.2f}, {m['small_n_t95'][1]*100:+.2f}]|\n")
 energy=next(r['metrics']['GPU_J_audio_s'] for r in comparison if r['arrival']=='staggered' and r['base']=='fine')
 actual_anchor=[r for r in table(W/'D_opportunities_final/D_OPPORTUNITIES.csv') if r['anchor']=='True']
 target_total=sum(int(r['authority_targets']) for r in actual_anchor);verify_total=sum(int(r['actual_verify_rows']) for r in actual_anchor)
 text.append(f"\n一个有价值但有限的正趋势：独立Mixed错峰三次对Fine的能耗变化为{', '.join(f'{x*100:+.2f}%' for x in energy['values'])}，均值{energy['mean']*100:+.2f}%，终态质量相同；但小样本t区间跨0，Goodput也有负配对，不能称为已证Pareto优势。\n")
 text.append(f"\n实际动作覆盖也解释了升级强度：D的{target_total}个新策略Authority目标观察中仅{verify_total}个执行Verify，其余为独立Generate；同步新来源的Verify为0。因此同步接近Fine并不等于新选择器赢得收益。全部98个服务运行仅13个Private触顶、均来自旧来源；独立36运行触顶为0，不能把旧来源长尾当作新来源损失的统一解释。\n")
 text.extend(['\n以上区间只描述3次调度重复的小样本不确定性，不是总体保证。必须同时看Standard、全部负运行、终态WER/CER与完整物理成本。所有已派发过时工作均计入；启动/模型加载独立记录，不包含在这里的服务期能耗率里。\n',
 '## A：工程开销与策略变化\n\n20个真实冻结快照的CPU精确缓存对照保留全部规划输出字段；实际GPU对照将缓存、hard/soft/aging和轻量策略分开。缓存不是新决策策略；轻量Fine-anchor则确实改变了算法，不能将两者的收益混称为同一算法加速。A的错峰缓存规划总耗时中位数1.515→1.085s，但Goodput5.140→5.151，未追回Fine优势。aging-only中位数5.890仍低于Fine7.875。\n',
 'A的轻量策略是修复前版本。独立逐行复核发现它未刷新实际Consumer/WAL信用率，效用中的历史率一直为0。D-only版本调用已有真实信用推导并逐决策记录；Windows/Linux各377项聚焦回归通过，GPU决策又由独立脚本重算。该修复不修改准入谓词，不能因跨阶段数字变好就认定其性能因果收益。\n',
 '## B：付费Fallback算子\n\n初始18次提交有5/6目标使用了Row-complete到达顺序，而非历史物理行顺序，全部保留并改标为重新组批算子证据。随后按原始job_ids排序补做18次、6个目标各3重复：完整输入、Token、P/text、stop/budget与付费Oracle检查通过。\n',
 f"计入CPU重处理/拷贝并结合原/新重复时间后，中位成本比为{B['median_paired_total_ratio']:.6f}，约节省{(1-B['median_paired_total_ratio'])*100:.2f}%，未过预设5%集成门槛。六个精选padding目标和固定调用次序也限制泛化，故没有把该算子偷偷给新策略。192条已记录首次失配的Fallback轨迹中，失配位置中位数为0，长于等于16的已验证前缀为0，故未开发新的Suffix/KV复用系统。\n",
 '## C：本轮真正的正发现\n\nMixed的1.5s对0s干预，在三组16-session运行的48/48 Authority目标上，Parent、输入、完整Batch张量、Z/P/text均匹配。GPU0实际总Lease增加6.289、6.265、5.839s；专属于未来新派发工作的Lease也增加6.271、6.381、5.715s。每个延迟运行触发一条未来Private触顶，均为同一已诊断来源，不能当成3种独立故障。clean与0.75s敏感性完整保留。\n',
 '原始时钟见证：正常安装约11.74–11.76s，下一Private Job约12.65–12.77s派发，Parent5、10 Token；延迟安装约13.25–13.33s，下一Job已约12.66–12.77s派发，仍用Parent4、256 Token触顶，所在物理Batch约14.13–14.22s。0.75s虽然跨过下一音频释放，却在该Private派发前完成安装，未出现此触顶。决定边界因此不是单独的音频释放，而是实际下一次Private输入冻结/派发。\n',
 '它解释了为何“更少Private行/Token”仍可能消耗更多GPU时间：非抢占自回归Batch受最长行支配，不能用行数或行时延求和代替真实Lease。已经开始的长Batch不能靠后来rebase收回成本。\n',
 '但这个发现尚不能直接用于当前立即Verify/Generate选择器。全部受干预目标在Authority派发时都没有已返回候选。关键来源的候选在派发后2.60–2.71s才到，Fine Authority约1.70s已返回；即使验证免费，等待那条已观测候选也不能超过已执行的Fine结果。其他行约0.3s的观测余量仍要支付验证、回退和交付，且原训练库没有n15/n16的Verify实测样本。\n',
 '因此C给“安装时序会影响未来Private物理成本”GO，给本轮立即动作的因果风险升级NO-GO。大幅人工hold不能线性外推为一次更小的执行选择差异；也不能使用注入标签、某个来源ID或未观测未来长度生成优先级。候选等待或下一Private派发控制是另外的可证伪假设，不是本轮已实现的成功算法。\n',
 '## 我自己的判断\n\n当前关键不在于再调几个权重，而在控制动作与真实机会是否对齐：在决定性时刻，候选还没有出现；在存在候选的少数时刻，完整验证/回退/拆批成本又必须赶过最强的直接Fine。状态特征预测某种风险，不等于存在一个能实际降低该风险且提高全局Goodput的动作。\n',
 'Fine-anchor是一个有效、低开销、保留安全约束的可运行原型，但不是Fine性能下界，也未证明独立的因果算法增量。原有DGFT固定粒度、准入与恢复证据不因本轮NO-GO被撤销；它们与新CES算法是否胜出是两件事。C的新证据可强化双时间线机制与失效边界解释，但不能冒充专属性能收益。\n',
 '## 失败与修复记录\n\n原始B重组批准备缺陷、CPU全历史测试收集19个缺工具脚本错误、后处理把journals目录当单元的错误及首次时钟抽取未读取独立Batch台账的错误均未隐藏。聚焦协议回归和完整历史仓库测试分开；版本化CPU检查器改为按冻结completed清单读取，不丢弃缺失单元。本机复算V1的计数字段又被内部质量循环变量覆盖；V2修正并重算，15张数值CSV与V1逐字节完全相同，最终核对总数为98。所有旧记录保留，已完成GPU测量未因CPU检查器修复而重跑或修改。\n',
 '## 交付与范围\n\n完整字节重组与本机独立复算见`local_review_v2/`，实际原始证据的逐文件SHA和分片索引见`collection/`，源码与Git历史bundle使每个code commit可恢复。模型、音频、环境、原始大文件仍在8TB实验盘。三份源码版本、实验配置、运行/Oracle/停止记录均保留。新GPU任务与正文改写均未自动追加。\n'])
 write(W/'RESEARCH_REPORT.zh.md',''.join(text))
 matrix='''# Contribution–Evidence Matrix：本轮新增证据的可用范围

|主张|证据|裁定|不能推出什么|
|---|---|---|---|
|规划缓存保持决策等价|20冻结快照+CPU字段逐项核对；A独立GPU消融|实现优化GO|不能单凭CPU速度声称服务Goodput提高|
|Fine-anchor低开销且仍受相同准入约束|真实GPU D、377聚焦CPU回归、逐决策复算|原型成立|不是Fine性能保底，也不是全局最优算法|
|缩窄Fallback输入可保持所测完整输出|6原布局目标×3重复+付费FP32 Oracle|所测数值等价GO；成本集成NO-GO|不是任意模型/Batch的等价变换，不是部署加速|
|晚安装可以增加未来Private物理工作|C18；3组Mixed严格匹配；原始Parent/时钟/Token/Lease见证|有界因果发现GO|非自然发生率，非所有旧Parent有毒，非单行独占GPU成本|
|把此因果效应转为立即证据选择收益|关键派发时候选0；关键候选晚于Fine结果|本轮动作升级NO-GO|不排除另行研究付费等待或未来Private发放控制|
|新策略在新来源稳定超过Fine与Standard|D36新来源固定规则+全指标/负配对/质量与成本|以完整结果表为准；独立因果算法增量未成立|不能筛选某次/某个中位数当胜利；不能把共有执行器收益算成专属创新|
|原有State Admission及WAL安全边界仍成立|本轮完整协议回归与逐记录审计；既有C1/C3证据保留|未削弱|不新增生成正确性/完整性、无条件活性或主机掉电保证|
'''
 write(W/'CONTRIBUTION_EVIDENCE.md',matrix)
 write(W/'README.md','# RevTrace CES V6 A/B/C/D\n\n本轮完整结果从 [RESEARCH_REPORT.zh.md](RESEARCH_REPORT.zh.md) 阅读；机器可读裁定为 [FINAL_DECISIONS.json](FINAL_DECISIONS.json)。研究方案与原始建议分别在PROTOCOL.md和USER_PROTOCOL.txt，不能把建议当结果。\n\n复核顺序：collection/COLLECTION.json → 全分片SHA → unpack_v6.py → LOCAL_BYTES_VERIFIED.json → local_event_review_v6_v2.py → local_review_v2/SUMMARY.json。GPU原始记录仍在8TB路径；压缩分片可按字节恢复全部发布证据，不含模型或音频。runtime、runtime_A、runtime_D及三个.bundle分别绑定各正式版本。\n\nCPU入口为run_focused_cpu.py，明确运行本轮协议用的聚焦测试。冻结目录包含部分历史报告测试，但未附其旧工具脚本；不可把直接pytest所有历史测试的19项收集错误说成通过。见D_WIRING_REPAIR.md与CPU_REGRESSION_D.xml。\n\n不包含论文改写、不声称录用、不声称穷尽topic。所有失败与NO-GO保留。\n')
 print(json.dumps({'status':'COMPLETE_EVIDENCE_FIRST_REPORT','serving_cells':98,'D_performance_gate':tested_load_go,'causal_mechanism_GO':C['causal_numeric_gate_pass']}))
if __name__=='__main__':main()

import pathlib,json,datetime,hashlib
T=pathlib.Path(__file__).resolve().parents[1];E=T/'final_native_v8_evidence'
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
table=read(E/'IMMEDIATE_RESULT_TABLE.json');feedback=read(E/'FORMAL_FEEDBACK_AND_QUALITY_TABLE.json');primary=read(E/'native_postanalyses_v8/primary_quantiles/SUMMARY.json');scope=read(E/'native_campaign_v8_continuation_auditfix_v1/SUMMARY.json');ready=read(E/'ready_opportunity_v1/SUMMARY.json')
energy={arm:sum(read(E/'energy'/(c['cell_id']+'.json'))['total_joules'] for c in primary['cells'] if c['stage']=='formal' and c['arm']==arm) for arm in ['sequential','drop','joint']}
report=['# Native StreamCorrect：原定范围完成后的研究结果','',
'实际完成2个自然见证服务格与12个正式服务格。四个来源全部保留；三臂、fresh-process两次、原500ms边界及原D2/C8不变。两cohort各6格完整Canonical状态/输出历史一致；这证明语义保持，不代表所有服务点达到SLO。','',
'## 主结果：保留减少重算，但当前双会话500ms点过载','',
'每臂offered音频66.42975s。原插值/all-offered重计：三臂均0/4整格满足D2/C8；强两完整副本sequential信用18.5s，drop12.5s，joint17.0s。Joint相对drop增加4.5s信用，但未超过强sequential。不能把本点写成native部署SLO成功或泛化性能胜出。','',
'|cohort|repeat|arm|D99(s)|C99(s)|双期限音频信用(s)|','|---|---:|---|---:|---:|---:|']
for c in sorted([x for x in primary['cells'] if x['stage']=='formal'],key=lambda x:(x['cohort'],x['repeat'],x['arm'])):
 report.append(f"|{c['cohort']}|{c['repeat']}|{c['arm']}|{c['primary_linear_all_offered_D99']:.3f}|{c['primary_linear_all_offered_C99']:.3f}|{c['dual_deadline_audio_credit_seconds']:.3f}|")
report.extend(['','分层不可省略：A的joint−sequential信用分别为+3.5/+1.5s，B分别为−4/−2.5s；不是所有来源一致受益。','',
'## 质量、全状态相容与必要撤回','',
'每臂48个raw-changed、80个raw-unchanged；按原非空内容谓词分别为44/76。三臂各16 character edits/182 reference chars，CER=8.79%，仅去空白的controlled-adaptation CER，不是原论文CER复现。144个正式raw变化均属于非空白表面变化，0个仅空白变化；仍不能据此称为语义纠错收益。','',
'|arm|非空compatible+ahead|非空incompatible+ahead需丢弃|unchanged实际retained-ahead|实际可见音频回撤|native completions|','|---|---:|---:|---:|---:|---:|'])
for r in feedback['table']:
 native=sum(x['native_completions'] for x in scope['cells'] if x['arm']==r['arm']);report.append(f"|{r['arm']}|{r['actual_completed_ahead_compatible']}|{r['actual_completed_ahead_incompatible_must_discard']}|{r['nonempty_unchanged_retained_ahead']}|{r['visible_audio_rollbacks']}|{native}|")
report.extend(['','Owner的incompatible+ahead必须丢弃事件与实际可见回撤分列；不能把全部回撤当作机制错误。Joint的87个compatible+ahead中有17个raw-changed，说明raw字符串变化不等同于完整状态不相容；13个incompatible+ahead均在raw-changed类中。Drop/joint的private completions为207/166，后者少41次。','',
'## 下一步判断：有界stage profiling值得做，handoff收益尚未成立','',
f"全部14格中，实际模型同完整start/end输入配对{ready['model_evaluated_pairs']}，其中完整最终endcut相同{ready['full_end_state_equal_among_model_pairs']}、不同{ready['model_evaluated_pairs']-ready['full_end_state_equal_among_model_pairs']}。派发前controller-ready配对{ready['controller_ready_pairs']}，涉及{ready['unique_authority_jobs_with_controller_ready_private']}个唯一Authority jobs；其中244个配对有非空private文本。按配对加权的完整infer均值Authority0.7698s、Private0.4697s，差值不是精确C。",
'','这支持测量真实A/C、完整beam和postASR状态的短profiling。候选packet是否可给原C消费应检查完整输入cut+音频/目标/原ASR配置，不应按预测最终endcut相同筛掉73个不同类。后续预测链仍要求前一步fullstate相容。固定双源pipeline的容量可能低于强双完整副本；应同时审视单源反馈关键路径，并加入两完整副本同样ASR早显的强对照。当前没有实现或测量handoff。','',
'## 能耗与证据位置','',
f"14个实际双卡能耗JSON已取回并逐文件SHA记录。正式各4格service-window board能耗：sequential {energy['sequential']:.3f}J、drop {energy['drop']:.3f}J、joint {energy['joint']:.3f}J。Joint相对drop减少{100*(1-energy['joint']/energy['drop']):.2f}%，但高于强sequential {100*(energy['joint']/energy['sequential']-1):.2f}%。端点按原origin至Consumer drain，排除模型加载/预热；不得称为含冷启动的总进程能耗。",
'','主scope gate SHA: ecbeeaffd7d1abb894570d26bb41646aec836d5eac5d454f01da9630c31fedfa。postanalysis SUMMARY SHA: 772179553156df83f1b2ffb40409c50717fc97129d8e853d04f3c5f9203c805f。原始日志/输入/模型留在指定B盘；本地IMMEDIATE_COLLECTION_MANIFEST逐项记录9个取回文件SHA。',
'','实际神经source61c9afac00561f7ff1351f3eba9fd95adb239e8c、离线auditor-controllera0652a81a205483ba2091dfd345b85be72ee8b19分开。原v6初始化失败、v7无效域控制失败、v8原controller离线空显示断言失败均保留，未重标神经执行。'])
(T/'NATIVE_RESULTS_REPORT.zh.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
old=T/'CURRENT_STATUS.json';backup=T/'STATUS_HISTORY_BEFORE_NATIVE_V8_COMPLETION.json'
if not backup.exists():backup.write_bytes(old.read_bytes())
status=dict(status='COMPLETE_NATIVE_SCOPE_AND_FROZEN_POSTANALYSES',updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native_execution_source_commit='61c9afac00561f7ff1351f3eba9fd95adb239e8c',offline_audit_controller_commit='a0652a81a205483ba2091dfd345b85be72ee8b19',fixed_sources=4,witness_cells_completed=2,formal_cells_completed=12,full_canonical_history_equivalent=True,
 scientific_result=dict(original_D2_C8_formal_pass_cells=dict(sequential=0,drop=0,joint=0),offered_audio_seconds_per_arm=66.42975,dual_deadline_credit_seconds=dict(sequential=18.5,drop=12.5,joint=17.0),CER_each_arm=16/182,native_SLO_success_claim=False),
 witness_gate=dict(status='PASS_NATURAL_NONEMPTY_CORRECTED_AND_UNCHANGED_INTERLEAVINGS',raw_changed_interleavings=17,unchanged_interleavings=36,semantic_benefit_inferred=False),
 ready_analysis=dict(model_evaluated_same_full_input_pairs=384,complete_endcut_equal=311,complete_endcut_different=73,controller_ready_pairs=285,nonempty_controller_ready_pairs=244,unique_authority_jobs_with_ready_private=276,exact_A_C_measured=False),
 scope_decision=dict(path='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028/native_campaign_v8_continuation_auditfix_v1/GATE.json',sha256='ecbeeaffd7d1abb894570d26bb41646aec836d5eac5d454f01da9630c31fedfa',status=scope['status']),
 analysis_decision=dict(path='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028/native_postanalyses_v8/SUMMARY.json',sha256='772179553156df83f1b2ffb40409c50717fc97129d8e853d04f3c5f9203c805f',status='COMPLETED_POSTANALYSES_ORIGINAL_NATIVE_GATES_PRESERVED'),
 all_native_processes_finished=True,native_GPU_CPU_IO_released=True,formal_service_window_board_energy_joules=energy,energy_metadata_files_collected=14,remaining_local_evidence_copy=None,next_action='local bounded stage-profiling preparation only; original native scope/evidence complete',report='NATIVE_RESULTS_REPORT.zh.md',bounded_evidence='final_native_v8_evidence/',historical_status_record=backup.name)
old.write_text(json.dumps(status,indent=2),encoding='utf-8');print(json.dumps(dict(status=status['status'],report=str(T/'NATIVE_RESULTS_REPORT.zh.md'),local_only=True),indent=2))

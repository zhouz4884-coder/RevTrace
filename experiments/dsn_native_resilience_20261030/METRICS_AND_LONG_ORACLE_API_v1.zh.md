# 长状态与离线结果 API（实现就绪，正式NN尚未执行）

## 独立长流原任务参考

`source_dev/long_reference.py --plan PLAN --manifest SOURCE --out B_OUTPUT` 由root统一source冻结后运行。它先在同一已加载原FP32模型/同物理GPU上完成原始连续engine轨迹（每步只insert_audio→原infer→export，步间不restore），独立落盘后才进行逐边界serialize/restore full_step对照。两阶段均无early projection或推测，输入/C/U不改。原固定source0 1.5→2.0秒真实神经warmup后丢弃并重置；seed、线程、cuDNN/TF32与serving worker保持一致。

计划必须显式固定 `continuous_no_between_step_restore=true`、`per_edge_restore_comparison=true`、`failure_controls={same_input_adapter_repeats:2,original_continuous_prefix_repeats:1,first_failed_boundary_per_source:true}`。失败时执行这些同输入/原连续prefix诊断，不按输出换source或弱化比较。完整state/C/IDs与source marker均比较，不进行字段投影。完整DETAILS可很大，只在8TB上供campaign审计；按source分片与小DETAILS_INDEX支持bounded收集。参考时钟不能冒充serving指标。

两长流已在48个固定原clip全CRC/header/SHA通过后生成：S0770 228.51025秒、S0903 208.1003125秒，各24个原utterance、无额外静音/重采样/接缝reset或EOS。实际875个连续原步＋875个restore边对照。数据路径和SHA见 `../dsn_native_sustained_20261030/SOURCE_RECEIPT_v1.json`；IO释放见同family `DATA_IO_RELEASE_v1.json`。来源是合成连续输入，不称自然录音。

## 原生边界观测

`NativeStateObserver(engine,emit=...,history_limit=256)` 只委托原insert_audio/trim_context；调用 `bind(source_id,job_id,start_frontier,end_frontier)` 关联实际job。记录以 `boundary='audio_insert'/'context_trim'` 标识，不自带kind，Owner可包成 `kind='native_state'`。动态class描述符针对具体engine观测，copy.copy投影仍正确调用clone原方法，不会误绑原engine；多个engine独立，close恢复原方法。

记录移窗样本数、原函数最后removed返回、tokens/context/总decoder长度、实际trim变化和仍超界状态。完整FeedbackCut才是保真依据，这些counts/hash不能替代完整状态。recent deque有界，全部记录流式留8TB。19项development CPU包含无restore原路径、原EOS、全字段比较、observational保真、copy语义和Owner envelope。正式CPU/NN结论仍等待root统一实际source gate。

## 离线trial聚合

`resilience_metrics.analyze_trial(trialroot)->dict` 只能在trial结束后使用，写 `METRICS_SUMMARY.json` 与 `METRICS_GATE.json`，不覆盖Supervisor的根SUMMARY/GATE。根Supervisor可将返回值按自己的完成协议写入根SUMMARY。离线分析会按归档长度分配内存，绝不能将其作为在线控制面有界内存实现。

必要输入为CONFIG/ORIGIN/consumer.jsonl/facts.wal；能耗另需power.jsonl及明确 `SERVICE_END.json.service_end_perf`。原 `cell_metrics`、`analyze_cell` 与 `Power.energy` 直接复用；D2/C8、全offered、partial EOS、infinity规则都不改。磁盘JSON的GPU key恢复为int后进入原能量积分，服务区间包括所有故障/重算/冷恢复；只排除原origin之前首次加载，不扣除故障后加载成本。

可选固定参考为CONFIG顶层 `reference_details` / `reference_details_sha256`。`reference_kind='continuous_original'` 严格全字段；`'short_bdfa_static_source_mapping'` 只将contract.stage_execution.source_commit在原bdfa与实际commit之间静态映射，别的字段/C/IDs不能忽略。不提供参考时明确NOT_REQUESTED，root formal trial须require_reference；不能将结构检查代替固定原任务实证。

输出包含primary原指标和actual C50、fixed whitespace CER、actual-G全文后验支持、WAL父链/原cadence/record绑定、实际Consumer journal序号绑定、pending accepted与全部offered未完成量、history entries/RSS/currentCut/输出分列、原Canonical移窗与已选边预测簇。`legal_progress_wrong_rejections=None`有意等待独立实际转换checker，不凭完成任务就宣布零误拒。14个development CPU覆盖原端点、能量边界、完整参考/静态source map、错误Consumer引用、原clock重置、后验支持不替换信用、恢复时钟和意外Owner代码错误不得被最终完成隐藏。

恢复时钟优先用Supervisor直接fault_triggered，避免把Owner镜像事件重复计成故障；durable_sync receipt区分故障前旧持久事实。实际旧fact replay、新持久fact第一次消费、真实model_end在故障后且被认证消费均分别报告；旧replay不能冒充新推理。故障前accepted未认证债务与未来offered分开，pending不能直接宣称永久lost。replacementReady和durable replay可能交错，不强迫错误的顺序。

可见中断只称“低于故障前可见frontier的实际观察缺失时间”，不自动将必要不兼容修订归因于故障。未出现的marker保持unknown，不填0毫秒。真正admissibility、合法误拒和全路径消费支持由独立actual-log checker补充，不能借metrics的结构PASS声称整个Python/CUDA已形式化。

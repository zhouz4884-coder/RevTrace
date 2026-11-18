# 冻结最终重算源f29c2706：静态schema审阅

日期：2026-11-18。对象为analysis_source/final_recount.py，Git提交`f29c2706e365df86ea18eecbb048a8f635976d36`，源码SHA256 `049639048e933e1c334169e511496535b4f5b4be250881ed58ea38e688be806b`。仅静态读取源码、既有完整PILOT20摘要和原写入函数；未运行该分析程序、未生成80格最终结果、未运行GPU，未修改冻结分析源。确认批仍在执行，不把pilot当完整银行。

## 结论

**未发现会由当前实际PILOT20输出schema必然触发的阻断项。f29c源可保留，当前没有必须冻结V2的schema修复。** 必须在CONFIRM60完成和逐格镜像齐全后再正式执行。尚未镜像的逐格文件哈希/原配置相等只能届时验证，不能由本静态审阅代替。

## 1. Root指定的continuity别名问题：当前不会KeyError

源码遍历`stored['continuity_totals']`后用`t[key]`取独立和。实际pilot五个condition均只有以下9个key：

- avoidable_gap_audio_seconds_x_wall_seconds
- avoidable_withdrawals
- compatible_ahead_applications
- necessary_gap_audio_seconds_x_wall_seconds
- necessary_withdrawals
- removed_audio_seconds
- total_gap_audio_seconds_x_wall_seconds
- unknown_gap_audio_seconds_x_wall_seconds
- unknown_withdrawals

这9个key都存在于最终脚本total返回字段。driver的ADDITIVE白名单虽含right_censored_windows/boundary_truncated_windows，但实际continuity字段为gap_right_censored_windows/gap_boundary_truncated_windows；白名单不匹配导致它们未进入driver聚合，并未产生错误别名。因此当前不会触发KeyError。最终脚本直接从逐格continuity读取真正的gap_*字段，能够恢复截尾计数。

确认批使用同driver1bd3与audit0571、且脚本要求两个campaign的component identity完全相同，所以按现有冻结源码会输出相同字段族。如果未来更换source/schema，应作为新分析版本重新审阅，不应静默忽略未知key。

## 2. 实际pilot20结构读检查

本次仅针对20个既有完成cell做字段存在性/类型/绑定检查，不计算完整80格效应：

- 每个cell的COUNTS/AREAS字段齐全、类型及有限非负值符合脚本要求；缺失字段0。
- 五个R/S到underlying strategy映射与显式bool一致。
- semantic、actual_READY_gate、sampled_energy_ownership、job_accounting、worker_ledger和view_audit均为脚本期望的对象；原始state/C/IDs strict reference及NN11453433身份一致。
- 两板能量对象确实使用board_joules、total_joules、begin_perf/end_perf；board keys为字符串0/1。READY门确实有status，外部drain有confirmed_perf。
- job账有dispatches/partition_count/unique_promoted_jobs/Owner_admitted_ready_reuse，worker账有unique_jobs/missing_worker_timers/missing_infer_timers/total_infer_seconds。aborted infer缺测保持None。
- pilot CONFIG与本地冻结PLAN解析对象相等，其实际原始字节SHA与RUN_RECORD.frozen_config_sha256一致。
- 所有20份本地冻结config路径存在，并逐一匹配plan内config_sha256。

输入PILOT20 SUMMARY SHA：`51fa2c0ae280f0db15a72dae44d0c550a2061506183ee9fc3baf6cda6d1ff73c`。

## 3. 逐格文件key与原写入函数核对

- runtime/resilience_trial.py写GATE的status/source_commit/cell_id；resilience_metrics.analyze_trial写SUMMARY的gate和primary。原primary包含cell_id/arm/repeat，并追加EOS_D2_misses，因此脚本的EOS兼容分支不会误判当前schema。
- production_support/audit_results.py的EXTERNAL结果正是controller放进campaign SUMMARY的同一对象；原producer的gate字符串和selected_trace的PASS_COMPLETE_SELECTED_TRACE_REFERENCE与脚本一致。
- controller将accounting写入JOB_ACCOUNTING，worker原始账写入WORKER_TIMER_LEDGER，并把去掉per_job后的worker摘要嵌入result；脚本只比较共同字段，符合写入方式。
- audit_native_cell.py将相同result写到view_audit/SUMMARY，controller再将相同对象写INDEPENDENT_VIEW_AUDIT和嵌入campaign result；GATE含consumer_retain_views。脚本比较这三份对象及S flag的预期正确。
- 原reference gate/receipt字段包含reference_only/actual_serving_runs及新NN源；连续141、恢复282的字段名与脚本一致。

## 4. 解释层面的检查

- 全部80计划键齐全才产生最终结果；SLO失败、零机会、零效应和反向结果没有过滤分支。
- root-bounded可避免面积与全高水位面积分列，gap_scope保留，不把两者加成或命名成完整跨root G。
- 因子I、S/R简单效应和Conservative独立锚点的代数方向正确；source级求和守恒，与不同runtime旧数据隔离。
- sign枚举保留全部8来源及零效应；只标成固定配对输出的条件性描述诊断，没有把1410潜在事实比较当独立n。
- 输入路径/哈希及代码SHA记录的是独立汇总所读的报告，不冒称缺失raw Consumer/WAL已重新执行完整检查。

两个非阻断事项供Root注意：

1. `close`对绝对perf时钟也采用相对1e-7容差，时钟约2e4s时可容许约2ms；本数据的原始相等值能通过，但这不是严格微秒级时钟同一证明。若以后要更紧的时钟绑定，可单独绝对容差，不影响当前指标报告。
2. 默认E依赖脚本处在实验目录的analysis_source/review直系子目录；在当前本地镜像布局正确。若把脚本另行放到远端analysis_v1/source运行，冻结plans路径也需对应布局；预定本地执行不受影响。

## 执行后应做的最小核对

先确认20/60都Complete并镜像清单齐全，再运行冻结源一次；核对FINAL SUMMARY80/8/5/2和每条件137.864125s/282前沿、当前同runtime保留/串行能量、unknown/censor字段及全部source反向点。若最终缺文件或哈希不符，补齐镜像或排查对应源记录，不能靠删除cell继续。

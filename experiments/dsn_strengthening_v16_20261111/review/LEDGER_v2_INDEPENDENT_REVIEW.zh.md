# Ledger v2：独立只读复核

审查对象：分析source `817ebbbabce15e6d9c2d84f8435bbbc8640d8b22`、manifest SHA `6993b20a88435db68fbe393a01d2c96da1145d7a177a43b050636707dd635300`，以及 `history_ops/results/LEDGER_v2` 的JOBS/SUMMARY/晚discard时序。6个源文件与manifest逐bytes/SHA相符；本次没有重跑正式实验、读取新音频/转录、调用模型或修改旧source/结果。

**接受数值与主要解释；有一项正文时间戳名称应收紧，不需要重跑。** SUMMARY SHA复核为`f45f76636321933a08ce7f1fd98a554bfccbbb67bea424b256be8416c0d7f9ca`。

## 接受：92个job的父确认前区间与单位

独立从JOBS重算 `max(0,min(end,parent_boundary)−begin)`，全部92项与输出相同，求和差0：

| 原观察区间交集 | parent terminal receipt边界 | parent install receipt边界 |
|---|---:|---:|
| worker区间逐job求和 |22.428635673597455|24.487471990287304|
| infer同步墙钟逐job求和 |21.865506775677204|23.924343092367053|

92项的顺序都满足 `worker_begin ≤ infer_begin ≤ parent_received ≤ parent_install_receipt ≤ infer_end ≤ worker_end`，且92项`native_model_evaluated=true`。完整冻结start与真实selected parent完整end绑定由reader明确检查。因promotion自身没有原timestamp，receipt→install日志是保守的应用边界区间；不能把两端任一戳当精确promotion瞬间。

单位应称**跨job累计的worker/infer墙钟秒（job-seconds）**。它们是观察到的前缀区间总量，可能跨两个物理worker重叠，不是episode经过秒数、独占GPU算时、GPU busy积分或已经节省的资源。完整69.016526秒worker全程不能替代22.428636–24.487472秒的确认前前缀。

## 接受：24个abandon缺infer timer，不是零ASR

JOBS中24项均`ASR_prefix_executed=true`、`original_infer_wall_s=null`；异常路径跳过完整infer record，worker仍含已执行ASR和同步/清cache。不得称“神经模型前拦截”或“神经0”。

SUMMARY的`original_infer_wall_observed_s=0`是对空的已观察timer集合求和，旁边`infer_timer_missing_calls=24`；不能用它表示实际infer成本为0。后续表/计算必须显示NA/unknown并保留missing_count，不需要为修正展示而改写这个冻结JSON。已完成报告表当前写“不可确定”，可接受。

## 接受：23.779是固定重启假设的代理

逐job代数重算得23.77908689621836秒：

`parent_install − child_infer_begin − (child_worker_end − child_infer_end)`。

其中92项post-infer导出尾部累计为0.14525619614869356秒，即23.924343092367053减该尾部。它假设同infer时长、立即重派/获槽并忽略真实重启restore/排队等；不是实测完成延迟的因果节省。92次求和也不是单episode关键路径收益。5.1067588同样只是完整调用worker成本构成比，不是取消带来的效益比。

## 应收紧：j16的上界是produced_perf，不是实际发送完成或C入口

原bdfa `source_snapshot_v3/candidate_bridge.py:22–32` 顺序为：现有 `before_corrector` hint检查→capture/projection/serialization→`produced_perf`→`on_asr`（worker补sent_perf并results.put）→原学习C函数。故ledger取到的 `asr['produced_perf']` **位于现有检查点之后**，是该检查点的严格时间上界；并非检查点本身、IPC发送完成或精确C-entry。

parent j15 infer结束分别比该produced上界晚6.738500ms/70.529654ms，完整parent证据更不可能提前可用。因此可接受的否定结论是：**仅把同一合法proof更快下发，无法赶上原实现已经经过的那一个检查点；这两例不是已经定位的hint下发bug。**

建议把报告“原ASR发送时刻”改为“ASR投影/序列化完成的produced_perf（在原检查点之后）”，并把“合法before-C点”明确为“原实现现有before-C检查点”。本证据不排除未来在publication之后、真正调用C之前增加另一个合法轮询点；该点无精确旧标记，不能声称它一定能救下两例，也不能声称所有可能before-C检查都已经被否定。合法C中途取消、等待或再轮询均是不同策略，须另付成本并单独验证；不建议为这项文字收紧追加实验。

## 五臂设计能检验什么

* RevTrace vs safe UIR只改变已发起工作的cooperative早停提示；完整输入分类、实际parent AU、durability与SUP都共享。它能检验**现有合法早停的增量服务/资源效应**；相同结果不能证明使用前输入验证多余。必须同时报告实际hint机会/到达点、废执行占用和后继实际进展，否则没有处理强度时不能将tie解释成机制普遍无用。
* Ready-only vs RevTrace检验Owner已有完整结果复用是否足够，以及保留在飞合法调用的条件性增量；须按已冻结Owner receipt/install序号定义，不能从旧ready=0推新策略等价。它不支持“任何系统都必需RevTrace”的普遍必要性。
* dependency-versioned对比只能在真实祖先失配/后续完整输入收敛等分歧机会中识别两策略差异；直接handover同效时应报告机制同效。strict-birth辅助臂不能冒称全部版本策略或Retire复现。
* unsafe UseAll的CPU反例展示去掉AU后可以产生错误parent转移，不是一个被允许的online exact性能臂，也不是自然发生率。共同守卫在五臂里始终保留，因此五臂没有“删除输入资格的安全部署”估计量。

设计足以进入原定pilot检验上述条件性问题；没有理由额外增加镜像CPU控件来累积数量，也不能在新GPU结果前把区间前缀或proxy宣称为必要性/性能胜利。

## Metadata许可与当前工作顺序

`METADATA_SOURCE_CHOICE_v1`记录官方页面/归档Usage的表述差异，但没有规定用户审批、联系作者、付费或暂停合法原样非商业benchmark的流程；不应由此新增permission gate。原WAV不变、研究来源与条款保留。当前audio下载HOLD来自root明确要求先制定header census与冻结metadata选择，而不是该报告自行推导出的许可审批。无需再向用户问许可；本次仍未下载audio。

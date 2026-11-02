# 实现前只读审查记录

日期2026-11-02；对象为本轮`history`及`cost/source_dev`工作源，尚非冻结运行结论。无模型、reader、重计器或测试执行；未改被审源。以下位置随实现agent整理目录可能移动。

## 历史分析

已读`history_analysis.py`的完整选择/原Consumer映射/时轴积分/首期限/输入门，以及`CONFIG.json`、`reference_view.py`和`reference_kernel.py`相关apply入口。

### 已发现并由实现agent修复、随后只读确认

1. **最终EOS/零时长应用遗漏。** 原版仅在正duration piece内保存deadline snapshot，最后一行`start=end=global_end`因此可能将真实EOS certified coverage判为无穷。现工作版把所有原应用snapshot放在积分循环前，包含最终EOS和同timestamp应用，并独立统计zero-following-duration，修复方向正确。
2. **RECEIVE→APPLY之间的host结果漏入proof universe。** 原版按receive时点构造core全部父节点集合，却按稍后的actual observed时点开始给duration信用；两者间到达的完整结果可能产生额外父歧义而被忽略。现工作版在point和piece均使用`received<=actual APPLY`，candidate仍必须已Consumer登记，修复方向正确。不存在实际锁/原J snapshot记录时，不能把较早receive集合说成actualapply时的完整支持集合。

### 保留为结果范围/建议的检查

- 原baseline应重现frontier/text外的原contract、owner/session epoch、certified P/Z/transaction、mode字段；缺失字段列覆盖/UNKNOWN，不能生成。已有strict原event消费是有效基础，但“完整baseline reproduction”的报告措辞应与实查字段对应。
- 当前char计数命名为`at_original_apply_cuts`是合适限定。额外host/retirement切点改变可选择集合，不自动是实际Consumer新apply；不能把该字符数叫完整连续新策略实测UI修改量。
- 观察horizon取全attempt最后globalConsumer事件，最后source窗口右删失。它是global-prefix状态保持范围；若要称每source实际持续体验，建议另报same-source最后cut裁剪敏感性，或明确其上界性质。不得在尾部无限外推。
- `core_apply_check`将真实root/已收完整jobs放入受限reference state并调用原`apply-request/view-applied`，适合证明此cut的完整view通过原core谓词。它没有重放全Owner调度、每个原publication ticket与所有生命周期，不能报告成原完整runtime端到端精化。
- `legacy_registered_canonical_point_opportunities`和强化joint duration应分列。新增generation/core限制可能合理排除旧native-positive cuts，原14点不能成为强制凑出的expected正面积。

## 成本实现

已读`cost_probe.py`、`trace_cost.py`、`cost_runtime.py`、`observed_trial.py`及`PLAN_AND_SCOPE.zh.md`。

范围基本可接受，没有发现要求停止冻结的语义错误：原4f独立clean source导入；wrapper不改安全谓词/return/exception；Owner自身spawn-safe安装；完整receive/EL/ownedbind/commit、FactStore、whole-viewConsumer及实际fsync有分层span；只扣同线程child形成exclusive；原模型不patch。观测器RAM记录/元数据的span外成本仍进入off/on端点，Owner批量export早于原SERVICE_END的事实也被明确记录。

结果应分三账，不能相加后命名全协议税：

1. 真实NN里current完整路径span；
2. CPU使用原完整对象、实际fsync的FactStore/Consumer重放；
3. `REPLAY_COMPONENT.full_input_materialize_and_equal`及ownedbind独立probes。

第三类没有原Owner动态history/队列占用，不是Owner实际EL分布；第二类也不重建调度或服务clock。新16格off/on测**观测器总系统影响**。同4f安全协议两臂都执行，不能称移除全部协议后的因果tax。

建议记录exclusive负残差被clamp为零的计数，便于检查嵌套账本；这不是在无异常证据下要求阻止冻结。最终source/test/manifest/环境/资源gate由root与实现agent负责，本审查没有代跑或声明其通过。

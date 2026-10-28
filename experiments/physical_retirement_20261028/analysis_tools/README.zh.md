# 独立服务聚合工具

`aggregate_service.py` 只读取冻结计划、单 cell 的 SUMMARY/FREEZE/RUN_RECORD、独立审计 JSON，以及实际 Consumer 和选中 Canonical 历史。它不导入 policy、scheduler 或 GPU 库，也不运行推理。`source_v2` 未被修改。

## 使用

在能访问原始 8 TB 结果的机器上运行：

```text
python aggregate_service.py --plan SERVICE_PILOT_v2_CONFIG.json --output 新的聚合目录
```

计划内的原始绝对路径可直接使用。若已将整组 cell 复制到本地，增加 `--results-root 本地目录`，按各 cell 输出目录名定位。`--additional-plan 另一冻结计划.json` 可重复，用于同一数值／输入／来源／到达／rho／repeat 合同下的跨计划强对照；同名方法不足以建立配对。不同输出根的合并推荐在远端直接使用原始绝对路径。

输出目录必须是新的。`ANALYSIS_RECORD.json` 记录脚本哈希、计划哈希、实际读取文件的字节哈希、Python 环境和各执行源 commit。

## 输出与解释

- `COVERAGE` / `BLOCK_COVERAGE`：每个计划 cell 与配对 block 的完成状态。失败、缺失、deferred audit 全部保留。修复后的旁路审计不能把旧失败 cell 改写为正式成功。
- `RUNS`：全部 offered 音频／frontier、2s/8s 信用、实际 P99、质量、两 GPU 能耗、冷启动成本、取消和物理占用。未观察到的 frontier 保持 miss；不做有限值过滤后报好看的百分位数。
- `SOURCE_METRICS` / `SOURCE_PAIRED_EFFECTS` / `FRONTIER_PAIRED_EFFECTS`：每源、每真实 frontier 的对照，列出新增信用与失去信用、实际停顿变化。受控故障的 other-session 组由冻结 fixture 预先确定，不依据策略运行后的好坏挑选；这只是分析分组，不是 policy 输入。
- `FACTORIAL_EFFECTS`：对每个 cohort × adapter × arrival × rho × repeat 完整 block 计算 `Y11 - Y10 - Y01 + Y00`，同时报告条件主效应。没有四个已审计 arm 就不生成交互。
- `SOURCE_FACTORIAL_EFFECTS` / `SPEAKER_BOOTSTRAP`：按 speaker 聚类，同一人的 deadline windows、重复与多次计算不增加独立 N。primary、paired-jitter、coarse 各层分别报告。若源级端点缺失／无界，不删除该 speaker 后计算有限 CI。GPU 工作与能耗是共享 batch/run 成本，不能虚构逐源能耗的 bootstrap。
- `STANDARD_POSITIVE_CONTROL`：完整 Standard 与 R1_S1 的替代实现正控；同效是可接受结果。
- `CANONICAL_HISTORY_GROUPS`：按实际 Authority runtime 合同、来源、模型、rho、arrival 分组的完整 `F/Z/P/text` 序列哈希。排除时间和 job ID；先报告是否同史，不强求所有实验同史，也不隐藏差异。
- `SOURCE_REGISTRY`：源与 speaker 的实际复用次数。H3 的 24 个 speaker 不会被报告成 110 个 cell、重复次数或 thousands of windows。

实际 Consumer 回撤来自相邻 `valid_visible_frontier`，不是 first-coverage 高水位记录。回撤面积积分 `max(历史已见最高前沿 - 当前可见前沿, 0) × 持续时间`，嵌套回撤不重复计费。文字修订按实际相邻文本的公共前缀计算擦除字符。canonical-triggered、可信前沿推进、明确 tentative-invalidated 等元数据分别列出；标签不足时不自行判定撤回是否合法或是错误。

## 性能效果 gate

先要求同冻结输入、原期限、真实 Consumer、可信选择合同、输入义务和独立安全审计；缺失或失败的强对照不能消失。随后看实际服务端点：全 offered 双期限信用／goodput，及其他合法会话的真实停顿与进展。取消次数、较少 token、缩短的失效窗口本身均不等于服务价值。

这里不临时规定 5% 或其他任意幅度门槛。先列出配对效应、重复方向、源／cohort 分布、质量和代价，再决定下一阶段。单个配对只能支持机制／价值小试；重复同向、超出本组可见抖动的改善可以支持进入强对照，仍不足以宣称独立来源的总体优势。端点出现相反变化会标记 `OBSERVED_SERVICE_TRADEOFF`；这是保留真实取舍，**不是要求每个微小计时差都不得回退的自动 NO-GO**。

parent/watchdog 取消时可能还有合法贡献，与实际丢失已证实的合法完整结果，是不同事实。本工具不会用 parent 变化、target ahead、取消计数或最终输出缺失来自动判为错误取消／浪费。若需要丢失结果的证据，必须另有同实际模型输入的完整对照与当前链兼容见证。

验证：`test_aggregate_service.py` 的 **12 个 CPU 测试通过**。这些测试验证聚合语义，不是研究性能数据。

## 已经读取的真实结果

- 旧 v1：读到了 runner rc=0、审计失败的原始 STOP/GATE，聚合保留为未被正式接受；见 `real_pilot_v1_status/`，没有得出算法失败或性能胜利。
- 正式 v2：4/4 cell 完整审计通过，已经读取实际结果并聚合；见 [real_pilot_v2_v4/SUMMARY.json](real_pilot_v2_v4/SUMMARY.json) 和 [PILOT_v2_FINDINGS.zh.md](PILOT_v2_FINDINGS.zh.md)。此处才有真实服务层面的有限结论。

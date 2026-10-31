# 仅读图表冷读审查 v1

范围：只读指定的两张 PDF_PAGE 图、当前 main.pdf 第7–10页的图表/表注，以及对应 TeX 中的 figure/table 环境与 tables/native_reliability.tex；忽略正文段落。不读项目历史、原始统计、项目报告。本审查只判断图表能否传达收益对象及结论边界，不判断数据真实性或录用前景。

总体判断：图表足以支持“联合保留减少可避免的前沿撤回”和“更多已提供音频及时呈现与选定模型输出相同的整段内容”。它们不支持“识别准确率提高”“总能更快”“过载或故障下SLO已通过”。主要剩余风险是聚合口径、正控身份及 Pass 的样本单位没有完全自包含。

## 1. 四臂的身份与2×2聚合口径

矩阵是两个因素的四种组合：

| 图内名称 | Computation R | View S | 冷读可确认的角色 |
|---|---:|---:|---|
| Recompute | Off | Off | 两种保留均关闭的基线 |
| View only | Off | On | 只保留视图的消融 |
| Compute only | On | Off | 只保留计算的消融 |
| RevTrace | On | On | 两者联合的完整方法 |

图注另提一个 separate positive control；它不在上述四个矩阵格内。仅读图表不能得知该正控的名称、实现或具体变化，不能把 View only 或 Compute only 自动称为正控。

四格大数分别是累计前沿撤回次数12、1、17、0；下方654.115、628.435、664.150、680.760 s是满足 display 2 s / certified 8 s 时限的累计音频覆盖。每臂共同分母为714.110 s，图内写明 three cohorts。这是每臂跨三个 cohort 的合计，不是单次运行点，也不是把714.110 s乘以三。图注没有自包含地定义24-speaker stratum与三个cohort的对应关系或独立性。

RevTrace的零前沿撤回与最高累计及时覆盖不等于整次通过：图注明确四个矩阵臂及另列正控都失败于 whole-run D2。零撤回也只表示前沿没有回退，不保证文本从不修改。

## 2. 内容堆叠图的收益对象与Pass单位

Matched与Resident是两个分开的bank，每个bank每个policy提供66.340 audio-s，均来自四个已有来源。分母是所提供音频时长，不是字符数、词数、更新次数或请求数。

- 深蓝：及时覆盖，且在相同音频前沿处，所显示的完整文本与该前沿实际选定的模型输出事后一致。
- 斜线：及时覆盖，但不满足上述整段文本一致。
- 浅灰：未满足及时覆盖的音频，即至少一个显示/认证时限未达到。

因此，这三个比例是“音频时长 × 时限 × 选定输出一致性”的划分，不是相对于人工转写的识别准确率。蓝色增加支持“相同选定内容更早达到时限内”，不能支持选定模型输出本身更正确，也不是直接展示平均延迟下降。

图上Matched的深蓝占比从33.9%到76.9%，及时但不一致从11.3%到22.3%；Resident对应为36.2%到75.8%、10.6%到20.9%。剩余浅灰是截止未覆盖；RevTrace的小浅灰尾段未标数。显示值有四舍五入，不能要求每行标签严格加到100.0。

Matched的6/8是trial pass。表II明确每个policy为四个来源、每来源两个fresh trial，且通过要求同时满足整次D2/C8；不是6/8说话人。Resident的7/8是request pass，不是trial pass或说话人通过率。图注只写“retain their original criteria”，不足以让只看图表的人复述Resident的请求级通过规则；也不能据8这个分母推断有8个独立声学来源。

## 3. Fig.1(b)能与不能说明什么

计算保留臂在1.444 s首次完整显示12–14 s区间，1.544 s撤回，3.720 s恢复相同文本，覆盖空缺2.176 s。RevTrace在2.027 s首次显示同样完整文本，比前者晚0.583 s，并超出D2约27.4 ms；之后没有再出现14 s覆盖空缺，3.794 s的选定更新还保留了更靠前的16 s视图。两者认证均满足C8。

可说：“在展示的RevTrace执行中，首次完整交付后保持了该区间的覆盖。”不可说：“Fig.1(b)首次交付更快”或“已因果证明它避免了(a)同一事件的2.176 s空缺”。图注已声明是两个独立实际执行、有不同交错；这是相同输入区间的执行对照，不是同一事件轨迹的配对反事实，也不支持所有执行都无空缺。

## 4. 故障表的零违规与SLO

表IV标题与caption已清楚分开合法性和时限：24个短trial全部零illegal installation；但worker/owner故障四类条件下，两种policy的D2/C8 pass均为0/2。No fault和Duplicate / late下RevTrace也只有1/2，Conservative为0/2。Reject / ΔC中的4 / 0表示拒绝了消息且未引起选定状态变更，不表示服务成功。

New result测的是从故障到实际认证消费一个新事实，其call在故障之后完成；不是旧事实重放时间或替换进程就绪时间，也不能仅凭这个单列判断整次SLO。表支持故障隔离合法性保留，不支持故障SLO通过；“零违规=可靠性全通过”是错误读法。

## 最多四项局部修复

1. **2×2聚合和正控范围不够自包含。** 图内three cohorts与caption的24-speaker、positive control (15 runs)相距较远，15可能被读成正控自身运行数。短修复：写明“Each cell sums three cohorts; 714.110 offered audio-s per arm”，并明确正控名称及“four matrix arms + one separate control, three runs/cohorts each, 15 total”（若这是实际设计）；把“All fail whole-run D2”放到矩阵下方可见位置。
2. **内容图标题和蓝色可能被当成准确率。** “The same content arrives sooner”比图中实际测得的及时匹配占比宽。短修复：标题改为“More selected-output-matching audio meets the deadlines”，图注加“audio-time fractions, retrospective agreement, not transcription accuracy”，给小浅灰尾段补值或明确由100%减得。
3. **Pass列跨两种样本单位，标准仍依赖正文。** 短修复：把Matched标题改为“Matched trials (4 sources × 2 repeats)”，Pass列分别写“Trials passing D2/C8”和“Requests passing [explicit criterion]”，并在caption直接写Resident请求级判据，替换“retain their original criteria”。
4. **示例图容易被当作速度提升或同事件反事实。** 短修复：在Fig.1(b)的首次交付标注旁直接加“later first delivery; no later coverage gap in this run”，caption保留“different executions/interleavings”，并补一句“not an event-matched counterfactual”。不用再引入新的对比数据。


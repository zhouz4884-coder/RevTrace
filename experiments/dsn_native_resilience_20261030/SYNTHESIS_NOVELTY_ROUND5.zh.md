# RevTrace 的单一主张与本轮收束判断

分析时间：2026-10-30。这里只读当前正文、完整正式 short28 汇总与其只读索引、独立六格开发轨迹检查、有限规格模型和完整长流参照。没有运行 NN，没有操作远端、CURRENT、正文或图。本文件不是正式 36 格终门；online8 和全 36 独立轨迹检查尚未完成。short28 的 `illegal_installs` / `legal_progress_wrong_rejections` 仍为 unknown，不能从 runtime PASS 推成零。

## 1. 最值得保留的中心发现

**在原始纠错程序递归决定下一次推理输入的服务里，预测是否正确，不是一个能同时决定计算、选择和可见进展的布尔量。完整调用的输入可以后来被确认合法，而它自己的下一状态预测仍然错误；这项调用的继续执行，也不自动保护 Consumer 已经消费的整个临时假设。**

因此，RevTrace 最有竞争力的单一主张是：围绕不改变的原始反馈任务，以保留原身份的完整输入和真实依赖路径，分别判定计算是否仍有资格、整个可见假设是否仍受支持；原 C/U 继续决定所选输出，持久接纳和物理释放继续遵守各自边界。这个组合把可复用工作转化为可持续的合法服务，而不是只多算一些 token。

这比“我们有 R、S、K 和恢复四个机制”强，也比“我们证明了一种新的通用事务算法”准确。依赖复用、读集校验、写前日志、去重与 fail-stop 恢复本身都有成熟先例。新意应放在原 C/U 反馈递归下的具体复用对象、两个不可混用的见证，以及它们在实际 Consumer 和原选择语义之间的组合。

主张可由三类反例推翻，而不是依赖赢某一组加速比：

1. 一个被确认并接纳的完整调用，实际输入不是其所选父 cut，或者其纠错选择并非原完整 C/U；这会破坏所选任务语义。
2. 一个新认证根与整个 ahead 假设有真实依赖支持，但该应用仍将其撤掉；这会破坏条件式连续性。
3. 迟到消息、恢复重放或旧 physical incarnation 获得了新写入权，或者确认输入义务/原到达时钟被抹去；这会破坏同一协调协议在失效时的含义。

这些性质不意味着全会话文本单调，也不意味着所有负载下联合臂更快、更省电或都满足 D2/C8。

## 2. 当前证据如何闭合，而不是相互冒充

| 要回答的问题 | 最有用的真实证据 | 可以推出什么 | 不能推出什么 |
|---|---|---|---|
| 为什么计算端保留还不够？ | 24-speaker、三 cohort 的原 R×S；R 单开 withdrawal 17，双关 12，联合 0；另有完整 2 秒区间先准时出现、后兼容消失的实际事件 | 计算保留与持续可见服务之间存在真实协调缺口；这是单边方案不足的反例 | R×S 在任意时序下有正交互；这些数值是新 native 4f 源码的结果 |
| 原纠错程序能否保持？ | bdfa 四个未用 speaker 的 272 完整转换、92 个正在运行的提升调用，其中 20 个自身预测结束状态错误 | 确认当前完整输入足以保留原 C/U 调用，不要求其未来预测全部正确；有可测的服务机会 | 一条祖先失配后再收敛的自然 NN 发生率；改良了原 ASR 准确率 |
| 同一机制遇到失效是否仍有意义？ | 4f 正式 short28：同一组双策略、相同持久化/恢复/Consumer，原任务完成，包含实际 worker exit、partial IPC、durable 前后 Owner 终止、duplicate_late | 强顺序对照也有完整恢复能力时，测试的是组合协议是否守住原任务和实际交付，以及代价 | Full-call 比保守策略恢复更快；runtime PASS 已证明所有独立语义计数为零 |
| 长时间状态迁移是否使 cut 失真？ | 4f 连续原引擎 875 步 + 每步从原始 start 恢复的 875 次完整调用；完整状态/C/IDs 全等；真实 buffer shift 398/357、context change 353/252 | adapter 在真实状态边界上的闭合性有独立原始参照支持，避免“两个都依赖 restore 的路径互相证明” | 自然连续录音质量；每个前沿都有新 decoder 输出；长流服务期限或总 RSS 恒定 |
| 协议历史是否随旧工作无限积累？ | 待完整 online8 的真实 active closure、terminal/pinned、audit/window/outbox 观测及独立重计 | 在这些运行中检验相对活依赖的条目界，并与模型状态/累计输出分开 | 两条合成流是 48 个独立会话；总内存严格常数或无限时长活性 |
| 为何可以相信拒绝与恢复的语义？ | 手写有限规格模型 20,305 状态、36,941 边、27 命名控制；实际六格 c4 检查；随后全 36 实际检查 | 条件式归纳命题、有界反例控制与实际调用来源互补 | 自动抽取了所有 Python/CUDA 行为；有限状态总数是部署故障率 |

新故障实验最重要的意义不是又取得一项速度胜利，而是把“保留合法工作”落到可执行的授权、选择与物理生命周期上。特别是：已经接纳的完整 buffer 保持原 producer 身份，与接收新的旧 incarnation 消息不同；durable 后尚未安装的原事实可重放，与新 NN 进展不同。这两种区分会使论文比安全检查与正常态加速的堆叠更完整。

这仍需按实际事件分母写作：六格开发 c4 的 compatible-ahead application 和 closed-buffer 安装均为零。若全 36 审计仍没有对应事件，前一个性质的实际自然见证只能归给旧 bdfa 来源，后一个性质只能由当前代码/CPU 控制/有限规格支持，不能借“同一故障协议”把它们升级成已经观测的 NN 事实。

## 3. 必须进入解释的当前负面结果

short28 的六个主条件每臂各两次 fresh，不能挑最好的一次。正常 Full-call 的 D99 为 1.798–2.053 秒，只有 1/2 次通过原 D2/C8；另一次只有 EOS 尾部 D2 miss。duplicate_late 同样为 1/2 次通过，另一条 D99 为 2.079 秒。它仍优于正常顺序对照的 4.069–4.170 秒，但没有显示稳定的 D2 裕度。旧 bdfa 的 8/8 完整通过是那个冻结实现的结果，不能替 4f 的持久化/恢复扩展承诺期限。

worker 故障后首次新模型结果被实际认证消费为 1.762–2.251 秒，而所有 worker 故障整轮 D2 仍失败、C8 通过。这里可能是幸存 worker 继续产生工作；replacement-ready 无真实标记时保留 unknown，不能叫冷替换 NN 已准备好。Owner durable 后终止时，旧事实重放约 1.357–1.810 秒；真正新推理认证仍为 83.898–104.439 秒。durable 前终止的新进展为 64.612–108.081 秒。Owner 各格原双门均失败。本文不应靠“快速恢复旧事实”暗示恢复了实时推理。

S0908 的各格相同最终所选任务具有 17 个 introduced code-point occurrences、1 个撤回、16 个最终可见 codepoints；正常 Full-call 的 8.000–8.259 秒音频 credit 中 4.000 秒首次覆盖文本未变。因此前沿 credit 不应改名成新增正确文字。

长参照 post-trim 的 L≥448 有 340/36 次；原 decoder 还有 `L<448` 循环门。它说明部分原任务前沿不会再进入 decoder 循环，不是已经发生位置嵌入越界。长流论证应该承担“原任务状态闭合与协议持续运行”的角色，而不是长语音准确率广告。待 online8 后同时报告原模型最终 CER、实际文本变化/不变 credit 和调用类型，不能只展示漂亮的音频覆盖曲线。

## 4. 正文选择和 11 页预算

建议正文按一个因果链排列：实际兼容丢失 → 完整输入与完整 view 的两个见证 → 原 C/U 的输入确认 → 所选轨迹/持久化/物理边界 → 逐层证据。不要将 failure、long、GC 又写成三个同等篇幅的新算法贡献。

保留的主图表：

* 首图保留实际 2 秒完整区间的消失与返回。它让审稿人理解为何 first-delivery deadline 不等于持续服务，强于仅列 17/12 的事件总数。正文可将数字叙述压成 3–4 句，完整时刻留图。
* 原 R×S 主表保留，Full composition (ours) 必须仍是自建完整组合正控；它可以同效，不需要被人为做弱。该表回答组合义务，不承担恢复收益。
* 48 格工作区间图保留全部点和 c12 负面边界。c12 的长段门槛/逐重复数值可缩成两句：全部整轮 D2 失败、未取得预定完整非 EOS 区间见证，故停止搜索；详细门槛与 1/1/3 窗口数放 artifact。不能把探索中点伪装成预先冻结全部网格。
* native 四未用 speaker 表保留。将正文重复表中 credit/C50/energy 的段落压缩，保留“92 提升中 20 个自身预测错误、原 272 转换完整一致”和自然兼容/必要撤回的明确小分母。开发 69/276 的冗余统计和 10/162 重复 CER 可在 artifact，主文用独立声学分母 5/81 即可。
* 正式 short28 用一个紧凑全条件表：六行，固定顺序 Conservative/Full-call；任务完成、独立非法接纳/错拒、真正新结果恢复时钟、D2/C8、能耗。若列太多，能耗区间移入同一机器表，正文仅强调正常节省和故障非普遍节省。最终独立审核未出前，非法项保持 unknown。
* long 用一张简洁二或三 panel 图，不把每个 counters 填满。最低需要协议 live/pinned/terminal 的真实墙钟轴、原 offered-frontier D/C 延迟和实际文本变化/未知标记。模型状态/累计文本与 Owner RSS 可作为第三 panel 或机器表；`L≥448` 区域必须可辨。历史与 RSS 的横轴必须覆盖 input end 后的实际 drain，不能截到合成流终点。

优先压缩的内容：

1. K24 作为执行支撑，约一短段足够：释放后 96 行确实被消费并有同前沿整文本支持，但只有部分切换期限，R×K 交互/能耗不稳定。留同步/错峰收益符号和真实 drain/ACK 区分，逐个毫秒数、两套 deadline 行数不必全部主文出现。
2. 不再用主文详细复述旧 CK5/recovery 源码、84/1154 等编号。当前正文已较好地压缩；继续保持来源说明即可。
3. native 的 180/14/166 全部 LCP 数字可移 artifact；保留 exact-G support 29→51.518 秒、14.822 秒不支持和 unchanged credit 即可，这些直接限制服务含义。
4. 已有 2-source saturated capacity 的负面结果应保留一句准确边界，不必保留多个 kJ 小数或把不同比较的 warmup/Consumer 写成长历史。不能把独立链顺序对照说成全系统饱和吞吐优势。
5. Related Work 已能覆盖关键差异；避免为 DSN 共性增加不相关 DSN 引文。SSBD 已同时有复用与显示处理，所以不能宣称第一次把计算与显示放在一起。差异应落在原选择递归反馈、完整状态/调用对象和 whole-view root 应用上。

可用的一段方法定位（不是新增实验结论）：

> RevTrace does not require a provisional call to predict its own corrected output correctly. It requires that the complete input actually consumed by the call later become the selected parent state. This establishes execution eligibility; original correction still determines the output. A second witness governs the Consumer's complete visible hypothesis. The protocol preserves these identities through durable selection and physical failure, so retaining work neither grants it selection authority nor silently revokes an already supported view.

## 5. 本轮之后是否继续开 NN 实验

若固定 online8 和全 36 独立轨迹/端点/内容/历史检查完成，且没有出现语义反例或条目界失守，我建议**停开新 NN 横向分支，转完整正文与 release**。理由是当前最重要的证据缺口已经被明确限定为：同一最终源码的拒绝/失效链与持续状态边界；不是再找一个更好加速点。再重复调 D2 附近某个 EOS 点，会引入新的参数选择与 source version，只能改善小范围 timing margin，难以再改变中心科学发现。

仍有强理由继续实验的触发条件只有实质反证：独立检查发现非法所选边、误拒合法继续义务、恢复丢失原输入时钟，或 protocol 未引用历史持续无界。这时应按同输入/重复/合法原 oracle 诊断，不能通过删除失败格收束。若失败源于原模型长时 decoder/质量机制而双方同样保持原任务，则应将该负面结果解释为适配和部署边界，不顺手训练新模型或更改原 C/U。

这不是声称论文已经达到所有可能研究的上限。是判断本轮固定贡献的高价值可证伪证据链，在当前实现与时间范围内已足以进入严肃写作。DSN 的竞争力最终来自问题是否值得、见证是否清楚、原任务是否保持、失败和服务代价是否可审查；不会由实验文件数量或主表是否每项都赢来决定。

## 本次只读来源

* `Paper_DSN/revisions/20261030_resilience_progress/main.tex` 及其现有各节，尤其 03_continuation、03_native_extension、03_native_refinement_working、04_protocol、05_native_retention、05_execution_only。
* `FORMAL_SHORT28_V1_RESULTS_v1/SUMMARY.json`；`SHORT28_READONLY_METADATA_INDEX_v1/MAIN24_CONDITION_ARM_AGGREGATES.json`、`REGRESSION4.json`。该索引复制原完整 summary，不是 raw 语义重计。
* `../dsn_native_refinement_20261030/FORMAL_MODEL_RESULTS_v3.zh.md`；`SHORT_ACTUAL_TRACE_RESULTS_v2.zh.md`。
* `LONG_REFERENCE_RESULTS_v2/SUMMARY.json`；长 decoder 行为的解释沿当前原源代码/计数定义，不扩大成新的 forward 探针或自然数据结论。

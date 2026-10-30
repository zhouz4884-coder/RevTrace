# 长流全阴性后的研究取舍

2026-10-30；只读本地正式八格 SUMMARY 及各 cell 的主端点、quality 小字段、history 和 state-boundary 摘要。未读出/转储巨大 final_text，未操作 NN、远端、CURRENT、正文或图。全 36 独立 c4 检查仍在进行，以下不会把原 runtime/reference/Consumer gate PASS 写成非法接纳为零。

## 结论先行

这次结果**撤掉了 native 实现可持续提供实时、可用长语音服务的支持**，不能仅解释为很小的 timing margin 或少数 EOS miss。它没有推翻完整输入/整视图见证的合法性主线；反而把“忠实执行原程序”与“原程序提供了有用服务”明确分开。主文应将长流降为**受控状态与历史压力测试**，完整性能/内容图放 artifact。不要把 61.5 对 15.0 秒的少量信用差包装成长流胜利。

在决定停实验前，真正值得看的不是多补一个速度点，而是全 36 轨迹检查是否已经把**核心保留对象与物理 producer 失效**连成一条实际 NN 链。如果没有，这一条定点机制见证比更多长流性能调参更值得补；如果已有，则无需新 NN，进入正文和完整 release。

## 当前实际事实与含义

* 两个受控 PCM 拼接流长 228.51025 秒和 208.1003125 秒，各有 24 原始 utterance；它们不是自然连续录音。两臂各两次 fresh，共八格；每臂重复计的 offered 分母为 873.221125 秒、1,750 前沿。
* 八格均完成各自原任务/reference/实际 Consumer 检查，原在线 Canonical 边合计 3,500。独立连续原引擎 875 步与从每个完整 start 恢复的 875 次调用，在完整状态、原 C 和返回 IDs 上全等。这支持 adapter 的状态闭合，不支持任意 GPU 行为等价定理。
* 八格原 D2/C8 整轮门全部失败。D99 最小 449.727 秒、最大 502.952 秒。Conservative 总信用 15.0 秒，Full-call 为 61.5 秒；后者也仅占 offered 音频约 7.04%，前者约 1.72%。不能只报约四倍的相对比值而隐藏两个都不可用的绝对服务水平。
* 两源最终 CER 分别为 3,103/486=638.477% 和 1,313/522=251.533%，各臂及重复相同。CER 超过 100% 是大量插入等编辑的合法计数结果，不是百分比计算错误。这是这个固定长时原任务的退化，而不是 RevTrace 改写所选结果得到的性能收益。
* 连续参考中确实跨越 398/357 次 buffer shift、353/252 次 context change。post-trim L≥448 的 340/36 次意味着原 decoder 的 `L<448` 循环不再进入；不能把这些前沿称为新解码内容，也不能称为已经触发位置嵌入越界。encoder、原选择和 update 的工作仍需按其实际调用类型区分。
* 摘要中 Full-call 活跃 job 最大为 2、node 最大为 2–3，Conservative 各为 1；Owner RSS 的实测范围和模型 cut、累计 text、预载音频分别存在。这里仍要等完整 terminal/pin/audit 独立重计，不能只凭少数摘要 maxima 宣布所有 GC 界已证明，更不能声称总 RSS 常数。

同样的原选结果，以及独立连续原参照的一致性，使“状态 restore 漏字段把原任务改坏了”缺少当前证据支持。退化发生在固定无 VAD、多 utterance 拼接且不中途 reset 的任务本身。但这仍不等于完成了退化根因的因果分解：人工拼接/会话合同、原软 trim 与 decoder 门、纠错递归都可能参与。不能把某一个观察直接写成唯一原因。

## 对创新主线的实质影响

最强主张继续是：完整调用的输入可被后续原选择确认，即使它自身的下一状态预测错误；计算资格与 Consumer 整假设支持要分别判断，同时不授予预测输出新的原选择权威。R×S 的反例、未用 speaker 的原 native C/U 忠实执行与服务机会，仍然成立。

应撤掉或避免的主张包括：

* 以新长流说明当前 native 组合已经可部署到 always-on 连续语音；
* 以零原任务差异暗示准确率良好；
* 以完成 3,500 个前沿暗示产生了 3,500 次新的 ASR 解码或有用文字；
* 以 Full-call 长流 credit 略好说明可以解决持续过载；
* 以两个构造流说明自然长语音中的兼容机会或故障频率。

这也提醒写作不要把所有贡献放在最终单个 native 实现的实时性上。核心 R×S 实验提供协调缺口及其相对推进条件；native 实现提供在原反馈程序上的具体可执行见证；失效与持续状态试验检验该实现的边界。三者互补，但不会合并成一个超出各自条件的部署承诺。

## 主文与 artifact 如何分配

建议主文保留一个约 140–180 英文词的段落，位于最终 native 故障表之后，标题可用 `Controlled sustained-state stress`。必须同时给出：

1. 两个构造流、八次实际运行的 scope；
2. 连续原参照 875+875 与完整在线任务一致性，真正跨越状态边界；
3. 全八格不满足原服务门，D99 的绝对数量级；
4. 两源巨大原任务 CER，说明其不是可用长语音运行点；
5. 协议历史界与模型/累计输出内存分开，完整图与计数在 artifact。

主文不需要再为这组实验安排四 panel 全宽性能图。那张图既耗掉接近半页，又容易把“越过状态边界”和“可部署服务”混淆。如果 root 认为 GC 图是 DSN 论证必需，最多保留一个小 panel：原墙钟上的协议未引用 terminal/audit 条目与活依赖，覆盖 input end 后 drain，并在 caption 明确所有运行的期限和质量失败；其余延迟、模型状态、RSS、内容/unchanged-credit、能耗全部在完整 artifact 图中可审查。图上不截断最差延迟，也不以不同口径单独突出 Full-call。

可用英文正文草案（最终 c4 数值出来前不加入非法接纳计数）：

> We additionally stress the adapter with two constructed streams of 24 concatenated utterances, lasting 228.510 and 208.100 seconds without intermediate resets. A continuous original-engine reference and 875 separately restored calls agree on complete state, correction and token IDs. The eight online runs reproduce all 3,500 reference transitions across actual buffer and context changes. This is a state-stress result, not an operating service point: every run misses the original D2/C8 gate, with display P99 of 449.727–502.952 seconds. Both policies retain the original task's severe degradation, with CER of 638.48% and 251.53% on the two streams. Complete-state fidelity therefore does not imply usable transcription or timely service. The artifact reports every run's content, delays, energy and protocol-history measurements separately from current model state, cumulative output and RSS.

其中 `reproduce` 指原任务/reference gate，而非已经通过独立 c4 语义审核；若读者可能误读，可写 `match their complete fixed references`。没有必要在摘要加入这组长流的 credit 数字；摘要仅说测试 sustained-state 边界即可。

## 还有什么值得补，什么不值得现在补

### 有实质价值的条件式补充

等待全 36 c4 的**真实事件分母**。若仍没有以下实际 NN 链，当前故障试验更多说明通用恢复协调器可工作，而非直接说明核心保留对象在失效时仍有价值：

`真实完整条件结果已登记/真实 ahead view 已消费` → `producer 物理退出且旧 channel 封存` → `原输入后来被所选父 cut 确认` → `原 job/birth/incarnation 不重签` → `旧完整 buffer 合法安装或受支持 view 继续保留` → `实际 Consumer 新进展`。

这是一条值得补的定点机制见证。可以使用先前已有的 development 输入，不冒充新的独立 acoustic confirmation；必要时只在明确声明的 controlled timing fixture 中短暂停顿 Owner commit，让完整结果先到，再杀 producer，随后解除停顿。原 C/U、输出选择、完整输入、原到达钟和期限不变。重点是原始收据能证明这条链，不是让 Full-call 在故障速度上压过强基线。若同样路径已在当前八个长流或 28 个短流中出现，就不要为另一遍截图再运行。

这项建议不是要求立即启动：先检查实际事件，然后确认现有 fault API 能否表达；若需要大幅更改运行时或找输出碰运气才能触发，则 CPU/规格范围应坦陈，而不把它扩展成新的机制工程。

### 当前不值得做的“修复”

* 再调长流 chunk、期限、token cap、删掉坏尾部或选另一条输出；这些会改变本次任务/分母，无法修复现有证据。
* 给原 corrector 训练新模型，或改原 C/U/trim/循环门来让 CER 变漂亮；这是另一项 ASR 研究，且失去当前固定原任务的依据。
* 仅因 Full-call 在兼容性差时浪费调用，临时发明自适应阈值/切换器；这可能改善资源消耗，但在原任务质量已不可用时，未必改变本文的中心科学发现。已有原始调用、取消、能耗可先离线诊断，不应将离线理想切换当部署结果。
* 用会话 reset 后的漂亮结果覆盖此无 reset 任务。自然 VAD/用户明确端点可以形成合法而实用的新 adapter 合同，但必须有真实状态表示与独立原程序参照，另列为新合同；不是本次失败的就地修补。

若未来要把 native always-on 连续语音本身作为论文中心，一个采用原作者实际分段/端点行为的有用长录音验证会有价值，也不必更改 C/U。但它需要重新明确 VAD/端点相关完整状态、输入义务和会话边界。这项工作会扩大当前贡献，不宜在临近本轮 release 时通过隐含 reset 加进去。

## 本轮停止条件

当前阴性结果要求**收窄可部署性，保留并解释全部失败**，而不是为凑正面结果无限开分支。独立 c4 和完整历史重计若通过，且上述关键保留—失效链已有 NN 见证或明确限于 CPU/规格支持，则现有论文可以诚实地围绕反馈协调的两个见证和固定原任务写成一篇完整系统论文。若该链完全缺席且可用小规模明确故障 fixture 补到，它是本轮唯一值得优先考虑的新 NN 范围。

这份判断不承诺 DSN 接收，也不把质量退化淡化为普通限制。它明确区分：核心协调发现仍有证据；当前无 VAD 长流 adapter 没有达到有用服务要求；下一步应补连接机制的证据，而非继续刷看起来更好的统计点。

# DGFT Elastic Authority Granularity：定向补强结项

实验 ID：`REVTRACE-ELASTIC-20261022`。结论：**NO-GO：不将本轮联合 Elastic 调度升级为 C2 的正式算法贡献。** 机制安全扩展可行且真实GPU历史通过审计，但性能优势假设未通过预冻结门槛。此结论不撤销原 DGFT 的 C1/C2/C3，不是该题目的普遍不可能性证明，不修改正文/摘要/标题。

## 1. 本轮到底增加了什么

原论文 Theorem 1 的 accepted-history 归纳不使用固定区间长度；在可信caller、单Owner、连续合法父状态、冻结输入、音频就绪和同一准入/WAL检查的前提下，可以推广到依赖过去观察的 rho 序列。**原代码不能原封不动支持动态粒度。** 新增了逐会话不可变区间计划、允许集合/选择规则的静态契约绑定、caller 的计划/实际样本护栏、动态完成计数和恢复重计划语义。没有改变 `dgft.py`、WAL、Worker、可信Render和whole-view兼容原语（逐SHA一致）。

原 `adaptive_audio_plan()` 是离线声学能量切分，不是队列调度器，且边界不保证位于当前2s格点；不能直接替换 live/WAL resume。Qwen实际消费完整prefix音频并按当前chunk处理反馈；rho变化可能改变真实Canonical History和质量，不只是少发几个相同计算。每条历史都独立生成和审计，没有拼接固定轨迹的输出。

## 2. 三阶段与门槛，负面结果没有撤销

1. 源码/原稿/历史审计：GitHub基线 `af0920092abd25213378861a9a73bda17d7c2bc7`；正式runtime基线 `2a4b56bc5d8dcbf3884f03f8213f9c39101f59f8`。重算76个历史T1/R4单元。旧T1的相同负载可配对；旧R4不同并发/源集合不能拼成在线动态因果证据。
2. 16源资格实验：rho1/2/3 × sync/stagger/LHL，9个真实GPU scout。LHL中最佳固定rho2的Goodput为5.111 audio-s/wall-s，距理想到达上界只剩1.415%空间，门槛 **NO-GO**。保留全部结果。
3. 一次预冻结跨microbatch资格修订：32不同speaker完整音频，峰值超过MB16；同样9个固定GPU scout。低段Fine的Commit优势4.622s、高段Coarse优势13.818s，且实际存在Authority压力；主空间门槛允许最小原型。该结果仅是实现许可，不是动态收益。没有继续搜索第三套“更漂亮”的负载。
4. 正式比较：同32源/604.85音频秒，固定1/2/3、Backlog-only、Deadline-only、Joint各4次fresh运行，共24个。scout不计入正式重复。全过程只研究C2，没有额外C1/C3、Whisper、新模型、KV或恢复Worker实验。

总计 **42个真实双RTX3090运行 = 18 scout + 24 formal**。到达模式是受控实时replay，不是生产自然到达统计。32源不是128独立源。

## 3. 公平执行及测量

共同：Qwen3-ASR-1.7B，GPU0 FP16 Proposer/GPU1 FP32 Authority，eager、MB16、预算256、fine2s、decoupled-lazy、D1可信文本绑定、严格whole-view保留、two-lane真实FIFO消费、durable/group_ready WAL。六策略使用相同载体、模型、音频、精度和资源。策略声明本身不同所以chi可以不同；共同安全语义、资源与执行配置不放松。

LHL32：2流在0s、28流在10s、2流在42s释放；每条完整独立录音16–28s。不循环、复制或删尾。在线规则不读取未来cohort、未来音频内容或参考文本。已声明有限会话的真实EOF可缩短最终job；预测只在EOF实际到达后使用该信息。计划不等于派发，实际GPU调用仍等待目标音频已释放。

主SLO：Display 2s、Commit 8s。共同2s/精确末端frontier；Audio Goodput是同时满足两期限的音频秒/包括到达和drain的真实wall。所有未完成前沿为无穷延迟并保留分母；本轮正式运行均完成。Display取覆盖该前沿的**真实consumer应用完成**时间；Commit取覆盖该前沿的**WAL完成后owner安装状态**时间，不是consumer后来收到canonical publication的时间，也不是enqueue/worker完成/owner刚收到结果的时间。覆盖是输入音频前沿，不等于转录内容完整性。

主能耗是两GPU严格共同服务窗口积分，正式运行覆盖率均100%；初始化不在该服务窗口，主机能耗未测。原采样span值也保留，不把两种能量口径混用。WER/CER来自每条真实完整Canonical输出和同一独立音频参考，触顶独立计数。

## 4. 正式结果

下表是4个完整run指标的算术均值；WER/CER用百分数。不是池化P99，也不是新独立语料。

| 策略 | 双SLO Audio Goodput | Display P99 s | Commit P99 s | GPU J/audio-s | WER % | CER % |
|---|---:|---:|---:|---:|---:|---:|
| 固定rho1 | 1.408 | 12.637 | 23.656 | 43.732 | 2.033 | 0.503 |
| 固定rho2 | 2.012 | 10.033 | 11.871 | 38.447 | 2.033 | 0.517 |
| 固定rho3 | 2.207 | 7.836 | 9.905 | 36.072 | 1.970 | 0.517 |
| Backlog-only | 1.715 | 8.714 | 11.612 | 37.772 | 1.970 | 0.517 |
| Deadline-only | 2.353 | 8.329 | 11.328 | 36.592 | 1.970 | 0.503 |
| Joint | 2.115 | 10.525 | 14.393 | 39.528 | 1.842 | 0.461 |

**所有正式高压运行的整run双P99都未通过2s/8s。** 表中Goodput仅为部分音频按时交付，不能写成该负载满足SLO或生产容量。

Joint对最佳固定rho3：Goodput **−4.17%**，配对条件bootstrap 95%区间 **[−20.92%, +14.51%]**；4重复并非全正。Commit P99 **+45.31%**，能耗 **+9.58%**。

Joint对最佳简单Deadline：Goodput **−10.13%**，95%区间 **[−22.38%, −1.82%]**，4个重复差值均负；Commit P99 **+27.06%**，能耗 **+8.02%**。

质量非劣门槛通过：Joint对Fine的WER差−0.191pp，95%区间[−0.429pp,0]；CER差−0.042pp，区间[−0.095pp,0]，正式所有策略无触顶。区间含零，不能宣称统计确定的质量优越或用质量点估计抵消未达性能门槛。

Deadline对最佳固定Goodput点估计+6.62%，但95%区间 **[−7.44%, +27.90%]**；这是补充诊断，不支持“动态策略已显著战胜最佳固定”。没有另开事后成功出口。

统计：10,000次、seed20261022，4run/32source配对条件bootstrap，比较者在每次抽样中重新选最佳固定/简单策略。源重采样不会重新执行排队，因此区间条件于这些真实contended traces；能耗仅run层bootstrap。4重复/有限英语源池不能证明普适最优。完整每次结果、12点SLO网格、逐源质量/所有前沿在证据包内。

## 5. 为什么安全可行却性能未提升：事实与猜想分开

**测量事实：** Joint每轮平均173次认证，Deadline134次，固定rho3为116次；对应Authority去重worker服务38.861/30.168/29.279s。Joint选择1/2/3共268/122/302次（4轮），Deadline16/160/360次。Joint既没有拿到Fine的Commit尾时延，也没有拿到Coarse的能耗。

Joint安装减预测时间的P95为4.318s，Deadline为2.906s；该误差包含等待、Render和WAL，不是纯模型误差。选择器host耗时每轮0.150/0.122s，远小于尾延迟；这不支持“仅CPU调度太慢”的解释。Proposer的实际模型调用时间也随策略不同（Joint36.002s、rho3 33.324s），所以只优化Authority的局部预测不能直接推出双SLO Goodput。

**未证明的机制猜想：** 从固定粒度批次标定的median/p90成本在混合历史/排队下可能失准；Joint在无可行选择时的least-lateness退化可能偏好更多细调用，而不是最大化全局按时音频。当前证据能说明关联，不能断言某个单一根因已被隔离。若未来另立研究，应先固定真实日志做可证伪的过载目标/预测校准诊断，而不是在本轮正式结果后调阈值追正数。本轮不实施该修复，因为现有强基线已否决所冻结的升级假设。

## 6. 安全、恢复和证据等级

- 148项明确scope的CPU机制回归通过；新增Elastic测试覆盖冻结plan、非法rho/parent/sample范围、无未来cohort、pending不变、CPU WAL中断/恢复与契约改变拒绝。全历史pytest收集因19个旧脚本/fixture未随独立SDK分发而失败，原log保留，绝不称全suite通过。
- 81种变长区间原语序列，324次合法准入、重复全部拒绝、81次真实CPU WAL close/reopen。此为CPU合成内容，不是GPU恢复、神经输出或生产故障证据。
- 正式24条运行的Render、证书、WAL、实际消费者、音频就绪和冻结计划完整复算；4,224个正式选择按声明规则重放，未发现新增准入违规。安全性归纳的假设不由有限实验“证明”。
- 原始663文件逐SHA建立索引，453个有界原始文件/无损解压内容在本地回验，其余大型事件、Worker、consumer、功率和WAL留8TB盘。所有42运行的config/provenance/summary及原始位置可定位。
- formal前后模型权重逐哈希一致；源文件逐项一致。生成manifest自条目和未执行嵌套源码副本的打包缺陷明确记账，原测量source archives未改。

## 7. 对DSN贡献的裁定

**可支持：** C2的条件性安全可扩展至离散动态区间；允许集合、动态完成计数、父状态/音频/WAL接口不是免费的；新增rho2与公平非平稳固定/动态比较给出真实运行边界。

**不可支持：** Elastic DGFT显著优于最佳固定/简单动态、获得Fine时延与Coarse能耗、自动满足SLO、不同Canonical History等价、有限CPU/GPU记录证明无条件活性/质量/恢复。

**建议：** 原论文C2仍以双时间线因果协调及既有factorial/witness为主。本轮安全扩展与NO-GO可作为设计空间证据，不增加一个未赢强基线的“核心算法贡献”。原C1的E1/R5、A/V0/V1边界、C3三级恢复证据继续保留，既不重复扩充，也不被本轮性能失败否定。最终没有重命名旧组件包装新颖性，没有为正结果削弱基线，没有改稿。

入口：`README.md`、`C2_UPGRADE_DECISION.md`、`CLAIM_EVIDENCE_MATRIX.md`、`EVIDENCE_INDEX.json`、`collected/FORMAL_DECISION.json`。所有后续解释必须从这些冻结数字出发，不从最初的6.88x等旧口径推导本轮结论。

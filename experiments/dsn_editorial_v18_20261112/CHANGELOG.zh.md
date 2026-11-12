# RevTrace v17 → v18 变更记录

日期：2026-11-12。类型：既有结果的论证、写作与交付修订。本轮没有新增或重跑服务实验、参考推理、故障注入、工作负载或 GPU 调用；原始执行源、冻结数据和实测结果保留其原身份。

## 1. 基线与保留身份

- 保留的起点：`Paper_DSN/revisions/20261111_dsn2027_release_v17`。其原 PDF SHA256 为 `cdc69fdab3577558ebc8fc76d30fdf9d8c5ac7c239361cbcad0c553f32bd8b93`，本轮只读重核一致。
- 初始源基线由 [BASE_V17_MANIFEST.json](BASE_V17_MANIFEST.json) 逐文件记录；该快照 SHA256 为 `6e452e30772f253778227b166c164e744fd7d48109dc17bfb71dc288ba1dbce5`。其中原 `SOURCE_MANIFEST.json` 的 SHA256 为 `6fd4fabdefe2dba9842c081bf072e0616f54c721a503329563aeae989e064088`。
- 新稿在隔离的 `revtrace-dsn-v18-writing` 工作树中建立，版本目录为 `Paper_DSN/revisions/20261112_dsn2027_release_v18`；v17 及更早 release 保留。
- 论文归档与实际执行源分开。既有 native NN 源仍为 `de0936b2e30179d63aeef6e235cd1af685578c58`；本轮编辑不将归档提交号替代执行源身份。

## 2. 主线及选择性补回的证据：B / A / C / E / D

全文回到一条主线：在原反馈程序继续选择和修订时，联合保留仍合法的计算与实际可读的完整视图。贡献按“可复核服务问题 → 可执行协调协议 → 机制与端到端证据”排列。删除只重复防御质疑、没有推进这条论证的段落；在比较首次出现处直接说明其对象和测量身份。

| 采纳项 | 既有证据与本轮落点 | 对论证的作用 |
|---|---|---|
| **B：联合机制跨 cohort 复现** | 主 Qwen/2-s-feedback/staggered 层的三个 cohort 信用交互为 +18.530/+6.205/+17.555 audio-s。先定义 `I=Y11−Y10−Y01+Y00`；以逐 source 信用比例为 Y 时，均值 +5.90pp，描述性 bootstrap 95% 区间 [1.13,10.28]pp。放回主 factorial 结果。 | 以严格交互补足 6→17→0 的机制发现；源内比例交互、音频加权总量和 N8 配对差分别报告。 |
| **A：首次信用与持续服务可反排名** | 另一个 c16 开发银行的第三重复中，compute-only 首次信用 201.960s，高于 joint 的194.735s，却在原 D2 读点缺失4.000 audio-s已获信用的合法内容；joint为0。保留2.176s实测动机和低负载1/2/1损失。 | 显示首次及时到达与后来持续可用是不同服务端点；这一 secondary 分析没有改原信用。 |
| **C：输入资格与自己的预测正确性分离** | 旧 BDFA 四 source 银行的92次真实 model-active promotion中，20个 tentative successor 与原 C/U 最终选择不同。接到方法和机制评估。 | 调用输入成立使已执行工作有用，但结果仍由原完整 C/U 决定；旧银行不重新标记成当前 N8。 |
| **E：真实协议轨迹及 durable→install 故障见证** | 两个 earlier Fullcall after-durable案例中，原 journal sequence5 已同步、原Owner尚未安装即被终止。实际 durable/原Owner安装/Consumer使用为 **2/0/2**。恢复时由幸存 Supervisor 推进Owner命名空间，将已验证原fact及原job身份重放给幸存Consumer，再启动替代Owner。另保留36条轨迹的3,976次selected应用、9,068次provisional应用及90次compatible-ahead保留。 | 将命题允许的sync–install gap接到实际恢复；重放使用已有神经边，并不重新生成该边。 |
| **D：完整同步路径足迹** | 既有早期full-call实现8个timing-on真实run：完整fact commit的run-mean为20.35–27.25ms/调用，其中实际fsync为15.78–22.18ms；whole-view Consumer apply为18.58–23.91ms。恢复一个紧凑表及解释。 | 给出已实际执行的完整对象、持久化和Consumer路径成本。fsync嵌套在commit内，inclusive行不相加；这些是路径足迹，不能解释成移除协议后的净开销。测量保留旧runtime身份。 |

细化来源见 [评估主张映射](review/EVALUATION_CLAIM_MAP_v1.zh.md)、[评估改写记录](review/EVALUATION_CHANGES_v1.zh.md) 与 [引言／相关工作／结论映射](review/INTRO_RELATED_CONCLUSION_OUTLINE_v1.zh.md)。原始证据入口集中在 [v17复查与遗漏证据报告](../dsn_strengthening_v16_20261111/review/V17_REVIEW_FINDINGS_AND_MISSING_EVIDENCE.zh.md)。

## 3. P0及相关材料性修正

1. **取消普遍性能带推论。** 删除用93.1–97.7%与36.2–42.4%混合pilot及包含该pilot的N8，进而宣称普遍双峰分界、两独立native银行或编码决定服务水平的说法。N8主比较保留为93.9%对42.4%；core alternative-joint的1.85pp差异是已测工作点，不是正确实现之间的宽度上限。
2. **区分shadow判据与实际保留动作。** 290是sampled job/install predicate rows，278为当前完整输入匹配、12为反证；它们来自五个speculative政策的实际前缀上的判据比较。实际Fullcall/VDag各56次model-active handover另计，Ready的56次同输入重派、49次before-C退出与9次late refusal另计。原生text-only性能臂未测，不再写成落在某一低性能带。
3. **取消跨runtime事件同一性及错误因果比较。** 总信用或通过数相同不升级成相同miss事件结构；旧Conservative40.62%与新Ready42.43%不解释为缓存的净收益。保留清楚标识为earlier-runtime的同全文及时支持证据。
4. **统一资格、选择与支持的对象。** 输入绑定版本可承载资格witness；保守丢弃仍可安全。未决工作保留、原结果选择和whole-view支持分别说明，不把安全性等同于复用完备性，也不由safe UIR共用守卫的表现推出输入检查可删。
5. **校正工作点解释。** 负paired-jitter中 `R11−R10=−4.245s`，严格交互 `I=−2.245s`，仍有5次兼容ahead保留；primary-sync的简单差为−0.790s、I为+2.565s，仍保留3次。机会计数用作已测执行诊断，不作为部署前单变量收益预测器。
6. **校正比较身份与单位。** LA2-CP为固定实际候选日程上的文献规则适配；0.5-s fixed-lag为generic control。Native每条utterance为8.138–9.000s，16–18s是同来源两次重复的合计。worker wall、infer wall、GPU-active、两板服务能量和冷启动／参考费用保持各自口径。

N8的原数值不变：32个Full/Ready cell，8个既有speaker、每源两次fresh重复；前2源是pilot，后6源为预定确认。每臂offered137.864125 audio-s；信用129.460/58.500s；整场10/16对0/16；Ready有3次实际完成态复用。总体worker占用减少30.9%、两板服务能量减少22.0%，八源在合并各自两次重复后均为相同改善方向；两项精确总体降幅不扩写为每源降幅。

## 4. 文献、图和版面

- AlignAtt修正为Papi/Turchi/Negri的Interspeech2023原工作，使用 `papi2023alignatt`，移除不相符的旧年份／venue／arXiv字段。
- Related Work恢复SGLang跨程序原语的API speculation描述，并分别说明OCC的提交前验证、MVCC的多版本读管理和snapshot isolation的事务保证。
- 删除未引用的Saltzer条目。当前34个bib entry全部被引用，source audit无missing/unused/duplicate引用或重复标签。
- 两个venue使用标准简写：Whisper-Streaming条目的 `Proc. IJCNLP-AACL, System Demonstrations`，AISHELL-1条目的 `Proc. O-COCOSDA`。参考文献压回一页。
- 原四个矢量图PDF与v17逐字节一致，`figure_data_v16.json`也逐字节一致。图2的同一协议图移至更早的引言浮动位置，最终出现在PDF第3页；它仍是因果示意图。图1的真实时间线及图3/4的数据未变。
- 当前构建为10页技术内容＋1页参考文献，共11页；摘要139 token words（138 whitespace words）；34条已引用文献。该页数由实际PDF检查，引用数由reachable-source audit核对。

## 5. 收束与发布状态

本轮只进行了正文编辑、既有证据核对、静态源检查、CPU编译和逐页阅读／版面检查；没有GPU流程或新的科学实验，也没有改实际神经运行源／机器源指针。原研究总记录及失败／负结果继续保留。

本记录不充当最终PDF／源码包哈希回执。Root负责最终打包、GitHub同步和远端字节核验；提交身份与交付状态以其后续发布回执为准。本文件写成时不声明已提交或已推送。

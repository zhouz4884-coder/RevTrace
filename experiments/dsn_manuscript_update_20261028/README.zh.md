# DSN 2027 补强实验与正文修订：进行中

**2026-10-29当前进展：**下表四项原实验范围已完成，新的完整核心稿已写并初步编译为9页技术正文加参考文献。原生阶段profiling和69输入神经保真均完成。新增三臂pilot及全部四旧来源16格确认均完成：我们构造的整调用推测优于当前ready-only交接，选其为优先实现。每臂66.42975s分母上，原信用37.5→66.29375s、整轮D2/C8通过0/8→6/8，276步完整原状态/C/IDs保持。2个0.068s EOS miss未删除，严格实际可见F整文本支持另列33.5→56.287875s，旧指标不变。独立新来源与最终稿仍待本轮最后有意义的设计门闭合。

完整报告：[pilot内容边界](../dsn_streamcorrect_stage_handoff_20261029/PILOT_CONTENT_AND_SERVICE_REVIEW_v1.zh.md)、[阶段真实成本](../dsn_streamcorrect_stage_handoff_20261029/PILOT_STAGE_COST_AND_DECISION_v1.zh.md)、[真实在途保留与EOS](../dsn_streamcorrect_stage_handoff_20261029/PILOT_FULLSPEC_CAUSAL_REVIEW_v1.zh.md)。16格同时保留全部source/GPU角色换位/fresh配对；它是旧开发来源上的确认，不能冒充独立来源。99次promotion均在真实model路径未结束时发生，12次调用自己的预测终点不同仍被合法保留；20个自身完整start被否定的调用没有执行C/U或写入结果。

下一项仅是[编码器读集机会](ENCODER_READSET_OPPORTUNITY_PREPROFILE.zh.md)的有界组件成本探查：4个被否定whole-start与合法fallback的音频编码输入相同，反馈tokens/transcript不同；全部跨卡，需要真实7.68MB搬运。尚未实现或测得encoder缓存服务收益，不把条件成立当收益。现有整调用实现已成立，不因某条阶段代码没有独占性能而否定组合创新。

新证据包括：[阶段成本与完整候选](../dsn_streamcorrect_stage_profile_20261029/RESULTS_REPORT.zh.md)、[69输入神经等价与旧任务保真](../dsn_streamcorrect_stage_handoff_20261029/OLD_FIDELITY_RESULTS_v1.zh.md)、[原生内容端点](../dsn_native_content_20261029/RESULTS_FINDINGS.zh.md)、[完整2s实际文字病例](../dsn_full_interval_case_20261029/RESULTS_v2/timely_full_interval_case.pdf)。13个真实输入的最终预测状态不同，但其完整ASR候选经原C/U后仍与原生完整调用一致；这是组件合法性证据，不能代替在线服务收益。v1字节码参照检查失败和完整模块参照修复均保留。

本阶段接续 `cd6cf27` 已完成的110格独立确认与16格退出对照。目标是补齐服务区间/时序稳定性、计算保留×覆盖退出、真实纠错反馈应用，然后基于当前DSN旧稿改写完整正文并编译核验。

## 当前冻结任务

| 工作 | 范围 | 实际状态 |
|---|---|---|
| [服务区间与时序稳定性](../dsn_service_stability_20261028/README.zh.md) | c8-sync / c8-staggered / c16-staggered × R/S四臂 ×3新进程，共36格 | 36/36完成并通过独立复核；[完整结论](../dsn_service_stability_20261028/RESULTS_FINDINGS.zh.md)与[论文图](../dsn_service_stability_20261028/FIGURES_v2/FIGURE_MANIFEST.json)已生成。 |
| [保留与覆盖退出](../dsn_joint_retention_exit_20261028/RESULTS_FINDINGS.zh.md) | two_lane固定，R×K四臂 ×sync/staggered ×3新进程，共24格 | 24/24完成；独立重计和实际输入/Consumer侧证据齐全。交互符号混合，K定位执行支撑；同工作后继批真正miss→hit的数量已另列，不把所有obsolete行算作期限失败。 |
| [StreamCorrect有界适配](../dsn_streamcorrect_adaptation_20261028/NATIVE_RESULTS_REPORT.zh.md) | 原作者真实ASR与发布纠错器，固定4来源，2见证+12正式 | 全14完成，完整可信历史/CER一致。Joint减少41次Private调用、保留70次非空unchanged-ahead，但信用17s低于强两完整副本18.5s；全部formal D2失败，能耗边界已报告。 |
| [唯一12会话中点](../dsn_midpoint_continuity_20261029/MIDPOINT_FINDINGS.zh.md) | 原16开发源前12、四臂×3fresh | 全12及完整重计完成；强见证阴性，冻结STOP，不试10/11。原36+新12全部四工作点三重复已合并绘图。 |
| DSN正文 | 基于`Paper_DSN/CURRENT.md`所指20261008 coordination-spine旧稿 | 旧稿保护；完整核心稿`core_draft.tex`已写并初编译为9技术页+参考文献，正式main/PDF/CURRENT仍为旧基线，待最后研究决策、全页QA与干净发布包。 |

Qwen主实验实际神经源码为干净冻结的 `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`；原生v8执行源码为 `61c9afac00561f7ff1351f3eba9fd95adb239e8c`，不是本过程归档的HEAD。各CPU分析另有干净提交、完整manifest/bundle与实际输入哈希。所有大日志、环境、模型和音频仍在指定8TB盘；相邻任务不并行占用GPU，计时期间也避免重下载/解压和重CPU I/O。

## 当前设计判断

36格结果：c8-sync/c8-staggered每个点四臂三次均通过整场D2/C8，但错峰接近边界，仍有0.215秒末尾区间超过D2且没有从分母删去。c16-staggered全部12格未过D2、均过C8；联合相对双关的三次全offered信用净增20.280/22.885/20.180秒（每次250.18秒），R-only的16/17/12次回撤在联合下均为0。信用交互不是每次为正，对仅R也不全面占优。

新36格未出现普通发布触发的同root合法回撤，停止为强化Consumer另开支线。按[第三轮独立讨论](ROUND3_DECISION.zh.md)，不把三个嵌套工作点扩大成普遍容量曲线；下一步优先完成同场R×K与真实应用。当前[主张证据图](CLAIM_EVIDENCE_MAP.zh.md)记录效应、代价与尚未完成的工作。

[第四轮独立讨论](ROUND4_INDEPENDENT_DECISION.zh.md)提出并完成了一项有新意义的补强：在原始首交信用完全不变的前提下，重计全部36格/3204前沿的[及时交付后连续性](timely_continuity_v1/README.zh.md)。c16仅R的45次兼容回撤中，10/11/9次撤掉了原D2首交且C8最终及时的进展；其在原始D2读点仍缺失6.000/10.675/4.000音频秒，联合对应均0。c8错峰四臂P99均通过，仍观察到仅R的0.215/0/0.215s读点缺失。它补充说明首次交付与后续可用性不同，不替换原SLO，也不把暂定内容变成认证事实。必要撤回、未知和跨根截断均保留。

[正文论证计划](MANUSCRIPT_ARGUMENT_PLAN.zh.md)据此收紧：以可执行合法重根和端到端进展保留为主线，执行退出为支撑；后续是否增加候选交接，取决于真实原生机会与阶段成本，不因完整组合正控同效而否定组合创新。

根据新增连续性结果，[第五轮判断](ROUND5_DECISION.zh.md)冻结并完成了**唯一一个12会话错峰开发点**。三次Joint D99为2.197/2.299/2.228s，全部12格D2失败/C8通过；R-only兼容及时窗口1/1/3，但没有完整2s非EOS强窗口，Joint及时兼容损失全0。强条件未建立，停止选点和加重复。[全部48格合并图](../dsn_midpoint_continuity_20261029/FIGURES_48_v1/service_region.pdf)保留阴性中点，不是纯并发容量曲线。

新增[R×K同F内容支持](../dsn_joint_retention_exit_20261028/same_F_support_v1/RESULTS_FINDINGS.zh.md)完成全24格和固定96行：96/96正常后继行的完整首次消费原文与后来严格同F Canon一致；原R1 miss→hit 6/6/1行全部支持，原mixed交互/信用不改。整场首次及时内容仍有raw/norm不同，完整最终WER相同不能替代这个检查。

原生14完整结果揭示了新的[候选阶段机会](NATIVE_STAGE_VALIDITY_IDEA.zh.md)：244个非空完整同输入Private结果在Authority派发前已ready，预测最终反馈需撤回也不必使同次ASR候选无效。后续有界同步profiling已完成：64次真实非空纠错调用的ASR阶段均值434.70ms、纠错阶段268.72ms，完整快照另有成本。完整候选适配器69输入保真通过，其中13个最终预测反馈不同，原C/U仍给出一致结果。当前source_v3正在集成在线ready-only调度，**尚无在线交接服务结果**。强对照保留两完整副本、相同ASR早显与真实神经预热；固定两卡A/C分工不能预设吞吐优势，原native过载点完整保留。原作者公开推理代码确为FP32，本轮不把未经测量的精度变化当成免费优化。

旧开发轨迹的唯一D2 miss为2.154821秒，其中ACK到enqueue为1.625349秒，与前一Proposer物理lease重叠1.553488秒；本次实际生成0.428193秒、输入ACK11.56毫秒、发布到实际Consumer11.92毫秒。这个逐前沿分解表明，需要分别看执行排队、组批和持久化；累计fsync增加不能独立解释一次超时。

计算保留单开反而增加回撤是有价值的引言现象。其现有机制解释是Canonical应用时的快照替换，并非已证明Consumer算力不足。speaker bootstrap下界为正不自动成为普遍必要性定理；C1先建立合同内充分条件，是否最小必须另证。D2/C8信用改善和整场P99达标继续分开陈述。

[技术主线备忘录](SEMANTIC_SPINE.zh.md)明确完整跨调用状态、同边界、真实依赖、冻结在途输入和条件性可见保留；它不声称复用任意数值KV状态。先前1154状态与64-role检查必须核对实际模型范围，不能直接替代新C1的证明。

## 研究收束条件

核心条件可检查，时序实验给出收益及边界，R×K关系已辨明，外部应用完成有界验证或形成有证据的适用限制后，评估进一步实验是否还能改变主张或实质改善服务。新增工作仅重复已知结论时转写正文；发现影响主贡献且仍有端到端机会的具体设计缺口时，再做最小补强，不横向展开通用Agent或新取消原因。

当前状态见[ACTIVE_STATE.json](ACTIVE_STATE.json)。本过程版本明确区分计划、正在运行和完成结果；后续提交会补实际结果与最终正文入口。

# DSN 2027 补强实验与正文修订：进行中

本阶段接续 `cd6cf27` 已完成的110格独立确认与16格退出对照。目标是补齐服务区间/时序稳定性、计算保留×覆盖退出、真实纠错反馈应用，然后基于当前DSN旧稿改写完整正文并编译核验。

## 当前冻结任务

| 工作 | 范围 | 实际状态 |
|---|---|---|
| [服务区间与时序稳定性](../dsn_service_stability_20261028/README.zh.md) | c8-sync / c8-staggered / c16-staggered × R/S四臂 ×3新进程，共36格 | 36/36完成并通过独立复核；[完整结论](../dsn_service_stability_20261028/RESULTS_FINDINGS.zh.md)与[论文图](../dsn_service_stability_20261028/FIGURES_v2/FIGURE_MANIFEST.json)已生成。 |
| [保留与覆盖退出](../dsn_joint_retention_exit_20261028/RESULTS_FINDINGS.zh.md) | two_lane固定，R×K四臂 ×sync/staggered ×3新进程，共24格 | 24/24完成；独立重计和实际输入/Consumer侧证据齐全。交互符号混合，K定位执行支撑；同工作后继批真正miss→hit的数量已另列，不把所有obsolete行算作期限失败。 |
| [StreamCorrect有界适配](../dsn_streamcorrect_adaptation_20261028/NATIVE_RESULTS_REPORT.zh.md) | 原作者真实ASR与发布纠错器，固定4来源，2见证+12正式 | 全14完成，完整可信历史/CER一致。Joint减少41次Private调用、保留70次非空unchanged-ahead，但信用17s低于强两完整副本18.5s；全部formal D2失败，能耗边界已报告。 |
| [唯一12会话中点](../dsn_midpoint_continuity_20261029/MIDPOINT_FINDINGS.zh.md) | 原16开发源前12、四臂×3fresh | 全12及完整重计完成；强见证阴性，冻结STOP，不试10/11。原36+新12全部四工作点三重复已合并绘图。 |
| DSN正文 | 基于`Paper_DSN/CURRENT.md`所指20261008 coordination-spine旧稿 | 旧稿保护；新合同/合法性/协议技术章节草稿已写，main与PDF尚为旧基线，待最后有界设计判断后完整改写/编译/QA。 |

Qwen主实验实际神经源码为干净冻结的 `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`；原生v8执行源码为 `61c9afac00561f7ff1351f3eba9fd95adb239e8c`，不是本过程归档的HEAD。各CPU分析另有干净提交、完整manifest/bundle与实际输入哈希。所有大日志、环境、模型和音频仍在指定8TB盘；相邻任务不并行占用GPU，计时期间也避免重下载/解压和重CPU I/O。

## 当前设计判断

36格结果：c8-sync/c8-staggered每个点四臂三次均通过整场D2/C8，但错峰接近边界，仍有0.215秒末尾区间超过D2且没有从分母删去。c16-staggered全部12格未过D2、均过C8；联合相对双关的三次全offered信用净增20.280/22.885/20.180秒（每次250.18秒），R-only的16/17/12次回撤在联合下均为0。信用交互不是每次为正，对仅R也不全面占优。

新36格未出现普通发布触发的同root合法回撤，停止为强化Consumer另开支线。按[第三轮独立讨论](ROUND3_DECISION.zh.md)，不把三个嵌套工作点扩大成普遍容量曲线；下一步优先完成同场R×K与真实应用。当前[主张证据图](CLAIM_EVIDENCE_MAP.zh.md)记录效应、代价与尚未完成的工作。

[第四轮独立讨论](ROUND4_INDEPENDENT_DECISION.zh.md)提出并完成了一项有新意义的补强：在原始首交信用完全不变的前提下，重计全部36格/3204前沿的[及时交付后连续性](timely_continuity_v1/README.zh.md)。c16仅R的45次兼容回撤中，10/11/9次撤掉了原D2首交且C8最终及时的进展；其在原始D2读点仍缺失6.000/10.675/4.000音频秒，联合对应均0。c8错峰四臂P99均通过，仍观察到仅R的0.215/0/0.215s读点缺失。它补充说明首次交付与后续可用性不同，不替换原SLO，也不把暂定内容变成认证事实。必要撤回、未知和跨根截断均保留。

[正文论证计划](MANUSCRIPT_ARGUMENT_PLAN.zh.md)据此收紧：以可执行合法重根和端到端进展保留为主线，执行退出为支撑；后续是否增加候选交接，取决于真实原生机会与阶段成本，不因完整组合正控同效而否定组合创新。

根据新增连续性结果，[第五轮判断](ROUND5_DECISION.zh.md)冻结并完成了**唯一一个12会话错峰开发点**。三次Joint D99为2.197/2.299/2.228s，全部12格D2失败/C8通过；R-only兼容及时窗口1/1/3，但没有完整2s非EOS强窗口，Joint及时兼容损失全0。强条件未建立，停止选点和加重复。[全部48格合并图](../dsn_midpoint_continuity_20261029/FIGURES_48_v1/service_region.pdf)保留阴性中点，不是纯并发容量曲线。

新增[R×K同F内容支持](../dsn_joint_retention_exit_20261028/same_F_support_v1/RESULTS_FINDINGS.zh.md)完成全24格和固定96行：96/96正常后继行的完整首次消费原文与后来严格同F Canon一致；原R1 miss→hit 6/6/1行全部支持，原mixed交互/信用不改。整场首次及时内容仍有raw/norm不同，完整最终WER相同不能替代这个检查。

原生14完整结果揭示了新的[候选阶段机会](NATIVE_STAGE_VALIDITY_IDEA.zh.md)：244个非空完整同输入Private结果在Authority派发前已ready，预测最终反馈需撤回也不必使同次ASR候选无效。独立讨论同意先做有界同步A/C/H与完整beam/open-state profiling，保留原纠错选择与两完整副本ASR早显强对照。**目前只在本地准备新阶段方案，没有实现handoff或测得其服务收益。** 固定两卡A/C分工不能被预设为吞吐优于两完整副本；原native过载点完整保留。

旧开发轨迹的唯一D2 miss为2.154821秒，其中ACK到enqueue为1.625349秒，与前一Proposer物理lease重叠1.553488秒；本次实际生成0.428193秒、输入ACK11.56毫秒、发布到实际Consumer11.92毫秒。这个逐前沿分解表明，需要分别看执行排队、组批和持久化；累计fsync增加不能独立解释一次超时。

计算保留单开反而增加回撤是有价值的引言现象。其现有机制解释是Canonical应用时的快照替换，并非已证明Consumer算力不足。speaker bootstrap下界为正不自动成为普遍必要性定理；C1先建立合同内充分条件，是否最小必须另证。D2/C8信用改善和整场P99达标继续分开陈述。

[技术主线备忘录](SEMANTIC_SPINE.zh.md)明确完整跨调用状态、同边界、真实依赖、冻结在途输入和条件性可见保留；它不声称复用任意数值KV状态。先前1154状态与64-role检查必须核对实际模型范围，不能直接替代新C1的证明。

## 研究收束条件

核心条件可检查，时序实验给出收益及边界，R×K关系已辨明，外部应用完成有界验证或形成有证据的适用限制后，评估进一步实验是否还能改变主张或实质改善服务。新增工作仅重复已知结论时转写正文；发现影响主贡献且仍有端到端机会的具体设计缺口时，再做最小补强，不横向展开通用Agent或新取消原因。

当前状态见[ACTIVE_STATE.json](ACTIVE_STATE.json)。本过程版本明确区分计划、正在运行和完成结果；后续提交会补实际结果与最终正文入口。

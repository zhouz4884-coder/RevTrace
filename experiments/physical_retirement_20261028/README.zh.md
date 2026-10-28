# RevTrace：2026-10-28 研究结果与论文路线

本轮完成了真实decode安全点退出、16格服务强对照、110格独立来源组合确认、Whisper坏数据诊断与最近工作核查。没有修改论文正文。

**先读：[DSN 2027 初步贡献与实验收束计划](../../docs/research/independent_synthesis_20261028/CONTRIBUTION_PLAN.zh.md)。** 三项初步贡献是反馈兼容关系、计算与Consumer联合进展保留、可信交付与执行生命周期协调。前两项作为论文中心；退出是有边界的执行支撑，恢复暂作扩展。对用户长建议的逐项判断见[选择性综合](analysis_tools/SELECTIVE_PAPER_REASONING.zh.md)。

## 最有用的新结果

- 严格同底座2×2：24新speaker，714.11秒基础音频，110格全部完成，独立重复/多臂不增加来源数。Qwen rho1错峰下，R/S全关、仅S、仅R、联合的双期限音频信用分别为654.115、628.435、664.150、680.760秒；音频前沿回撤分别12、1、17、0次。完整Standard正控为667.530秒、0次。所有臂完整可信历史一致。
- 组合价值是计算保留与可见进展保留的交互。三个cohort交互均为正，联合比全关净增26.645秒。同步低机会点效果接近；cohort A时序重复中联合低于仅R。此结果不支持普遍性能优越性。
- 物理退出：简单可信覆盖条件使两次服务信用净增15.385/17.255秒，每次offered250.18秒。下一批16行的实际输入、完整输出和顺序相同，原臂全部过时，释放后全部实际显示。整场模型时间没有降低，watchdog/parent也有收益，额外退休条件未触发。
- Qwen rho1 pooled WER为26/1908=1.363%，各臂相同。Whisper rho1为83.12%，单独保留为adapter质量边界；rho3反馈合同不同。全部Qwen错峰cell未通过整场D2/C8双P99；零音频回撤不等于零文本修订。

## 结果入口

| 证据 | 文件 |
|---|---|
| 完整分层概览与哈希 | [COMPACT_TABLES.json](H3_RESULTS_v2/COMPACT_TABLES.json)、[重计记录](H3_RESULTS_v2/COMPACT_TABLES_RECORD.json) |
| 110格原终点、强对照和交互 | [aggregate](H3_RESULTS_v2/aggregate/SUMMARY.json)、[所有运行](H3_RESULTS_v2/aggregate/RUNS.json)、[交互](H3_RESULTS_v2/aggregate/FACTORIAL_EFFECTS.json) |
| 实际内容支持与机会密度 | [usefulness](H3_RESULTS_v2/usefulness/SUMMARY.json)、[opportunities](H3_RESULTS_v2/opportunities/ANALYSIS_RECORD.json) |
| 独立分析 | [H3独立阅读](analysis_tools/H3_INDEPENDENT_READING.zh.md) |
| 16格物理退出服务对照 | [结果判断](analysis_tools/real_service_full_v2_v1/SERVICE_CONTROL_DECISION_v1.json)、[完整配对](analysis_tools/PILOT_v2_FINDINGS.zh.md) |
| 同输入输出的真实服务窗口 | [服务机制证据](service_opportunity_v2/REPORT.zh.md) |
| 操作层收益，不是服务吞吐 | [operator_review](operator_review/README.zh.md) |
| 原始失败与分析修正 | [有界记录](H3_RESULTS_v2/records/DOWNLOAD_INDEX.json) |
| 来源清单与实际执行记录 | [冻结计划](confirmation_design/PLAN_v3.json)、[GPU完成记录](H3_RESULTS_v2/records/GPU_execution/GATE.json) |
| CPU回归 | [502通过、5子测试、16跳过](remote_evidence_v3/cpu_v3/SUMMARY.json) |
| Whisper诊断 | [9个付费正式调用](whisper_diagnostic_v1/RESULT_SUMMARY_v3.json) |
| 文献身份及最近工作 | [ASR邻居](literature_review/ASR_NEIGHBORS.md)、[Retire等](literature_review/BASELINE_IDENTITIES.md) |

后见同F Canonical全文支持不是groundtruth或在线正确性认证。rho3中未匹配同F的快照保持未知，不据此判错。实际Consumer是实验服务中的真实FIFO处理，不是生产WAN客户端。自然发生率、受控压力、条件性保证分开陈述。

## 源码与可重算性

| 工作 | 实际源码提交 |
|---|---|
| 第一版物理退出 | `c9c2469ba2ca38db5b7d9a3f1a7ea35052e57d68` |
| 16格正式服务对照 | `1d8c30804a945570429d85d934b3bfcba6171a43` |
| 最终统一运行与110格确认 | `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf` |
| 独立三项CPU分析 | `5cb9e17ef9ce0e97784f253dbb795585c5b1e29a` |
| 汇总路径解析修正 | `a4956b3cbb4a0bc92a822a6705d12d46f962c8c7` |

GitHub交付提交是证据归档提交，不替代这些执行提交。`packages/`保存完整历史bundle及逐文件SHA256清单，`source_v3/`是最终242文件源码快照；在新路径重建时先从对应bundle clone并核查清单。机器本地的根目录来源指针与本快照归档身份分开，不能将归档HEAD重新标为旧运行源码。

完整原始日志、模型、音频、环境与缓存保存在指定8TB实验盘：
`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028/`。
各重计的 `ANALYSIS_RECORD.json` 列出实际输入路径与哈希。GitHub只包含有界结果、配置、完整源码和重算程序；不声称已经上传全部大日志或模型数据。

初次聚合读取了冻结计划中的历史`out`别名，而非实际`argv --out`，因此报告110格缺失。测量命令与控制器`output`始终一致；独立分析修正只改变路径解析，并保留该差异计数、旧失败门和所有原始运行。正式重计接受110/110，没有新增GPU调用或更改实验计划。

## 后续优先级

依[贡献计划](../../docs/research/independent_synthesis_20261028/CONTRIBUTION_PLAN.zh.md)：先完善兼容关系与真实交错论证，再以少量冻结工作点确认可部署服务区间，随后考虑一个贴近StreamCorrect式真实纠错反馈的应用适配。复杂CES、跨Owner、Capsule及新的取消原因竞赛暂不进入主线。规划中的工作不计作本轮已完成实验。

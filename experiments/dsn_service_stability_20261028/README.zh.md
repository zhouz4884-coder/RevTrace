# DSN 服务区间与时序稳定性：冻结的 36 格

本研究只使用旧开发清单，神经运行源保持 `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`。没有读取 24 个 H3 确认来源的输出来选负载点，没有改变 D2/C8 或丢掉 offered 分母。

三个点为 c8 同步、同 8 源错峰、旧清单全 16 源错峰。每点计算保留 R × 双通道消费 S 四臂，各 3 个全新进程，合计 36 格。固定相位错峰为会话 sid×0.25 秒，保持现有运行实现。每波三个点随机排序，四臂采用随机化且位置计数差不超过 1 的 Latin 轮换。每格仍独立生成可信结果、持久化输入与 Canonical WAL、应用实际 Consumer，并计两板实际能耗。

这不是纯合成负载扫描。c8→c16 同时扩到原清单后 8 个真实来源，来源混合变化必须报告；只能称这三个实际工作负载的服务区间，不能据此估计精确最大容量。三次进程重复衡量时序变化，不是新音频独立样本。已有 H3 的作者完整组合 Standard 阳性替代实现继续承担跨方法载体检查，本轮无需重复扩大到第五臂。

## 先分析旧开发数据得到的解释

独立只读重算将 3 个旧 Qwen 单元的全部 **198 个前沿**逐个连接到实际发布结果、输入 ACK、执行器、完整行终态、Owner 与实际 Consumer。同步 R1S1 的 Display P99 为 1.4134 秒，错峰为 2.0343 秒。错峰的唯一 D2 miss 总延迟 **2.154821 秒**，其中：

| 实际路径阶段 | 秒 |
|---|---:|
| 原始 ready → 持久化输入 ACK | 0.011557 |
| ACK → 合法作业 enqueue | 1.625349 |
| enqueue → worker | 0.009041 |
| worker → model | 0.062209 |
| model → 完整行 terminal | 0.428193 |
| terminal → Owner receive | 0.004109 |
| Owner receive → publish | 0.002444 |
| publish → 实际 Consumer | 0.011919 |

ACK→enqueue 区间与同一 Proposer 的前序物理 lease 重叠 **1.553488 秒**。这是真实占用重叠，不是宣称取消能直接节约这么多时间。ACK→enqueue 还包含合法反馈依赖与可调度性，不能全部叫作排队或代码开销。该 miss 的直接瓶颈是生成开始前的等待，而非本次 0.428 秒生成或 12 毫秒 Consumer。

错峰还将 batch 数 27→50、输入快照同步次数 18→67、累计 input fsync 0.288→1.118 秒。单前沿的 input ACK 仍约毫秒量级；累计 fsync 数量不能直接拿来解释这个最差前沿。以上仅是实测机制线索，未做时移回放，也没有以叠加各组件 P99 来重建服务 P99。

## 冻结终点与判定

每格报告原始全程 D2/C8 P99 是否兑现、全部 offered 双期限信用、实际 Consumer 前沿回撤和缺口面积、质量、能耗。四臂每个时序重复报告 `Y11−Y10−Y01+Y00`，并在 Owner 安装与 Consumer 应用两条时钟分别重算兼容／不兼容 ahead 机会。自然收敛、兼容机会稀疏、真实不兼容时必要撤回以及过载失败均保留。

`critical_path.py` 将路径分成可加的实际阶段；前序 lease 与 WAL 重叠仅作描述。`aggregate_service_v5.py`、`canonical_usefulness_v1.py`、`interaction_opportunities_v1.py` 分别独立核对端到端终点、首次实际消费内容和完整祖先兼容。后两者是离线复核已有服务证据，不能当新服务调用。

计划及 SHA 见 [PLAN_v1.json](PLAN_v1.json)、[PLAN_RECEIPT_v1.json](PLAN_RECEIPT_v1.json)。独立 CPU 源冻结为 **fde6272b494db43a66eebea7444d7c9d1037e687**（7 文件）；`analysis_source_v1` 是未部署的早期包装器，v2 修正其已有 recounter 的摘要字段适配后才执行旧开发分析。没有重新标注神经实验。

旧开发分析、原始输入哈希和下载校验在 [old_development_recount_v1](old_development_recount_v1/)。实际原始日志仍在 8TB 盘。已通过本地无参 source preflight、远端 242 文件 byte 校验、CPU 分析源全文件校验与旧开发重算；**本目录准备过程没有启动 GPU 新实验**。

主协调者可用 `python experiments/dsn_service_stability_20261028/launch_gpu.py` 串行发起冻结计划。不得在其他神经实验并发时运行。完成后调用远端 `projects/revtrace_dsn_service_stability_20261028/analysis_source_v2/run_analysis.py`，使用对应冻结计划与 `ANALYSIS_SOURCE_v2.json`，新结果写 `results/revtrace/physical_retirement_20261028/dsn_service_stability_analysis_v1`。

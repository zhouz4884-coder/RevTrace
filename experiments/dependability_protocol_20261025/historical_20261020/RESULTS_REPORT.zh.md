# RevTrace：压缩六周补强计划实验结项报告

日期：2026-10-20。约定实验完成、独立审计通过；正文未修改。

## 核心结论

这轮把几个设计问题变成了可复核测量：真实异步执行下的过时结果、真实 worker 的错上下文执行、固定未来输入的影响、共同音频前沿上的双时限，以及分组日志的部分恢复语义。

最有价值的结果不是把旧 1.403× 再放大，而是明确了**哪些检查解决什么问题、最低限度协调需要什么、哪些替代方法同样有效**。DSN 可靠性论证因此更具体，但创新增量和部署覆盖仍需价值判断。

- 错上下文的 24 个候选元数据全部合法，其中 15 个仍通过原 .05 margin 门槛；正确上下文重评分却识别了全部 24 个。支持“验证应针对预期上下文”，不支持“只能完整重生成”。
- lazy 在正常负载下吞吐接近 legacy；约 3.44–3.46× 的配对收益只出现在预设 6s 结果交付阻塞中，是抗延迟/减少无效工作，不是普遍加速。

## 1. 完成范围

依据共享会话的最后一个压缩六周版本，非早期扩展清单。来源已完整读取、去重保留；引用内容不是自动执行指令。

| 阶段 | 完成内容 | 证据性质 |
|---|---|---|
| W1 | 历史事件；单 in-flight 最小 lazy reconciliation；差分 oracle | 历史 GPU 离线分析 + 新 CPU 测试 |
| W2 | E2 三策略×c8/c16×0/6s 交付延迟×3 repeats | 36 个真实双 RTX3090 GPU 单元 |
| W3 | E1 实际执行上下文替换；F1/F5；两种重评分；固定未来 | 24 冻结上下文×10 GPU 阶段；CPU 准入重放另列 |
| W4 | E3 同一音频前沿的显示/提交配对、有效进展、双时限全网格 | 历史 12 traces + E2 原始事件复算，无额外 GPU |
| W5 | E4 分组撕尾、坏帧、ACK、旧 epoch、幂等重试 | 7 项 CPU 写入/重开测试，非新增崩溃注入 |
| W6 | 独立审计、口径表、文档、私有归档 | 本报告；按最新指令延后正文重写 |

未执行 Quarantine、自适应 rho、新量化、大规模 V100、完整新 GPU crash 矩阵、跨节点/存活 zombie worker 架构。这些不是本压缩计划的遗漏项。

## 2. 固定条件与最小修复

E2：Qwen3-ASR-1.7B，双 RTX3090，FP16 proposer/FP32 authority，fine=2s、rho=3，durable group-ready journal。12 条构造源音频池；c8 使用前 8 条，c16 是 16 个负载槽，不是 16 条独立音频。策略共享数据、资源、到达时钟、日志和显式 canonical-display 规则。

hold 在计算完成后的交付路径，不伪造 GPU 执行时间，实际 completed 时间保留。它是预设交付受阻，不是自然慢故障发生率。

lazy：退休已被 committed frontier 覆盖或 generation 失效的完成结果；逐窗口记录 outcome；跳过未派发的已覆盖窗口；下次因果合法派发再沿既有安全路径 rebase。每会话只有一个 proposal in-flight，私有输出不写 canonical state。旧 parent 不自动非法。

模型、音频和冻结源码已核验。SHA、逐文件证据、审计入口见 `EVIDENCE_INDEX.json`。

## 3. E2：36 个正式 GPU 单元

每配置 3 次中位数；过时发布为 3 次总数。display/commit P99 在共同 q=2s +精确末端音频前沿上测量，不是仅对完成的 display event 求分位。

| 负载 | hold | 策略 | 过时发布 | display P99(s) | commit P99(s) | audio xRT | GPU J/audio-s |
|---|---:|---|---:|---:|---:|---:|---:|
| c8 | 0 | legacy | 19 | 2.196 | 6.897 | 6.455 | 53.252 |
| c8 | 0 | lazy | 0 | 2.001 | 6.805 | 6.456 | 53.100 |
| c8 | 0 | barrier | 0 | 3.913 | 6.824 | 6.454 | 52.562 |
| c16 | 0 | legacy | 41 | 5.432 | 8.406 | 12.671 | 32.274 |
| c16 | 0 | lazy | 0 | 5.332 | 8.396 | 12.833 | 31.652 |
| c16 | 0 | barrier | 0 | 6.887 | 8.585 | 12.552 | 32.046 |
| c8 | 6s | legacy | 420 | 6.732 | 6.732 | 1.748 | 117.011 |
| c8 | 6s | lazy | 0 | 6.777 | 6.777 | 6.024 | 49.287 |
| c8 | 6s | barrier | 0 | 104.155 | 112.176 | 1.757 | 141.693 |
| c16 | 6s | legacy | 837 | 8.411 | 8.411 | 3.311 | 66.497 |
| c16 | 6s | lazy | 0 | 8.276 | 8.276 | 11.430 | 28.895 |
| c16 | 6s | barrier | 0 | 115.373 | 121.876 | 3.305 | 80.622 |

所有 12 个 load/hold/repeat 三策略组的最终投影完全一致。所有窗口有 outcome，没有将退休/跳过/未完成窗口静默删出分母。独立重放验证提交与 WAL。

同 repeat 配对后取中位数，lazy/legacy 吞吐比：正常 c8 **1.0008×**、c16 **1.0128×**；hold c8 **3.4414×**、c16 **3.4580×**。不是“中位数之比”，完整范围在 CSV/JSON。

hold 下 proposer jobs 中位数 c8 从 140→41，c16 从 279→83；配对 GPU 能量比 0.4212/0.4327，减少 **57.88%/56.73%**。能量是 NVML 样本覆盖区间内两 GPU 梯形积分，不是整机、模型初始化全生命周期能耗。

正常 c8 lazy display P99 三次范围 **1.868–2.185s**，只有一次 ≤2s，不能声称稳定达标。c16 也未通过。hold c8 的显示 P99没有优于 legacy，不能写“所有指标都改善”。barrier 是合法安全对照，交付阻塞牵连其进度。

质量按唯一源去重，负载复制另查一致性：

| 负载 | 英文 WER | 中文 CER | 三策略/两时序/三重复 |
|---|---|---|---|
| c8 | 17/389 = 4.370% | 11/422 = 2.607% | 全一致 |
| c16 | 18/554 = 3.249% | 16/637 = 2.512% | 全一致 |

这说明本轮协调修复未改变测得质量；不证明以前长时 Whisper 质量问题已解决，不将两种语言错误率合并。

## 4. E1：真实错上下文，而非事后修改输出

预先冻结 12 条源×parent=12/18s 的 24 个上下文，同语言伙伴固定轮换，未按 margin/结果选例。worker 收到合法 job 后、执行前替换 actual prompt，job/audio 元数据不变；独立 authority 使用正确上下文。actual-context digest 是观察仪表，不是可信硬件证明。

10 个 GPU 阶段各 24 行：clean/wrong proposer、actual/correct-context re-score、clean/repeat/wrong authority、protected/unprotected/repeat future。240 行阶段执行**不是 240 个独立样本**。F1、certificate 安装、F5 接受是对真实 GPU 记录的 CPU 协议重放，不另算 GPU 故障试验。

| 检查/现象 | 结果 |
|---|---:|
| clean FP16/FP32 投影不同 | 0/24 |
| F2 合法结构检查通过 / F1 陈旧 epoch 被拒 | 各 24/24 |
| wrong proposer 投影不同 / 正确 parent 上便宜重建仍不同 | 各 24/24 |
| 原 wrong-context margin ≥.05 / actual-context re-score ≥.05 | 各 15/24 |
| correct-context re-score ≥.05 | 0/24 |
| protected 安装精确等于正确 authority | 24/24 |
| F5 错 authority 被接受且投影不同 | 24/24 |
| authority 同输入重复 / future 同输入重复一致 | 各 24/24 |
| 固定未来输入，新生成 tokens 不同 | 24/24 |
| 无保护时最终错误数增加 / 相同 / 减少 | 15 / 8 / 1 |

actual-context 重评分的全 token greedy 匹配为 22/24；另两项原始及重评分 minimum margin 均为 0，不在通过门槛的 15 项内。FP16 ties 保留，不宣称两种前向数值路径完全等价。

质量分前沿/语言，不把重复暴露的源合成独立样本：

| parent | 语言/指标 | protected | 重建后直接反馈 |
|---|---|---|---|
| 12s | 中文 CER | 16/637 = 2.512% | 211/637 = 33.124% |
| 12s | 英文 WER | 15/554 = 2.708% | 37/554 = 6.679% |
| 18s | 中文 CER | 16/637 = 2.512% | 130/637 = 20.408% |
| 18s | 英文 WER | 16/554 = 2.888% | 16/554 = 2.888% |

最后一行总体相同不代表逐 case 相同，正负变化可相抵。识别变坏涉及 10 条源；15 个高 margin 项中 8 个变坏、6 平、1 变好。unprotected future 有 1/24 触顶，protected 为 0/24，原样保留。

**正确上下文重评分是有效竞争解释。** 固定批次的 FP16 重评分阶段 wall=1.347s，FP32 clean authority 生成=7.801s；精度、操作、保证和在线生命周期不同，不能相除当在线加速。它足以否定“只有完整 authority 生成能发现这类错误”，尚未证明所有输入上的 FP32 选择等价。当前没有跑该替代 selector 的 live 流程，不伪造结果。

## 5. E3：速度与有效音频进展分开

历史 12 traces 共 3,348 proposal displays：621 次 parent-superseded，只有 7 次 target 已被 committed audio 覆盖。Coarse 的 6 次是同一中文源在两个复制槽、三次运行中的暴露，末端 provisional 文本均与 canonical 相同；另 1 次是 Fine 中间事件。不能写 621 次故障、7 个独立用户损害或 canonical 污染。

历史无 canonical-display 事件。共同前沿 primary 度量中，每个 Coarse-decoupled run 有 2 个末端点缺显示，按无穷延迟保留；“假设 commit 可见”另列敏感性，不冒充历史实测。旧 event-P99 不改，新 E2 才对三策略一致加入真实 canonical 发布日志。

双 deadline goodput：同 q 上合法显示和 durable commit 都在各自时限内，累计对应音频秒数/Twall（到达+排空）。event-level goodput 不等于全负载 P99 可行性。display 2/5/8s×commit 4/8/12/16s 全网格留在 CSV，未只挑有利点。

历史分解显示 authority enqueue→start GPU queue 中位数约 .01s；Fine audio-ready→enqueue 约 .43–.50s，Coarse 约 .025s。不能把所有等待叫 GPU 队列。

## 6. E4、审计和保留失败

7 项 CPU 测试：4 个撕尾偏移保留完整 checksummed prefix；完整坏帧 fail-closed；首 ACK 不代表跨会话 group 全有全无；旧 epoch 新结果与相同客户幂等重试区别处理。不是 GPU kill、断电或 surviving worker 实证。

最终复验：修订核心+完整原 fixtures **324 passed**；额外 E3/E4 **11 passed**。此前 303 原项目、43/45 Linux targeted 是重叠覆盖，不相加。

保留失败：有界导出缺 fixture 曾 19 fail/280 pass/4 skip，后在完整 fixtures 上验证核心；CPU stress 的 2s 模拟 timeout 对两个控制统一扩至 10s；集成路径修正后断言被测代码路径。E1 后处理 CPU 审计初次漏注册 Qwen processor，导入修复后重建通过，未改 GPU 测量。上游 tokenizer regex warning 留存，冻结 tokenizer 未静默更换，clean projection 全部独立重建一致。

独立审计不是只读 SUMMARY：E2 从 events/power/WAL/result 重算窗口、前沿、P99、网格、能量、WER/CER；E1 从十阶段记录重算上下文绑定、projection、margin、重复控制、edit distance。原证据审计前后 SHA 不变。

## 7. 收口与下一决策

E1/E2 都 COMPLETE、无 STOP。2026-10-20 12:02 UTC 双卡各 24MiB/0%，无计算进程或本任务控制器/worker。本轮实验问题已得到明确答案，不为了更好数字反复重跑。

这不是“topic 已到极限”。最有价值的剩余问题是正确上下文重评分作为在线 selector 的同契约成本/覆盖；应另立协议，不能用离线阶段耗时替代。更长期真实流量、更多独立源、第二家族同款 F2 覆盖也未被本轮短时 Qwen 解决。

先决定正文研究主张，再决定是否值得启动新的在线 selector 矩阵。按用户最新要求，**本轮没有修改正文/摘要/标题，没有新增投稿或公开发布**。

数据入口：`E1_CASES_20261020.csv`、`E2_GROUPS_20261020.csv`、`E2_PAIRED_20261020.csv`、`E2_DEADLINE_SUMMARY_20261020.csv`、`EVIDENCE_INDEX.json`。

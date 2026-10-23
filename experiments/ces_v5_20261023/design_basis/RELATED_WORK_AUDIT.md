# CES 下一步：正式发表近邻与创新边界审计

日期：2026-10-23。证据基线：RevTrace `01f6e04aa88cf704c129242e6bbdaf42de159525`。

本文件是算法设计阶段的定向文献审计，不是系统性综述，不证明不存在其他先行工作，也不是新的 GPU 实验。未改动正文、模型、基线或冻结测量。

**创新口径澄清：** 借鉴已有调度方法不否定组合创新或系统创新。“某个部件不能单独声称新”不等于“整套系统没有贡献”。在相同可靠性契约和公平强基线下，把已知方法组织成有效的执行能力，且其收益可重复、成本完整、适用边界明确，就可能成为有价值的系统贡献。本轮应先求证有效的最小组合，不为争取某个部件的独占新颖性而强加复杂机制。

## 1. 检索纪律与可复核范围

- 按 `nature-academic-search` 的 multi-source-search 路径，先核正式出版身份，再检查原作者或出版机构的一手材料。当前 academic-search MCP 未挂载，使用联网搜索及官方 USENIX、PMLR、ACM/会议 program、作者/机构页面交叉核验。
- 只纳入已经正式发表的工作；不以仅有 arXiv 条目的文章充当正式相关工作。正式论文的作者托管全文不改变其出版身份，但如果作者 PDF 不是最终排版版本，明确区分。
- 遇到 ACM 403、机构 PDF 502/timeout 或 PDF content-type 不支持，保留读取限制，不绕过权限，不把摘要阅读说成全文精读。
- 下列八篇是与本轮算法最相关的核心近邻，而非全部被检索到的论文。没有凭论文结果倍数做横向性能比较。

## 2. 八篇核心近邻

### R1. AdaServe — EuroSys 2026（最直接的创新碰撞）

**Title:** AdaServe: Accelerating Multi-SLO LLM Serving with SLO-Customized Speculative Decoding.

**正式身份：** EuroSys 2026；DOI `10.1145/3767295.3769315`。官方 [accepted papers](https://2026.eurosys.org/papers.html) 列明论文，作者提供带 EuroSys 2026 信息的 [正式全文](https://www.cs.cmu.edu/~zhihaoj2/papers/AdaServe_EuroSys26.pdf)。本轮读到 §4.1、Algorithm 1、§4.2、相关硬件预算讨论及理论附录的相关段落。

**论文实际支持：** 在多请求的 SLO 要求和总 token 预算下分配推测树节点；先达到每个请求的预期接受进展要求，再分配剩余预算优化总体收益。路径概率已知时的最优性有明确前提，实际概率仍需估计。

**可借用：** 先把执行动作映射成受约束的服务进展，再联合分配物理预算；不能只优化抽象验证比例。

**不能归我们原创：** SLO-aware speculation、跨请求联合规划、预期接受进展优化、硬件感知预算，这些表述单独均不足以构成 CES 新增量。

**真正待验证的差异：** RevTrace 的候选证据成功后产生一个条件性已知的 Canonical 投影，从而改变哪些已生成/已派发的 Private 任务仍合法可消费。目标还包含已显示/尚欠认证的两项不同义务；这不是只分配本请求 token 树的数量。此差异是本轮推导，不是已完成实证或“首次”声明。

### R2. SuperServe / SlackFit — NSDI 2025（强简单调度近邻）

**Title:** SuperServe: Fine-Grained Inference Serving for Unpredictable Workloads.

**正式身份：** NSDI 2025，739–758。官方 [论文与元数据](https://www.usenix.org/conference/nsdi25/presentation/khare)，[全文](https://www.usenix.org/system/files/nsdi25-khare.pdf)。本轮重点读 §4.2、§4.2.1 和附录策略讨论。

**论文实际支持：** SlackFit 用最早截止请求的剩余 slack，联合选择模型子网及批大小；离线配置桶缩小在线搜索，在线采用可快速执行的策略。

**可借用：** 用实际剩余 slack 而非全局固定阈值；共享同一性能标定；把简单且足够强的策略作为对照。

**不能归我们原创：** “按 deadline 选执行模式/批大小”“动态适应 burst”本身不是新算法。CES 应保留同标定模型的 SlackFit-like gate，而不是仅与 Always Fine/Strict 比。

**差异：** 我们不能在 deadline 压力下换成较低可信度输出；Verify 和 Generate 必须交付同一个声明准入契约的证据，且动作会改变后续合法状态关系。论文的 accuracy/latency 伸缩不等于这一安全约束。

### R3. QoServe — ASPLOS 2026（过载处理边界）

**Title:** QoServe: Breaking the Silos of LLM Inference Serving.

**正式身份：** ASPLOS 2026；DOI `10.1145/3779212.3790206`。官方 [program](https://www.asplos-conference.org/asplos2026/program/index.html) 的 Session 1A 列明；[Microsoft publication](https://www.microsoft.com/en-us/research/publication/niyama-breaking-the-silos-of-llm-inference-serving/) 标注 ASPLOS 2026。机构摘要仍保留旧系统名 Niyama，不能把它误算成另一篇独立成果。

**阅读范围：** 官方出版信息和机构摘要。本轮 [最终 PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2025/10/QoServe_CC_final_v2.pdf) 读取超时，故不声称已独立复核全文算法或证明。

**支持点：** 动态 chunking、混合优先级、按 QoS 共同服务及过载时选择性 relegation 已有正式近邻。

**差异与红线：** RevTrace 中错过显示期限的前驱仍可能是后续合法 Parent 的必经路径，不能因为本段 Goodput 已失就跳过其认证；也不能丢弃请求后从分母移除。可借鉴显式区分服务优先级，不照搬改变本契约的请求降级行为。

### R4. Beyond Prediction / UniBoost — ICML 2026（v5A 的强碰撞）

**Title:** Beyond Prediction: Tail-Aware Scheduling for LLM Inference.

**正式身份：** ICML 2026，PMLR 306:66188–66203。[正式 proceedings](https://proceedings.mlr.press/v306/li26n.html) 给出出版信息、作者和摘要。

**阅读范围：** 正式摘要及作者项目材料；proceedings 链接的 PDF 被读取工具因 `application/octet-stream` 拒绝，未宣称检查全文证明。

**支持点：** 均值导向、预测长度式优先级不等于尾延迟优化；即使服务长度预测很好也可能尾部表现不好。该文提出分布感知、无需显式长度预测的软优先级及 cache-aware preemption。

**对本轮的意义：** v5A 将均值换 P95 只是风险建模改善，不能自动声称优化了双期限 Goodput。我们应使真正的残余完成义务成为目标，同时报告成本预测偏差与 deadline 失败之间的对应关系。

**边界：** 现有 RTX3090 SDK 没有该文的 cache-aware 可抢占执行能力，不得在仿真里免费借用。参考其“目标函数先行”的原则，不声称移植其运行时。

### R5. DistServe — OSDI 2024（双 SLO / 两阶段不新）

**Title:** DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving.

**正式身份：** OSDI 2024，193–210。[官方论文页](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin)，[全文](https://www.usenix.org/system/files/osdi24-zhong-yinmin.pdf)。本轮读了问题定义、§4 配置/放置、§4.3 运行调度及相关边界。

**支持点：** 同时受两个延迟约束的 Goodput、拆开不同计算阶段、按工作负载与设备成本配置资源，已有成熟正式工作。

**可借用：** 所有方法都用完整的双期限衡量，而不把两个单独达标比例相乘；区分阶段成本、资源配置和在线策略。

**差异：** Display 与 Canonical Admission 不是 prefill/decode 的同义改名。前者存在可独立兑现的可见义务、不可提前获得的状态写权限以及条件性 Parent 更新；CES 应证明此状态结构增加了可利用信息，而不是仅再做两个 GPU 队列。

### R6. Clockwork — OSDI 2020（成本标定和执行控制是底座）

**Title:** Serving DNNs like Clockwork: Performance Predictability from the Bottom Up.

**正式身份：** OSDI 2020，443–462。[官方论文页](https://www.usenix.org/conference/osdi20/presentation/gujarati)，[全文](https://www.usenix.org/system/files/osdi20-gujarati.pdf)。本轮读了系统方法、worker 和 controller 相关段落。

**支持点：** 显式掌握 GPU 操作、减少内部不确定性、使用执行时间估计安排 deadline-aware 请求，早已有系统化方案。

**可借用：** 先测完整物理调用、Worker Lease 与返回边界，再调度；估计模型应与执行器语义一致。

**限制：** 其 DNN 推理可预测性不能直接升级为 RevTrace 条件 Fallback 或批敏感自回归生成的确定时间界。本轮的分位数仅是经验风险控制，不能声称硬 SLO 保证。

### R7. SpecInfer — ASPLOS 2024（验证不是本轮新发明）

**Title:** SpecInfer: Accelerating Large Language Model Serving with Tree-based Speculative Inference and Verification.

**正式身份：** ASPLOS 2024，Volume 3，932–949；DOI `10.1145/3620666.3651335`。[官方会议 program](https://www.asplos-conference.org/asplos2024/main-program/index.html) 列出论文及正式 DOI 链接；作者 [publication list](https://hsword.github.io/publications/) 亦标明 ASPLOS 2024。

**阅读范围：** 出版身份已核。作者 [PDF](https://www.cs.cmu.edu/~zhihaoj2/papers/specinfer.pdf) 是较早的 17 页版本，标题/作者表与会议最终版有差别；只用它支持候选生成与可信模型树验证的高层机制，不依据其旧版具体实验数或页码论证最终版细节。

**可借用：** 可信验证必须完整，接受或回退必须支付真实模型工作，候选不因被选择而自动可信。

**差异：** RevTrace 本轮固定原模型与契约，不扩大 token 树或另造推测解码算法；研究的是跨轮状态准入证据选择对合法可见进展及后继任务可消费性的影响。

### R8. Decima — SIGCOMM 2019（依赖感知/后继价值不新）

**Title:** Learning Scheduling Algorithms for Data Processing Clusters.

**正式身份：** SIGCOMM 2019；DOI `10.1145/3341302.3342080`。[作者项目页](https://web.mit.edu/decima/)，带正式会议信息的 [作者全文](https://web.mit.edu/decima/content/sigcomm-2019.pdf)。本轮读了依赖图表示、目标函数与调度动作相关部分。

**支持点：** 利用 DAG 依赖、关键路径、后继任务的完成价值来选择资源分配，不是新的调度思想。

**差异：** 我们的可执行图不仅是固定输入 DAG；准入动作的真实结果决定新的 Parent，从而使部分已存在的 Private 链继续合法、另一些失效。因此需显式描述“证据结果驱动的合法集合迁移”，不能只把 descendant_count 放入一个打分器就声称因果创新。

**边界：** 不因此引入 RL、训练大规模控制器或声称不受经典 DAG 调度理论覆盖。新状态表示和动作对象即使成立，也必须有额外实证，而非仅命名。

## 3. 对拟议 CES v5 的独立判断

### 已知底座，应明确致谢/借用

1. 物理批次成本标定、分位数风险控制、deadline/slack 门控。
2. 滚动有限时域规划、joint batch selection、DAG/后继依赖价值。
3. 多阶段双 SLO Goodput、生成/验证切换及可信 fallback。

这三类即使实现成功，也不足以将其中某个常规部件单独宣称为原创；但它们在 RevTrace 契约内的有效组合、可靠执行和真实收益可以构成 C2 的系统优化。是否需要更复杂的条件性 Parent 规划，应由简单组合留下的实际收益缺口决定，而不是由“必须造一个全新部件”的预设决定。

### 有希望但仍未证成的独立对象

令一个已释放音频前沿的义务为 `(D, C)`：合法可见消费和耐久认证消费。已准时完成 D 而 C 尚欠的前沿仍有完整的认证边际价值；D 已逾期的前沿失去本段双期限 credit，但其认证仍可能解锁后续前沿。一次 Verify 成功时，已有完整候选 Z 配合当前 Parent 的确定性可信 Adapter，可条件性计算目标投影 `P'`，再检查实际冻结的私有链能否继续合法消费。Generate/Fallback 的 `P'` 在真实执行前未知，不能假定必失效，也不能赋予免费确定性保留。

因此本轮最值得争取的是：**在不改变任何准入判据的条件下，用证据结果所决定的合法集合迁移，规划尚欠 D/C 的实际前沿收益，而不是规划候选数量或历史私有工作量。** 这是对 RevTrace 对象的更准确建模；还不是已证实的性能贡献或全球新颖性结论。

### 与算法 agent 交叉质疑后的要求

- 不能用“不同出生 Parent”当硬拒绝；Correct-context Verification 的最终结果仍决定接受。
- 不能用 CPU render 旧 Z 当作新 Parent 下已实际生成的模型结果。
- 条件分支只影响规划，不提前触发 WAL、Consumer 或状态写入。
- 不能把 Direct 的未知 Parent 分支写成必定失效，或把 Verify 成功写成保留所有后继。
- 所有策略共用 Row-complete、成本模型、风险模型、真实覆盖/Consumer 信息与搜索预算。
- 除 Cost-only 外，必须有同双期限目标、同风险模型、同 lookahead 但关闭 `P' -> feasible-private-set` 迁移的规划器；还需简单 known-P 门控，排除复杂规划只是装饰的解释。
- 已运行但被淘汰的 GPU 工作是 sunk cost，不能因为调度器“少失效几个任务”就计为节能。

## 4. 最强创新否决票与证据回答

**质疑：** “这是 AdaServe 式进展优化 + SlackFit 式期限适配 + 普通 DAG/MPC，应用对象换成 ASR。”

不能仅靠 related-work 表回答。必须给出一个可执行反例：两个具有相同成本、slack、候选就绪和后继数量的状态，仅因 Verify 成功后的真实 `P'` 与已冻结私有链兼容性不同，就应选择不同动作；传统只看 cost/slack/计数的策略无法区分，而完整策略在真实运行中减少合法消费逾期。随后须证明这种状态对在正式机会中并非极少数，并在未用于设计的新来源确认净收益。

若没有这种机会，或简单 known-P 门控/同等信息的强 planner 已达到相同性能，则“复杂条件性 Parent 迁移提供独立交互收益”的额外主张 NO-GO，而非整个 CES 优化方向 NO-GO。仍应保留能够公平复现净收益的风险成本模型与简单 deadline 组合，并将其准确表述为系统组合/优化贡献；共享执行器收益也可作为系统资产，但不得包装成 CES 独占收益。

## 5. 额外检索纠正和读取失败

- InferLine 正式版是 **SoCC 2020**，不是 SOSP 2019：DOI `10.1145/3419111.3421285`。[机构存档检索入口](https://par.nsf.gov/servlets/purl/10245792) 可见正式元数据/摘要，但本轮直接打开两次返回 502；ACM DOI 打开为 403。因此未用它支撑逐节的新颖性判断。
- REEF 的正式 OSDI 2022 [论文页](https://www.usenix.org/conference/osdi22/presentation/han) 与 [全文](https://www.usenix.org/system/files/osdi22-han.pdf) 已核：其 reset-based kernel preemption 依赖真实的 GPU runtime 能力。这里只用于排除“已派发 Batch 免费取消/抢占”的非法估计，不作为本轮核心算法来源。
- Nexus/Sarathi-Serve/AlpaServe/INFaaS 的官方或作者出版资料有筛查，但为避免堆引用，未纳入八篇核心。
- 未对仅预印本工作作优先权或实验否决判断；这也意味着本文件不能支持“所有先行工作均已排除”的结论。

## 6. 研究决策

**GO（设计级，不是实现/性能 GO）：** 先验证风险校准与简单 deadline/frontier 记账的最小有效组合；若实际日志仍显示可利用而被简单组合遗漏的机会，再加入 `conditional post-admission Parent -> legal private feasible set -> residual dual-deadline credit`。仅当存在候选就绪瓶颈和真实空档收益时，在物理 Worker 空闲边界延伸到 GPU0/GPU1 联合派发。采用能取得可重复系统收益的最简单一层，不预设复杂度越高越好。

**NO-GO（主张级）：** 不把“P95 成本模型”“多请求 deadline-aware speculation”“普通滚动规划”本身写成单组件独占创新；不因其部件已有先例就否认经过验证的整体组合价值，也不预承诺优于 Fine、Cost-only、Standard，或提高 DSN 录用概率的具体幅度。

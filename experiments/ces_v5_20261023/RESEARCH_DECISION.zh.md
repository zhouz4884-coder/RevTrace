# CES V5 CPU 研究结论与算法取舍

本轮按用户最新要求完成 CPU 实现、数学审计、模型机制分析和正式文献复核。服务器网络不可用后停止了连接尝试；没有运行 V5 GPU 实验，也没有修改论文。基线为公开归档 `01f6e04aa88cf704c129242e6bbdaf42de159525`，执行过的 V4 源码为 `e0aeae1b418644c378dde331c59b55fc5948b40f`。

## 1. 我的判断

最值得继续的是同一条 CES 主线：**根据尚欠的合法音频进展选择认证证据，并通过批次划分及时完成必要前驱。** 组合已有的风险估计、期限传播和有限规划完全可以形成系统创新；是否采用更复杂的算法，以系统收益和实际成本决定。

本轮没有找到一个可以凭数学命名就保证优于 Fine 的公式。我们找到并修复了三个会阻止有效优化的具体问题，建立了检验更强算法的有限最优对照。后续 GPU 实验应测试这个收敛后的方案，而非继续给旧后代惩罚调整权重。

## 2. 新证据如何改变设计

V4 独立 Mixed 中，Fine、Standard、Cost-only 和 CES 每个到达组的 405 个前沿观测都满足 Commit<=8s。Goodput 差距主要体现在 Display 和整 run wall。405 是相同 135 个前沿的三次运行，不是 405 个独立来源。

CES 所选 Verify 批的平均预测/实际占用为 0.442/0.757s；这说明需要校准所选动作成本，却不能仅凭不同策略选出的不同批次就证明“这些 Verify 应全部改成 Generate”。正确比较还需要同输入下的合法操作成本，且必须考虑结果对后续状态的影响。

模型源码说明：完整 FP32 teacher forcing 是对完整候选的一次前向；失败后的 FP32 Generate 是额外真实调用。失败集合的行数、原 padding、音频输入和候选长度共同影响成本。当前代码没有把验证 KV 免费交给 Fallback。我们保留这些真实计算。

GPU0 的所谓 deadline-order 在 16 个单飞 Session、batch limit=16 时往往仍选中所有任务；统一 Display SLO 下 EDF 对未过期任务又与 release FIFO 同序。因此仅换排序不能冒充新增调度自由度。本轮将它保留为退化对照，不将其称作完整双 GPU 联合算法。

## 3. 数学目标：两项义务，两个完成路径

对音频原子 q，令权重为 a_q，释放时间 r_q，期限为 dD_q=r_q+2、dC_q=r_q+8。定义：

`Q_q = a_q * 1(D_q <= dD_q) * 1(C_q <= dC_q)`。

D_q 是实际 Consumer 的第一次合法可见时间，C_q 是耐久状态准入时间。已按时显示、尚未提交的前沿仍保留完整的剩余 Commit 价值；显示已逾期的前沿失去自身信用，但其认证仍可能解锁后继，不能跳过或删除分母。

更完整的双时间线模型还应表达：

`D_q = min(legal private-view completion, canonical publication completion)`。

这里的 private 路径必须在相应实际 Parent/branch/contract 下合法。认证不是所有 Display 路径的必经前驱。当前 `deadline_backprop.py` 和有限 Oracle 明确建模 Canonical 路径；不能将该模型的最优性直接扩展到全部真实双路径状态。

实际整 run Goodput 为 `sum(Q_q)/T_run`。在线原型比较同一当前任务集的 `E[新增Q]/E[完成墙钟]`，它是局部启发式。CPU 反例证明它不等于整 run 有限时域比率，也不等于 `E[Q/T]`。一个更强的短视域规划器应携带已观察的累计 Q/T，并对同一完整义务集计算各场景的比率；未知未来 Parent/Token 仍只能作为模型分支，不得进入真实执行。

## 4. 已实现的 V5 核心

### 实际进展反馈

Consumer 在真正应用合法视图后发不可变 ACK。Owner 校验 run、contract、epoch、前沿和时间后用于调度；重复 ACK 不重复计分，撤回不删除原 first-visible 历史，未来 ACK 不提前生效。所有对照共用这一能力和实际开销。

### 物理批次风险与逐行 CDF

对 Verify 批 B，使用：

`C_V(B)=C_verify(B)+E_F[C_fallback(F; original_layout(B))]+host/IPC`。

失败集合 F 的成本一般不能简化成 `C_fallback(E|F|)`；同批结果和物理占用也不能由独立行概率简单相乘表示。当前模型保存整批失败数与阶段成本场景，失败行身份按交换性近似；它还不是按真实状态条件充分拟合的失败集合模型。

每个物理场景保留逐行完成 CDF，独立保留最终 lease。期限信用计算使用 `Pr(T_row<=deadline)`，避免将 `1(E[T_row]<=deadline)` 当成概率。验证成功行可先返回，下一批仍必须等物理 Batch-drained。

### 合法批次动作

所有策略共同获得全量 G、可行 V/G 组合及有限 G/G、V/V 拆批候选；一次只发一个同构批，未选任务仍在共同完成集内付费。候选未就绪不能 Verify，不同出生 Parent 不作硬拒绝。

`progress` 以残余双期限信用/共同完成墙钟为主目标；Commit 逾期作为次级性能指标。状态准入谓词始终独立执行。`risk_cost` 保留风险成本目标作为对照。完整计划的 Owner delivery 尾部计入预测 cut wall，不把两张 GPU 的重叠执行时间相加。

## 5. 最有价值的下一层：前驱期限回传

若一个当前认证前驱 p 的自身 Display 已逾期，但完成它能解锁已释放的后续前沿 q，就需要向 p 回传 q 的期限。对一条声明的合法完成路径，使用：

`effective_finish(p) = min(own_due(p), min_q(effective_finish(q) - estimated_remaining_service(p,q)))`。

这个量用于构造值得比较的子批和次序，不是准入权限或硬 SLO 保证。只有已释放音频进入模型；下一真实 Job 必须等实际 Canonical Parent 形成后再构造。

对已有候选 Z，验证成功条件下的下一投影 `P'_V=Phi(P,Z)` 可计算，所以可以进一步检查现有 Private 链是否仍符合已有 `eligible_chain`。Direct/Fallback 的 P 未知，不意味着一定不兼容。已有的链保留能力本身不被重新命名为新机制；候选增量在于利用这个条件性状态关系安排真实工作。

建议的完整算法流程：

1. 合并真实 Consumer ACK、当前 Parent、已释放前沿和 Worker lease。
2. 构造 Display/Commit 残余义务及必要 Canonical 前驱。
3. 从真实空闲 Worker 上枚举共享的同构批和有界次序。
4. 以逐行完成分布、完整 Fallback/lease 和合法后继路径评估信用。
5. 用前驱期限回传引导候选动作，再用共同完成集的目标比较；只执行第一个当前合法动作。
6. 收到真实结果后重新检查全部原准入谓词并重规划。

当前在线原型已实现步骤 1、3 和当前目标的步骤 4；前驱传播和完整依赖规划已有可执行 CPU 模型，尚未接入真实未知 Parent 的在线长视野规划。这个分界是本轮的实际交付状态。

## 6. 为什么不直接使用贪心密度或声称全局最优

Parent/Child 工作具有互补性：Parent 立即信用可能是零，但与后续 Child 合起来产生正信用。因此“每项收益/成本最大”无法一般性地处理这些依赖。

有限 CPU Oracle 对至多 8 个任务、明示同构动作、固定时间/转移成本和结构依赖枚举完整调度。它对同完成集合保存 `(time,credit,commit_late)` 的 Pareto 标签，并与不剪枝的完整枚举核对。在这些明确前提下得到模型最优解。

真实系统中，相同完成集合可能对应不同 P、Private 链、候选和物理输入布局，不能只按集合合并状态。在线更合理的路线是：小问题用精确模型作校验，大问题使用保持这些身份的有界搜索，并报告它对模型 Oracle 的差距及实际 Host 成本。最优性边界必须跟着模型前提走。

## 7. CPU 结果与保留的负结果

- 原初版源 `fdf9243` 保留。Commit-first 反例在相同 1.6s 全部付费工作下选择 0 audio-s 信用；修复后选择模型内可达的 2 audio-s 信用。
- 0.1/0.9s 两行、期限 0.5s 的例子：平均行时间法错误判断两行都及时；逐行 CDF 正确得到一行及时。
- 子批与 Parent 解锁夹具在相同全量付费工作下具有不同按时覆盖；这是结构反例，不是 RTX3090 上的增益数字。
- Scoped runtime 回归 279 项通过；独立数学、有限 Oracle、期限传播、计量及优化等价测试 56 项通过。240 个随机计划/决策和 160 个剪枝/不剪枝对照均通过，另有精确期限边界测试。
- 用 90 个历史开发运行的 2,000 个 Authority 物理批拟合，旧验证池不参与拟合；最终场景预测器共核对 3,750 个历史实际 Authority 批。
- 旧验证池的 Generate P90 覆盖率 90.53%，Verify 为 86.45%；中位绝对均值误差分别约 106/147ms。这是历史选中批的预测检查，不是新 V5 服务效果或新独立确认。
- 8 个加权代表场景精确保留每桶 fallback/no-fallback 质量，但不能保留全部 K 分布和极端尾部。n16 Verify 桶的失败比例分布 TV 最大为 0.30；global Verify 最大成本比率由 4.144 变为代表值 1.830。保留这项近似误差。
- 扩大动作搜索后，直接标量实现的 16 任务满候选 CPU 夹具规划时间达到约 287ms。通过期望的线性分解、行 CDF 向量化以及模型内安全上界剪枝，同一校准/特征的测量降至约 29ms。所有计划度量/选择在声明容差内一致；CPU 数字不换算成 GPU 加速。完整冷/热耗时和较小负载均保留，并非每个单任务点都更快。
- 再从 14,670 条开发集真实 Canonical transition 独立重建行结果到 Owner/WAL/实际 Consumer 的延迟，三种时钟交叉核对误差为零。实际 Consumer 延迟中位数 38.614ms、P90 80.294ms。最终 calibration_v3 为所有方法加入这个共同经验交付 allowance；它不是确定上界，也尚未完整表示 Owner/WAL 串行队列与下一 Batch 派发的交互。

## 8. 正式文献怎样进入设计

这些是借鉴来源，不是把已有机制当作无价值。相关技术在 RevTrace 安全边界下产生可重复系统收益，仍可以成为组合贡献。

- [Clockwork，OSDI 2020](https://www.usenix.org/conference/osdi20/presentation/gujarati)：显式控制执行与成本，再做期限调度。借鉴物理资源计价，不继承自回归条件回退的确定时间保证。
- [Orca，OSDI 2022](https://www.usenix.org/conference/osdi22/presentation/yu)：调度收益需要真实执行选择。我们只使用现有 Batch-drained 边界，没有伪装 token 级抢占。
- [Speculative Decoding，ICML 2023](https://proceedings.mlr.press/v202/leviathan23a.html)：已知候选可以并行验证；本协议的完整跨轮选择与真实回退成本仍独立计量。
- [DistServe，OSDI 2024](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin)：多阶段完成指标必须联合衡量；Display/Commit 的状态权限关系是我们具体处理的对象。
- [SuperServe/SlackFit，NSDI 2025](https://www.usenix.org/conference/nsdi25/presentation/khare)：以 slack 选择配置和批大小，支持强简单对照；RevTrace 不因期限放松认证。
- [AdaServe，EuroSys 2026](https://www.cs.cmu.edu/~zhihaoj2/papers/AdaServe_EuroSys26.pdf)：将推测预算与服务进展结合。我们的研究单元是跨轮状态准入及其合法可见进展。
- [Beyond Prediction，ICML 2026](https://proceedings.mlr.press/v306/li26n.html)：较准的均值预测不等于较好的尾部服务。此处用真实 deadline 事件与完成 CDF 作目标，未移植其抢占运行时。
- [Decima，SIGCOMM 2019](https://web.mit.edu/decima/)：依赖关系与后继价值已有成熟研究；我们采用小规模可审计规划，不先引入 RL。

正式身份与阅读范围见上一轮 `RELATED_WORK_AUDIT.md`，本轮另有模型机制复核。没有将仅预印本论文纳入本次优先权判断，也不宣称穷尽先行工作。

## 9. 下一轮最值得验证的假设

主假设是：**有些 Display 逾期由认证工作排序与批次占用造成；在固定 rho=1 和相同安全契约下，用实际信用、完成分布和必要前驱安排同构子批，可以用相近或更低成本提高合法进展。**

恢复 GPU 后先做被测合法输入/布局的整批与拆批成本核对，再做 Fine、Standard、共享风险成本和进展策略的匹配短运行。验证失败需要区分成本模型误差、真实没有时序空间、质量变化和代码缺陷。所有旧 Private 工作继续计费。

若简单组合表现最好，保留它并解释其有效组合；若前驱规划进一步改善，就单独给它证据。若优势只存在于 CPU 构造、或改变了质量/口径，则不提升为 DSN 的实证方法贡献。原 C1/C2/C3 与此前负结果均保留。

本轮决策：**GO：CPU 原型与算法方向；GPU 系统收益待验证。** 不自动启动任何远端任务。

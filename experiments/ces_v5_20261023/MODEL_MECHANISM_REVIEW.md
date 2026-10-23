# CES V5：模型实现、输入语义与调度自由度复核

审计日期：2026-10-23。当前工作是 CPU 源码和已有证据审计；没有新 GPU 调用、SSH 操作或论文修改。代码引用相对于本目录 `runtime/`。历史报告位于 `D:/StreamTxn/outputs/`，不把已归档摘要当作本轮重新取得完整原始 GPU 轨迹。

## 结论

初版 V5（冻结 commit `fdf9243`）最应补的是**真实调度动作空间**。它已修复实际 Consumer 进展记账，并引入共享批次风险估计，但审计发现两个限制：

1. 当前 `progress_joint` 的 GPU0 动作只是 Ready 列表重排。正式 V4 的 180 份配置都为 `microbatch=16,rho=1`，负载每池 16 个 Session，每 Session 至多一个 Private Job 在途，因此 Ready 集合不会超过 16。`ready[:limit]` 仍然选中所有 Ready 任务；排序最多改变物理行次序，不能声称改变候选准备顺序或双 GPU 资源分配。
2. 初版 `fdf9243` 的 GPU1 只对已有候选划分 Verify/Generate；没有候选时，所有合法计划退化为整批 Generate。独立同步 Mixed 的 CES 三轮仅有 5、5、7 个候选及时就绪（135 个目标/run），因此仅改评分函数仍可能在大量决策上没有可选动作。

后续 CPU 修复已经给 GPU1 增加显式 G/G 与 V/V 同构拆批动作，因此第二项已不再描述修复后的动作集合。原反例作为修复前证据保留；是否有真实收益仍未知。GPU0 目前仍只是 Ready 排序，第一项集合等价限制仍在，尚未完成实质双时间线联合调度。

推荐下一项 CPU 算法增强：**对已经释放的后续音频前沿，将显示期限回传到必需的 Canonical 前驱，并允许有限的同构子批先行**。其目的是让一个自身已经错过 Display、但能及时解锁下一段音频的前驱获得恰当优先级。它必须和具有相同子批能力的 EDF/共享成本控制比较。先证明能改变合法动作和构造性收益，再讨论真实收益；不能将一个名称为 joint、实际只重排行的策略当作完整联合调度。

## 1. 完整 FP32 Verification 的真正成本

### 1.1 当前执行的不是旧 grouped_replay 的固定 64 倍数宽度

`scripts/tc_live_worker.py:184` 将 CES Verify 送入 `online_selection_worker.select_online`。
后者 `:23–38` 使用 `w=max(len(candidate))`，把完整候选右侧补齐到同一宽度，追加在 processor 的左侧已补齐 prompt 之后，执行一次 `model.thinker(...,use_cache=False)`。`lm_head` hook 只保留需要的预测位置，减少不必要的词表投影；它没有把 Transformer 主体的上下文计算、音频处理和候选 padding 成本消掉。

同文件中旧 grouped verifier 的 64-window 补齐路径依然存在，不能把它的宽度规则套在当前 CES 路径上。核对具体调用分支比看到名为 verifier 的函数更重要。

Complete strict certificate 检查全部 Token、首个 EOS/合法预算截止和预测长度（`src/revtrace/sequence_verifier.py:2–10`）。当前设计没有因更早发现低置信度就给未验证后缀准入权限。

### 1.2 Verify 和 Generate 的资源需求不同

可信 Generate 运行 `model.generate(...,do_sample=False,max_new_tokens=budget)`，逐步生成到各行终止/预算；完整模型 Batch 在最后一行排空前占用 Worker。Verify 是对已知完整候选的一次并行前向，其开销受物理行数、prompt padded width、最大候选长度、音频特征布局与 dtype 影响。

因此“验证 20 行比生成 20 行便宜”的常数比不应跨音频/候选长度直接迁移。对长候选或高拒绝批，验证增加的一次全上下文操作可能成为额外工作。对于短候选、无回退批，它又可能确实更便宜。

冻结 Phase N V1 操作器结果提供了正反两面：batch=16 的 C1 完整验证 1.273s 对独立生成 3.042s；C2 验证+实际回退 7.891s 对生成 5.563s；额外付费 Root Draft 的 C3 总顺序工作 7.245s 对生成 5.544s。这些是固定态操作成本，不能移作部署 Goodput 或 P99。

在当前选择器中应预测的对象至少是：

\[
C_V(B)=C_{\rm verify}(B,L_{\max},M_{\max},A_{\rm layout})+
\mathbb E_{F\subseteq B}[C_{\rm fallback}(F;\operatorname{layout}(B))]+C_{\rm host/IPC}.
\]

这里 `F` 是失败行集合。只有 `K=|F|` 不一定足够：同样 K 的失败行可能有不同条件输入、生成长度和 EOS 时间；选择性回退仍保留原 padded widths。K 分布是有价值的改进，但不是完全指定了服务时间分布。

### 1.3 实际 Fallback 必须付费，输出不是原整批输出的免费子集

`src/revtrace/online_admission.py::fallback_row_plan` 仅当所有输入张量的第一维确实是原 batch 行数时，才允许 selective layout。
`scripts/online_selection_worker.py:73–79` 对这些张量按失败行 `index_select(0,indices)`；其余维度不重新缩窄，原 padding 保留。随后真实调用一次 FP32 Generate。

这个执行布局比原整批少行，不能在任意数值环境下先验宣称输出等于原批中的对应行。已有 paid oracle 控制分别重跑原整批、回退布局、同输入重复和自验证（同文件 `:80–94`），这给出被测输入/布局的证据。后续新布局仍须独立审计。

Verify 使用 `use_cache=False`，代码没有给 fresh Fallback 传入验证 KV。任何把验证视为预填充已经免费完成、进而将 Fallback 降成续算的成本模型，都与当前真实执行不符。

### 1.4 逐行返回与物理排空是两个时钟

`online_selection_worker.py:70–72` 在验证整批完成后立即发出成功行完整结果；失败行继续真实回退。通过行可以先做 WAL/Consumer，但 GPU1 仍被该批占用。Generate 的完整行也可以在同行继续生成时返回。

当前调度器应同时保留 `T_row` 与 `T_drain`。把成功行早完成推算成整个 Worker 立即可用，会虚构容量；反过来用最终排空作为所有行的消费时间，又会抹掉已经实测的 Row-complete 收益。

## 2. Birth Parent、模型输入与合法投影不是同一种等价

### 2.1 Qwen 模型实际消费的上下文

`scripts/tc_live_worker.py:129–156` 的顺序是：取完整 waveform prefix → 解码实际 prompt Token → 当 `chunk_id>=2` 时重新编码并回退最后五 Token（Unicode 不完整则继续回退）→ 构造 prefix → processor 在整个物理批上 padding。

所以：

- 相同逻辑 Parent 不足以保证相同输入；chunk、rollback、音频 prefix 和 processor batch 形状都可能不同。
- 不同 Parent 也不自动意味着 Verify 必然失败。正确上下文 verifier 重新检查候选 Z，合法性来自这次可信选择。
- “旧 Z 在新 Parent 下经过 CPU Render 得到 P”只定义条件性输出状态；它没有证明新 Parent 下模型会选择这个 Z。

Phase N V0 保留了 batch-dependent input realization 负结果：一个 `chinese-05` 目标的逻辑 Parent、prompt、chunk、waveform 和 rollback prefix 相同，但 singleton 与三行批的 processor Token 长度为 523/524，特征长度 3464/3600，feature mask 的有效长度也不同。已有 CPU 同布局重放复现该差异。它是输入处理链边界，不是本轮重新测出的 GPU 故障或文本损害。

### 2.2 本轮可以使用、不能扩大的历史证据

Research Opportunity A 报告对 Phase D 90 单元的 3,993 次检查中，Exact-P 已接受 3,715 次，130 次缺同边界节点，148 次 P 不匹配。148 次仅涉及 12 个唯一 `(source,frontier,Pold,Pnew)` 组合，rollback5 后相同 prefix 和重新编码后等价均为 0。原机制后来对这些后代同音频再执行 0 次。

所以 17.164 秒已支付后代 GPU 时间不是可直接回收的关键路径预算；不能以“逻辑 P 不同但反正可能忘掉”启动新 Grafting。Whisper 当时使用显式 `prompt_ids`，没有走被引用的自动 previous-segment 截断分支，也不能借接口名字假定历史会自动截断。

另一方面，CES 正式同步 Mixed 三次选择的 16 个 Verify 全部通过，same-birth 目标为 0。这明确反驳“出生 Parent 不同就硬跳过验证”的规则。新政策可以使用可观测上下文关系预测成本，准入仍由真实 FP32 完整检查决定。

## 3. GPU0 deadline 排序什么时候与 FIFO 等价

源码锚点：`live_qwen.py:340–366`，`ces_runtime.py:86–96,169`。

设已释放且可派发的 Proposer 集合为 R，每个 Session 至多一个 Job；microbatch 上限为 B。当前实现做 `sorted(R,key=... )[:B]`。

**集合等价命题。** 若 `|R|<=B`，任何排序的派发集合都等于 R；同一 dispatch 点没有改变谁等待下一批。因此排序的差异只可能是批内行排列、Host 开销或由排列诱发的实际数值/处理差异，不能算作优先级调度将某 Session 提前到另一个批。

CPU 读取 180 个冻结 `*-config.json.gz` 得到所有配置 `microbatch=16,rho=1`；正式负载为 16 Session。单飞条件来自 `fine_busy`。于是这一等价命题覆盖当前正式负载结构。

**顺序等价命题。** 对都尚未完成合法 Display、尚未过期、使用同一 2s SLO 的任务：

\[
d_j^D=r_j+2,\qquad \operatorname{argsort}(d_j^D)=\operatorname{argsort}(r_j).
\]

也就是说普通 EDF 与原 ready FIFO 在这些任务上本来一致。新顺序仅在已显示、已经过期、aging 分类不同，且确实存在批容量选择时才可能改变执行次序。

`progress_joint` 的当前名称应在报告中精确解释为 **GPU0 deadline-order ablation**，不能先验称为完成了 GPU0/GPU1 联合资源规划。将其用于 CPU 退化检查很有价值，继续同名投入大量 GPU 并没有足够理由。

## 4. 已知 Z 如何形成真实的 action-dependent 后继机会

已有 `src/revtrace/continuity_proof.py:2–25` 的 `eligible_chain` 要求：同认证音频边界、Exact-P、相同 branch generation、每条边的冻结输入与前驱输出相等、完整链达到 tip；在途后继也必须使用该 tip 的实际冻结输入。真实 Commit 后，`live_qwen.py:621–634` 才应用证明并更新 branch root。

对当前合法 Parent P 和已就绪候选 Z，可以计算：

\[
P_V^+=\Phi(P,Z).
\]

这是 **Verify 成功条件下** 已知的下一投影。可以在只读 shadow Session 上把该 P 和目标 frontier 放入现有 `eligible_chain`，得到成功分支是否能接上已有 Private 链。不能把 shadow 成功当成状态已安装，也不能将字符串后缀拼进 Canonical 文本。

一个值得计入调度目标的条件机会至少同时满足：

1. 存在实际完成或在途的合法后继链，输入和 generation 已冻结；
2. 后继覆盖的目标音频已释放，而且此前没有实际 Consumer 按时覆盖的信用；
3. 成功 Verify 后现有 Exact-P 规则能保留该链；
4. 相应行完成、Owner、WAL/Consumer 开销之后仍有赶上 Display 的时间；
5. 对照动作的后继保留概率或时间确实不同，不能将 Direct 未知 P 直接置为“不兼容”。

前四项可通过已有状态和时间成本构造条件性预测，第五项往往仍需要校准或后续同输入真实对照。即使 Verify 的目标投影与出生投影相等，也不代表存在后代、更不代表相对 Direct 多得到有效 Goodput。

已有 compact Canonical witnesses 支持某些 accepted Verify 的投影相等，但不包含全部 Private 链及完整 Consumer 生命周期。本审计没有把缺失的 raw 状态补成“已存在的大量复用机会”。

## 5. 最值得实施的一个 CPU 增强：前驱期限回传与子批选择

### 5.1 为什么初版 fdf9243 即使账算对仍可能做不出改进

初版 `fdf9243` 的 `ces_v5_policy.py:275–314` 只枚举可验证候选前缀与 Generate 补集；没有候选时只剩 all-Generate。修复后显式拆批已增加动作自由度。仍需另行处理的是：`choose_v5` 只建模每 Session 的当前 authority target，一个已经错过自己 Display 的前驱虽然仍被付费，但其能解锁下一段已释放音频的价值没有进入计划。

这不是要求复杂学习器。只需要让必要前驱继承后继的最晚完成时间，并允许在物理空闲点决定先派哪一个合法同构子批。

### 5.2 简单数学定义

令 a 是当前可执行的认证前驱，u 是同一 Session 已释放、尚未及时合法显示的后续目标。令 `R(a,u,op)` 是在 op 实际生成合法 Parent 后，从 a 完成到 u 合法 Consumer 观察的剩余工作路径；不得计入尚未释放音频或假想未来 Token。

给出经过校准、带明确误差范围的保守工作估计 `\widehat c_R`，定义：

\[
\ell_a(op)=\min\left(d_a^C,\min_{u\in U_t(a,op)}[d_u^D-\widehat c_R(a,u,op)]\right).
\]

它是调度使用的有效完成期限，不是形式化 SLO 保证。没有合法后继、后继已获得 Display 信用或后继不可在期限内完成时，对应边不产生额外奖励。Direct/Fallback 的未知 P 需使用独立校准的区间；Verify-success 可以用已知条件 P 做更精确的兼容性检查。

在每次 Worker 真实空闲时，仅枚举有限动作：原全批、按有效期限选的 1/2/4/8/... 前缀（不超过现有上限）、原共享成本策略的动作。每个计划将未选中的当前债务继续计费；执行首批后根据真实结果重算。没有运行中取消、额外 Worker、免费异构 Batch 或 KV 重用。

所有强基线得到同样的子批执行能力。至少比较：普通 EDF 子批、共享风险成本子批、前驱期限回传子批。若子批本身解释全部收益，保留有效的简单组合并按实际来源解释贡献。

### 5.3 构造性 CPU 反例，不能当 GPU 实测

以下只是待测试的排程夹具。时刻 `t=10.05`：Session A 的 a0 音频释放于 8s，Display 已错过 10s，Commit 截止 16s，成本 0.4s；a1 音频已于 10s 释放、Display 截止 12s，必须 a0 完成后才能使用实际新 Parent，后续成本 0.9s。另一 Session B 已按时显示，Commit 截止 14s，成本 0.8s。

按单行 Commit EDF，B→a0→a1 的 a1 完成时间为 12.15s；a0→a1→B 则 a1 于 11.35s 完成，B 仍在 14s 前完成。a0 的有效完成期限是 `12−0.9=11.1s`，虽然 a0 自己的双期限信用已经为零，它仍有解锁下一目标的价值。

为检验与初版 all-Generate 批操作的差别，夹具还必须明确给定合批成本，不能只比较串行单行：例如冻结 `{a0,B}` 的物理占用为 1.2s，a0 完整行于 0.8s 返回，下一 a1 仍须等 GPU1 排空后执行 0.9s，于 12.15s 完成。子批 `a0→a1→B` 保留所有 2.1s 已付费工作、相同最终排空时间，却使 a1 于 11.35s 完成。若合法 full-batch Oracle 本已令 a1 按时，则这个具体夹具的子批收益为零，必须如实测试。以上所有成本都是构造参数，尚未由真实模型测得。

这个反例证明当前目标集合/评分可以遗漏一种合法的调度需求，**不证明真实批生成成本具有这些数值**。CPU 夹具应验证动作、父状态形成顺序和全债务计费；真实机会大小需要之后在完整日志或新实测中计数。

### 5.4 CPU 验证必须包括的退化情形

- 所有任务都无后继或后继已按时显示时，回传期限退化为基础期限策略；
- `|R|<=B` 且不启用子批时，新旧派发集合一致，不能报告调度机会；
- 未释放后继不能产生优先级收益；
- Verify-success 条件 P 不等于 Direct/Fallback 已知 P；错误预测不能越过原准入；
- 后继已经显示的信用不能再奖励一次；
- 延后任务在最终耗时、能量和未完成分母中保留；
- 到实际证据到达才构造下一 Job，禁止使用 shadow 的 P 提前执行真实后继；
- 同一前驱能够解锁多个前沿时使用互斥音频原子计算，不能将同一音频在多条路径上重复加分。

### 5.5 已落地的有界 CPU 符号模块

本目录新增 `deadline_backprop.py` 和 `test_deadline_backprop.py`，未接入 Runtime。
`build_symbolic_problem` 仅接收不可变 Canonical frontier、已释放义务、前驱 frontier、Display/Commit 截止与声明的服务估计/上界；返回 effective finish、latest start、结构依赖和优先级。它不接收或产生 P/Z，不签发证书，不构造真实 Job，也不修改已提交历史。

`to_oracle_tasks()` 将相同义务集传给有限 CPU 排程 oracle；每个前沿只对应一个音频权重，所有任务都必须完成。`priority_order(completed)` 中的 completed 只是 CPU 模型的依赖集合，不能替代真实 WAL 安装。

实际运行 `python -m pytest test_deadline_backprop.py test_cpu_planning_oracle.py -q`，26 项测试通过。本文夹具在完整付费 2.1 秒下得到 4 对 2 单位及时音频信用；该数值仅检查构造性推导和模型求解器联动，**不是 GPU 实测、模型输出或未来速度预测**。另验证未释放后继拒绝、D 已满足保留 C、旧 committed frontier 不可重写、缺失/分叉前驱拒绝，以及无有效后继时退化回自身期限。

## 6. 两篇正式文献能支持什么

1. **Leviathan, Kalman, Matias, ICML 2023, Fast Inference from Transformers via Speculative Decoding.** 正式 PMLR 页面确认发表身份。它支持“已知候选可由目标模型并行核查”的成本动机。RevTrace 当前核查的是完整跨轮 continuation，失败付费重新生成；引用该工作不等于继承任意 batch/layout 下逐比特相同的数值保证，也不意味着可以忽略跨轮状态准入。来源：https://proceedings.mlr.press/v202/leviathan23a.html

2. **Yu et al., OSDI 2022, Orca.** 正式 USENIX 页面明确将 iteration-level scheduling 用于获得哪些请求、多少请求在下一轮执行的控制。它提醒我们调度创新必须对应真实执行选择。RevTrace 当前非抢占 Worker 不能直接宣称具有 Orca 的 token iteration 调度能力；本建议只在 Batch-drained 时选择同构子批。来源：https://www.usenix.org/conference/osdi22/presentation/yu

两者都是正式发表文献。本审计不扩展为新的推测解码系统，也不把已有系统组合视为无效创新：若这些成熟方法在 RevTrace 的安全状态边界下组合后取得可重复系统收益，就应保留并据实解释。

## 7. 证据和代码身份

本次读取/复核：

- 当前隔离 runtime 的 worker、online verifier、D1 render、continuity proof、live owner、CES owner 与 V5 policy；
- CES v4 `FORMAL_FREEZE.md`、全部 180 份压缩 config（仅复核 microbatch/rho），`CELL_OPPORTUNITIES.csv`；
- 已有 `ces_progress_design_20261023/EVIDENCE_CRITIQUE.md` 的实际诊断及 witness 边界；
- Phase N 公开本地报告 V0/V1/V2 决策；Phase D R2 匹配因子报告；Research Opportunity A/B 正式决策；Causal Row Completion 结项报告。

Git partial checkout 的 Phase N blobs 未在本地，`git show` 尝试 lazy fetch 因网络失败；随后使用对应本地 `public_release` 报告。未据此声称重新逐字节核对整个 GitHub 归档。

审计时源码/证据 SHA256（若之后修改，需要重新固定行号与哈希）：

| 文件 | SHA256 |
|---|---|
| `runtime/scripts/online_selection_worker.py` | `5748f52f3ca07babed1fce2122959e9654c62a2fe2275bd0b080376a96405e97` |
| `runtime/scripts/tc_live_worker.py` | `72e1e1c04bbec73defdfd6e96080afd6f70a82b51f6817f5681be6c11e5f509e0` |
| `runtime/src/revtrace/continuity_proof.py` | `b1cab992b3109abaac1c07ba3414b022740f1a0387c6695e478a4fb0397989ac` |
| `runtime/src/revtrace/ces_runtime.py` | `51314925ec236c2e2483482dfa9725b0821510e0d31eb8d75a8d2712e2267d68` |
| `runtime/src/revtrace/ces_v5_policy.py` | `80cbcf2817374cb8ef556f6dfded13ef934ba11937053d6c3db22252b49079f2` |
| V4 `CELL_OPPORTUNITIES.csv` | `3654365a265f70a4be30fb4ec4ee51009f66bfc3a43a4551e66776035013b5ca` |

本轮没有新增模型输出、性能数字或真实服务结论。最强的新增发现是：当前所谓 GPU0 联合排序在既有最大并发/批上限下缺乏改变派发集合的自由度。下一步 CPU 工作应优先消除这个可证明的结构性空转，再选择值得付出 GPU 时间的最小组合。

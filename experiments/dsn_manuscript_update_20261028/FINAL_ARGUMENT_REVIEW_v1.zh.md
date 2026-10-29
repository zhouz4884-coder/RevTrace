# RevTrace DSN 工作稿：最终论证与取舍独立评阅 v1

2026-10-29。只读评阅当前 `core_draft.tex` 及其全部可达章节，以及已有近邻阅读与端点说明；不改正文，不启动网络、远端、CPU/GPU 实验。本轮聚焦论文贡献单位与论证，不做历史源码审计。

评阅时，新原生证据是四个已有开发来源、两次 fresh-process、两臂共 16 格；最终实现冻结后的四个新 speaker 独立确认尚无结果。因此下面所有 66.42975 s、6/8 等数字都明确属于开发证据。后续新来源结果应独立加入，不把开发来源重命名为 held-out。

评阅完成前，主执行方确认最终方法已在新来源元数据选择前冻结，新四 speaker 为 S0908/S0916/S0913/S0905。这个程序足以把随后结果定位为最终方法的新来源确认；结果只改变实证强度与适用范围，不需要再更改贡献机制。ready-only、完整调用、内容端点、条件保证以及更细组件停止门已完成各自设计选择。本评阅不把它们重新降回“尚待构思”，也不要求重启缓存工程。

## 总体判断

**现在有条件形成一篇清楚的系统论文，但论文的“前门”和新增证据尚未接上。** 方法与评价已经加入完整 native 调用保留，而摘要、引言贡献和结论仍主要说旧 R/S 协调，最后把 native 写作“暴露成本的适配”。这会让读者把最有服务价值的新证据当成临时追加的第二项目。

我建议唯一的贡献单位是：**在递归消费可信反馈的生成服务里，依据实际完整输入依赖，协调仍可用的已执行调用与已交付整视图；可信选择继续决定结果，版本变化不再自动抹掉这些对象。** core 的 R/S 分解说明两个动作边界不能互相代替；native 的完整调用实现说明同一资格原则可以保留原 learned corrector 已经执行的工作，并在固定选择任务下改善单条反馈链服务。这是一个具体组合与应用贡献，不要求每个原语从零产生，也不要求我们自己构造的完整组合替代路径失效。

下面五项按重要性排序，均可直接通过写作、现有材料选择或已计划的独立确认落实。

## 1. 统一摘要、引言贡献与结论：一项合同，两种保留对象，两类实测

**问题位置：** 引言第 60 行起的系统介绍及第 69 行的贡献列表；摘要最后两句；结论。当前 C3“a working protocol and evaluation”太宽，native 只作为附带适配出现。反过来，若把 full-call、packet、encoder-cache 分别列成新机制，会把论文拆散。

建议保留当前标题，不另起泛化范围更大的标题。引言系统介绍可替换为：

> RevTrace reconciles both executed calls and delivered whole hypotheses with each new trusted feedback state. An executed call remains eligible when its complete frozen input has a valid dependency witness from that state; the Consumer separately checks whether its current whole hypothesis remains supported. These decisions retain work and service without changing the protected selection that determines the next feedback state. We instantiate the same eligibility principle with recorded continuation paths in the core runtime and with input-confirmed full calls in a native correction pipeline. Physical retirement remains a separate decision for work with no remaining use.

贡献列表建议替换为以下三项，前两项是技术设计，第三项是实测系统实现；不写“我们证明组合普遍必要”：

> * A feedback-state contract and executable sufficient witnesses for retaining owned computation across trusted updates, including recorded continuations and input-confirmed full calls. The witnesses bind complete state, actual audio frontiers, frozen inputs, and execution identity.
> * Coordination of computation retention with whole-hypothesis consumption. A supported ahead view survives a compatible root application while the certified lane advances; incompatible views remain withdrawable and provisional text gains no certification merely by being retained.
> * An implementation and service evaluation that hold the selected feedback task fixed. Factorial controls expose the computation/consumption interaction, and a native published correction pipeline tests whether input-confirmed full execution improves timely service while preserving its original correction and complete state transitions.

这里不把 WAL、K、恢复单列为新算法。它们在实现与成本部分回答“这些对象如何实际安装、隔离与释放”，服务于同一个贡献单位。

结果预览应在新来源确认后同时给 core 与 native 各一句。当前开发数字若先用，可准确写成：

> In the independent core stratum, joint retention eliminates the observed frontier withdrawals and adds 26.645 s of original deadline credit over 714.110 s offered, while all arms preserve the same selected histories. In a separate single-chain native development study, full-call retention raises credit from 37.5 to 66.29375 s over 66.42975 s offered per arm and passes whole-run D2/C8 in six of eight runs, with the two EOS misses retained. These studies test different obligations: the former isolates whole-view continuity, and the latter tests timely execution of the unchanged native feedback task.

**最终新来源尚未出结果时，不把上句的 native development 改成 independent。** 出结果后优先用新来源的完整分母、通过数和全文支持作为预览，旧开发数字退到开发说明。

结论最后两句可改为：

> The core experiments show why retaining computation does not itself preserve already delivered service. The native implementation shows how confirming a call's complete input can retain original correction work without requiring its own predicted output to be correct. Together, these results establish a concrete composition of dependency reuse, protected feedback, and whole-view consumption, with measured timing and capacity boundaries.

## 2. 不把充分条件命题当成独立新理论；把 native 的“确认输入、选择结果”讲透

**问题位置：** `03_continuation.tex` 命题之后，与 `03_native_extension.tex` 的连接。两个短命题本身都容易被读成“相同输入当然可接续”“代码分支保留视图当然不会撤回”。它们有价值，但价值在于给具体实现一个可检查的合同，而不是一般增量计算定理的首创。

当前形式化强度基本合适：声明完整反馈 state、同 frontier、实际完整执行路径、冻结在途输入；没有把独立浮点重放等同于已有执行，也没有升级成最小充分条件。应继续保留。需要新增的是两个实现为何属于同一关系、为何需要保护的对象不同。

在 native 小节开头增加或替换一个短桥段：

> The native implementation uses a direct witness for the same dependency relation. A conditional call starts from a frozen prediction of its parent's complete closed state. When the original parent selection produces exactly that state at the same frontier, the already owned call is a supported successor. This confirmation concerns the call's input. Its protected original corrector still determines its output, which may differ from the call's own identity prediction for a further successor. Thus prediction error at the next edge does not retroactively invalidate an already confirmed input edge.

随后用 3 个编号动作或一个很小的时序示意即可，不需要再开一张大总览图：

1. 父调用尚在 C/U 时，typed identity projection 给出 `hat P_j`，子完整调用以该冻结输入启动。
2. 实际选中 `P_j` 后比较完整输入、frontier、epoch、contract 与外部 owned-job 身份；匹配则保留正在执行或已完成的子调用。
3. 子调用自己的 original C/U 产生 `P_{j+1}`；`P_{j+1} != hat P_{j+1}` 不否定它从 `P_j` 出发的合法性，但会约束后继调用。

应明确“protected selection independent of prediction”指选择逻辑与权限独立于 identity predictor/Consumer，**不暗示每个被采用结果都必须由另一份独立神经调用再次重算**。core 和 native 的保护域实现不同，不能让“independent selection”在行文中无声变成“必须另一个 GPU 再做一遍”。当前 native 段落已经保留 original C/U，改清这一点即可。

本轮 99 个真正 model-in-flight 的 promotion、12 个自身预测 end 不同、20 个已知坏 start 在 C 前阻断，最适合挂在这三个动作之后作为对应观察。不要把“13 个 packet 组件控制”与“12 个 service promotion”相加，也不要用 1154 状态旧模型声称证明新 native 全栈。

## 3. 把 DSN 服务价值写成两个可判定问题，而不是争抢一个总加速比

**问题位置：** 评价引言与小节顺序、摘要服务主张、native 表头。当前证据已经可以回答两个互补的系统问题：

* **已交付且依赖仍有效的进展，在可信更新后是否还实际可用？** core 的整视图、D2 读点、兼容撤回和实际 Consumer 给出答案。首次信用不能代替这项性质。
* **保留已执行且输入被确认的原完整调用，能否让相同可信任务及时完成？** native 以相同 C/state/IDs、原 offered 分母、同资源强保守执行和实际 board energy 给出答案。

建议评价开头增加：

> We evaluate two service obligations under unchanged selected feedback histories: retaining dependency-valid service that has already reached the Consumer, and completing the next selected transition before its original deadlines. The core factorial study isolates computation and whole-view retention. The native study tests input-confirmed full execution of the original correction pipeline. Timing, content support, and energy are reported separately for both.

这个组织能化解两个真实边界，无需回避：headline 15 格全 D2 fail 不抹掉持续可用问题；native 没有兼容 ahead view 也不抹掉固定原任务的时效收益。但不能把 native 6/8 达标“借给”core 的 C2，亦不能据 core 的 C2 给 native 宣称新的 R×S 交互。

native 当前主表有 C50、Pass、原 credit、全文支持和能耗，选择合理。建议把 `Same-$G$ support` 改为可直接读懂的 `Whole-text support`，caption 定义“first covering actual view at G versus later complete Canonical at exactly G”。`G` 的说明目前在表后，读者先看表时会遇到一个未定义字母。保留 6/8 与两条 EOS 的具体 D99，比只放 C50 更能传达服务目标。

“66.29375 s”是原音频义务信用；“56.287875 s”是后验整个首覆盖文本支持的信用子集；它们都不是新增转录字符量，也不是 human correctness。当前原文已经正确分开。主文只需一个短段说明，详细 aligned 子集 51.287875/28.5、unchanged-text 9/5 等放紧凑补表，避免真正的端到端收益淹没在指标沿革里。

新四 speaker 确认完成后应原样报告所有来源、重复、EOS 与每对变化。若有回落，明确限定工作负载/时序窗口；不凭旧开发收益绕开新结果。**完成这项已冻结确认就足以决定当前 native 论证强度，不建议再加盲目模型/负载矩阵。**

## 4. 有选择地压缩：保留会改变结论的阴性，移走实验历史叙事

**问题位置：** 评价约占数页，密集出现 110、36+12、24、19、旧 14 格，以及每轮测量的来源沿革。完整记录应在 artifact，但主文不需要像研究日记。

建议主文顺序：**合同与见证 → core 五臂与实际连续性 → native 原完整任务的独立确认 → 48 格负载/时序边界 → 简短物理释放支撑**。若为了少改版维持现有顺序，也至少把 native 从“最后一个泛化小节”提升成明确第二项服务评价。K 不应把 native 隔在一个长的取消故事之后。

可执行取舍如下：

* 保留 H3 五行表、完整组合正控、实际 37 字符的完整 2-s case、48 格图、native 主表及原选择保真。它们各自承担不同主张。
* c12 阴性保留在图内，并用一段约 80–100 英文词说明 12/12 D2 fail、预设强见证不成立、停止；冻结搜索程序和每个区间计数移 artifact。不要删掉阴性，也不必在摘要专门讲“保留阴性”来代替具体服务发现。
* K 保留 96/96 同输入完整后继文本、R1 新增期限行 6/6/1、一次 request/ACK/drain 链及错峰混合结果；多轮 raw-support 扣除、675 对完整定义留脚注/补表即可。K 是执行支撑，不是第四项独立创新。
* ready-only 6.5 versus full-call 8.0 的单源 pilot 用一句保留，说明为何选择完整调用；不再画阶段优化竞赛。encoder 组件保真通过但净慢的结果留 artifact 中的设计选择表，不插入正文新机制。
* 旧两完整副本的容量阴性保留简短一句与范围；明确旧 warmup/Consumer 不同，绝不包装成新版对旧版的因果胜利。它限定多源容量，不否定新单链关键路径。
* 恢复只保留与 outstanding input、既有事实恢复相关的实现边界及旧冻结原型来源。既然当前没有新 native 全栈 crash 证据，就不把正文改成以 crash 为 headline 的 DSN 论文。

这能腾出约半页解释“确认输入、选择结果”和新来源确认，而非继续增加页数。

## 5. Novelty 应正面落在组合对象与合同；正控与近邻比较只需准确一次

**问题位置：** 引言近邻段、Related Work、Full Standard 说明。当前描述已避免把作者自己的组合正控误当外部先例，这是正确的。仍可减轻防御感：身份定义一次，随后用实验事实说话。

建议把表内名称改为 `Complete alternative (ours)` 或长度允许时 `Full composition (ours)`；首次正文说明共享底座、另一 policy instantiation。没有必要把 680.760 versus 667.530 的差值当贡献。它回答“完整能力是否只依赖这一种调度选择”，四臂回答“两个保留动作各做什么”。它不提供独立代码复现，也不改变本文完整组合的作者归属。

Related Work 的核心定位段可替换为：

> Dependency reuse, provisional information, and speech speculation provide the foundations for RevTrace. Our contribution is their concrete composition around a recursively consumed, protected feedback state: a previously executed complete call must remain supported by its actual frozen input, and an already delivered whole hypothesis must remain supported when the selected root is installed. The core and native implementations expose different sufficient witnesses for this relation while preserving the original selected task. Their service evaluation measures both retained availability and timely execution, including the cases in which additional computation or retention does not improve capacity.

随后分别准确承认：IU 的 active/committed 与依赖撤销，Adapton 的依赖复用，SSBD 已联合 draft 复用与 display-only masking，PredGen 已做演进语音输入上的下游推测。不要写“以往方法只优化计算、不考虑显示”，不要把“不同应用领域”当全部差别。

既然现在已经实际使用完整 conditional calls，已有精读 memo 的 RelayS2S 也值得在 related speech paragraph 用 1–2 句纳入；不需要为此新开文献搜索。可用的已有条目是 `mai2026relays2s`，来源在 `STAGE_NEIGHBORS_20261029.bib`。准确区别是它用 learned verifier 的快路径前缀约束慢路径后续生成，而这里输入确认后仍执行原 C/U 并保留完整反馈状态；不要声称首个 dual path/handoff。Alignment Drift 可一条引用支持音频状态不能只用文本表示，无需扩写第二套 ASR decoding 综述。

**不建议出现的主张：** “联合普遍必要”“最小充分条件”“首次计算与显示协调”“任何可信更新下都不回撤”“完整组合独有可行 SLO 区间”“native 证明整个 core 的恢复/物理租约”。**可以肯定的主张：** 我们提出并实现这套具体组合；在所声明接口内给可执行充分见证；实际显示与真实调用的使用资格得到协调；在固定选中任务下测得服务收益，并保留测得边界。

## 当前可直接执行的交付检查

1. 等现有新来源确认完成后，更新 native 主表和摘要/引言预览；严格把开发与确认分块，不改失败/EOS 分母。
2. 将前三处 front matter 与结论改成同一贡献单位；补上 native 输入/输出预测区别的短桥段。
3. 按上面的最少主文对象压缩 K、c12、组件/旧容量沿革；保证每个保留数字确实服务一个主张。
4. 全篇以“完整选中历史相同”作为质量任务保持证据，以 first-credit、持续可用、全文支持、真实精度和能耗各自的定义报告结果。之后做最终编译与逐页 QA。

一个口径细节已独立核对：`timely_continuity_v1/RESULTS_v1/RUNS.json` 中 c16 R-only 的及时撤回**事件**是 10/11/9，而及时 interval-loss **windows** 是 10/12/9，第二次重复一个事件涉及两个区间。当前正文写 `10/12/9 timely compatible loss windows` 是对的，不应据旧摘要改成 11。

本评阅没有提出额外 GPU 研究分支。当前最重要的提升来自把已做成的 native 执行能力纳入同一论证、完成已经冻结的独立确认，并让主文选择清楚，而非再堆一个实验目录。

辅助检查：已运行 `uv run --no-project --offline python -B C:/Users/LENOVO/.agents/skills/latex-paper-en/scripts/analyze_logic.py core_draft.tex --motivation-thread`，退出码 0。其启发式也提示 front matter/结论衔接，但未识别手写贡献列表，存在误报；本报告结论以逐段人工阅读全文为准，不以脚本标记计分。

# DSN 正文：近邻定位、基线身份与贡献边界

日期：2026-10-31。对象为 `4411513` 对应的 v2 稿件及本轮写作修订。此项只做原文、公开源码与已有本地证据的定位；没有执行模型、访问实验机或修改正文。本文中的比较是对已声明机制和评估范围的比较，不是“没有写到便不能实现”的能力排行榜。

## 我建议采用的贡献单位

**RevTrace 在保持原反馈选择任务的前提下，分别判定完整调用输入资格、选中转移权威和当前整视图支持，再据此协调保留、撤回和安装。** 计算继续合法，并不意味着安装一个可信快照时已经交付的进展会自动保住。当前视图失去支持，也不意味着某个尚未知的未来完整输入已经被反驳。这两个方向的不等价，比“相同输入可以复用”更能说明实际设计难点。

这是一项具体的应用与组合贡献。不要把它改写成第一个双前沿、第一个计算/显示协调、第一个版本化保留或新通用增量计算定理。也不必因为这些祖先存在，就将已建立的合同、动作组合和服务证据降成无价值工程。

## 七行近邻表：它已经做了什么，我们具体增加什么

| 近邻与原文锚点 | 必须承认的既有机制 | 本稿的具体比较对象与证据边界 |
|---|---|---|
| **增量对话 IU**：[Schlangen–Skantze 2011](https://aclanthology.org/2011.dnd-2.11.pdf)，§§3.3.2–3.4.2、5.2.1–5.2.2，Figs.12–13；[出版记录](https://aclanthology.org/2011.dnd-2.11/) | 异步模块、支持关系、撤销传播，newest committed 与 active right edge 分离；commit 是该 unit 不再撤销的承诺。 | 本稿认证是原选择协议接受，不保证文本永不修订。要交代完整神经状态和独立可信安装时的整视图动作，不能只重命名两条前沿。未做 IU 原系统性能复现。 |
| **Adapton / Nominal Adapton**：[PLDI14 作者全文](https://matthewhammer.org/adapton/adapton-pldi2014.pdf)，§§2–3.2，Figs.4、6；[OOPSLA15 原文](https://arxiv.org/html/1503.07792v2)，§§2.1、4、5.2 | 动态依赖、已记录读取值检查、按需修复和跨上下文复用；names 加参数和依赖检查定位合法复用。 | 同输入复用、版本变化不全弃已有坚实基础。增量在受保护神经反馈接口和实际消费行为的结合；不移用其 from-scratch 定理证明未建模 GPU 推理。未做 Adapton 库移植。 |
| **SSBD**：[v2 全文](https://arxiv.org/html/2509.21740v2)，§§3.2–3.4、Tables3–4、App.A.1–A.2；[身份](https://arxiv.org/abs/2509.21740v2)，2026-01-04 版本 | 在更新输入上重新验证旧输出 draft；display-only mask-k 保留内部复用；有已评测的 β=0 版本。 | 不能声称首次计算/显示联合，也不能靠默认有偏贬低它。RevTrace 以完整冻结输入和实际路径保留调用，并在独立选中根应用时保护当前整个兼容视图。不是 SSBD 作者实现的直接性能比较。 |
| **PredGen**：[COLM25 官方 PDF](https://openreview.net/pdf?id=2Kl8Ztw6wk)，§3/Algorithm1、§§3.1–3.3、App.B.2；[arXiv v2](https://arxiv.org/html/2506.15556v2) | 在用户输入尚在变化时生成回答及首句 TTS，后续输入验证候选，最终可使用预合成语音；不同 verifier 的保证不同。 | “先做后确认”、ASR 修订与预生成均非首次。本稿固定原纠错反馈选择，考察完整调用和实际已显示视图；没有复现语音对话基准，不宣称跨任务速度胜出。 |
| **StreamCorrect**：[官方全文](https://aclanthology.org/2026.emnlp-industry.142.pdf)，Fig.1/§3.1，pp.2393–2395；§4.5，p.2397 | learned corrector 选择当前段，并将选择反馈给后续 ASR；已有完整管线副本和调用级并行。 | 本地是固定 500-ms/no-VAD 的忠实边界适配，保留 recognizer、C/U、token 顺序及完整状态；双完整副本对照是我们写的调度方案。原论文 benchmark CER、工业负载与本地结果不互换。 |
| **Retire**：[v1 全文](https://arxiv.org/html/2610.01160v1)，§§3.1、5–6、8；[身份](https://arxiv.org/abs/2610.01160v1)，2026-10-01 预印本 | runtime 指定 SUPERSEDE 的 scope、版本、修订上下文与执行合同；联合撤权、受界执行、已完成状态继承与异步回收。 | 泛称“不同生命周期”和“失效与保留联合”与它高度重叠。本稿补具体反馈合同中的资格推导和整视图应用义务；parent-cancel 只是一项自建保守策略，绝非完整 Retire 复现。未验证同行评议 venue。 |
| **OCC / WAL / RPC**：[OCC DOI](https://doi.org/10.1145/319566.319567)，§2；[ARIES DOI](https://doi.org/10.1145/128765.128770)，§§2–3；[RPC 作者记录及 PDF](https://www.microsoft.com/en-us/research/publication/implementing-remote-procedure-calls/)，§3.2–3.3 | 执行/验证/提交分离，日志持久化与恢复，调用身份及重复检测均为既有机制。 | 这些是支撑，不是单独新贡献。本文必须定义日志中究竟绑定哪些完整输入、选择、身份与消费义务；不能由“用了 WAL”推导整个异步服务正确。 |

SSBD、PredGen、StreamCorrect、Retire 的范围差别均不意味着它们理论上无法扩展。最有说服力的论证是本稿实际规定并测量了哪个额外服务行为，而不是做一个大面积打叉的能力表。

## 基线身份：正文至少给出这张映射的压缩版

| 正文中的对象 | 应使用的身份 | 能回答什么；不能回答什么 |
|---|---|---|
| IU、Adapton、SSBD、PredGen、Retire 等 | 外部发表机制或明确标注的预印本近邻 | 论证已有基础与具体缺口；没有运行其作者栈便不提供系统间性能排名。 |
| StreamCorrect 原管线及其本地接口 | 外部原任务的受控适配 | 核对完整原始调用、选择与反馈保持；不把本地 fixed-chunk/no-VAD 设置叫作者 benchmark 复现。 |
| Native Conservative | **自建保守正确方案**，同两副本、同 Consumer、同 C/U、同持久化 | 比较是否允许 conditional full call；不是削弱为单 GPU 或去掉恢复的弱对照。 |
| Core R0S0/R0S1/R1S0/R1S1 | 本研究同执行/验证/提交基座上的机制消融 | 隔离计算保留与整视图保留的作用。R0/S0 仍然正确，只缺本文要提供的保留能力；不能宣称两者对一切安全系统都必要。 |
| Full composition (ours)，旧称 Standard full | **作者完整组合的替代策略实现与正控** | 相同完整能力应产生相近行为。不是外部先存 SOTA，也不是独立重写神经栈；同效支持该组合可由传统机制实现。 |
| parent-cancel、watchdog、trusted-cover | 同 actuator 的自建控制策略 | 比较本执行路径的取消选择。不能借名字继承 Retire/InferCept 全系统身份；若覆盖和 watchdog 同效，应保留同效。 |

本地核查依据：`.execution/lp1_runtime/runtime/src/revtrace/standard_safe_async.py:1–6` 自述为 independent conventional policy adapter、共享 executor/commit core，明确不是外部 serving system；该文件是旧 core 身份说明，不给后续版本换身份。最终 native 的 `experiments/dsn_native_resilience_20261030/source_v2/resilience_policy.py:1–5` 明确两臂共享 coordinator 和 synchronous before_commit，差别为 conservative 仅从 canonical starts 调度，full-call 允许 legal conditional tail，均不改变 C/U。其实际源为 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`；归档 GitHub HEAD 不是它的执行身份。

## 建议可放正文的小表

若篇幅紧，正文只保留下面四行“设计对象”表，将七行文献表留在 artifact；它比打叉表更容易阅读，也不会虚构负能力。

```latex
% Existing keys only; place near the comparator paragraph or Related Work.
\begin{tabular}{@{}lll@{}}
\toprule
Family & Preserved object & RevTrace obligation\\
\midrule
IU / Adapton & Units / dependency computations & Full-call and whole-view guards\\
SSBD / PredGen & Draft tokens / candidate replies & Fixed original feedback selection\\
StreamCorrect & Selected correction prefix & Cross-call overlap and actual use\\
Retire & Contract-valid successor state & Feedback-derived call eligibility\\
\bottomrule
\end{tabular}
```

表中 preserved object 只是原文的主要对象，不是对其可表达能力的上限；应在 caption 明说。OCC/WAL/RPC 可保持正文短段致谢，不值得为“基础机制存在”再占表格一行。

## 两段可贴正文的英文建议

以下为建议文本，不自动替换现稿；原引用键不改。第一段说明研究祖先和本稿额外义务，第二段针对最接近的现实反馈/执行系统。两段合用约 300 词；如正文篇幅紧，可删独立重复的泛化边界句，不删正面承认。

```latex
Incremental dialogue models already separate committed information from
an active right edge and propagate revocation through support relations
\cite{schlangen2011incremental}. Adapton and Nominal Adapton preserve
computations by checking recorded dependencies, names, and arguments
\cite{hammer2014adapton,hammer2015names}. SSBD further coordinates internal
draft reuse with display-only masking, including an unbiased configuration
\cite{zeng2026ssbd}; PredGen verifies candidate replies and reuses
pre-generated speech as input evolves \cite{li2025predgen}. These are
direct foundations for RevTrace. Our contribution concerns their
realization under a protected neural feedback task: complete executed
calls must retain valid inputs without changing original selection, and
applying a newly selected state must separately decide whether the
Consumer's current whole hypothesis remains supported. Neither a birth
version nor a visible-text match supplies both decisions. The resulting
retention property permits required corrections; it does not promise an
immutable transcript or human-correct provisional content.

StreamCorrect supplies the recognition--correction--feedback task used
in our controlled native adapter \cite{vu2026streamcorrect}. We preserve
its original calls and selection while changing conditional scheduling
and consumption; our Conservative and Full-call policies are author-built
comparators with the same complete workers. Retire jointly addresses
revocation, valid state inheritance, and physical reclamation after a
runtime-selected version transition \cite{zhang2026retire}. RevTrace
specifies the feedback-dependent eligibility and whole-view actions
around an unchanged selected task; a parent-version cancellation control
is not a reproduction of Retire. Validation, durability, and duplicate
handling build on established concurrency, recovery, and RPC mechanisms
\cite{kung1981occ,mohan1992aries,birrell1984rpc}. The full-composition
positive control therefore tests whether a conventional policy
instantiation can realize the same design, rather than claiming that
an external system already contained it.
```

## 主张—证据映射及写作动作

| 主张 | 当前证据 | 写作决定 |
|---|---|---|
| 固定原选择任务下，计算保留和整视图保留保护不同对象。 | core 110 的预定 Qwen/ρ1/stagger 层：单 R 的 17 次撤回、联合 0；完整历史核对；三 cohort 交互。 | 作为核心机制证据；不能说所有场景交互为正或全部 SLO 通过。具体数值以冻结源结果为准，本次未重跑。 |
| 首次及时交付与之后仍可用是两个服务属性。 | 真实完整 2s interval，37 raw chars，1.444→1.544→3.720；全 48 workload 含 c12 阴性。 | 做首页钩子和机制后果；病例来自 c16 过载，不当自然发生率或联合臂逐事件反事实。 |
| 原始完整 C/U 可在输入后确认的条件执行中保留。 | native 独立确认与最终版本匹配 32 分列；最终 4f 6/8，常驻 7/8；完整状态/C/IDs 保持。 | 与上述三判断连成同一个系统能力；不把旧 8/8 给新版本。 |
| producer 存活和此前接受的对象权限不同。 | 完整 buffer 正负控制以及 sealed channel/fencing、实际安装消费证据；reader 修复后的不变 raw 复算。 | 是完整实现的证据，不独立声称新 WAL/fencing 理论；主文一句披露 reader 修复，原失败保留 artifact。 |
| 本方法提升临时文本的实际可用性。 | 最终4f已有同前沿全文支持信用 22.5→51.0s；本轮 CPU recount 将补 resident 与连续性。 | 仅用最终冻结 recount 结果，分开人工准确性、同前沿事后支持、前沿信用和新字数；未完成前不写新数字。 |

## 最大 novelty 风险及我自己的判断

**最大风险不是 Standard 正控同效，而是审稿人将全文压缩成“给推测调用做 memoization，再给 UI 加一个 guard”。** 如果方法只列三个检查，实验只列总 token/总回撤，这种印象是合理的。要让三个检查在同一个具体交错上产生不同动作：当前 view 撤回、未来完整输入 UNKNOWN 而调用继续；随后输入匹配、保留同 UID；原 C/U 决定真实输出，即使自己的下一预测错；最后 producer 退出只阻断未来消息，不销毁已取得的合法 buffer。这个交错把“接口判断”变成了非平凡可实现的协调行为。

**第二风险是 Retire 和 SSBD 的直接重叠被写得太浅。** Retire 已经明确联合 invalidation 与 preservation，并讨论 authority/resource lifetime 分离；SSBD 已经明确处理内部复用和显示策略冲突。因此不要再把泛化后的“跨层协调”本身当成独占贡献。贡献句必须包含原反馈选择保持、完整调用输入和整视图在可信安装边界的动作；用 R-only 更差和实际短语消失证明该具体组合值得研究。

**第三风险是读者以为通过换任务或换端点取得收益。** 原选择保持、双副本同资源、所有 offered/EOS 和共同能耗窗口都应在主表附近一次说全。各版本和 CPU 事后分析的身份压成简短映射，调试流水移 artifact。必要的失效结论保留在统一边界段，不让每个正面结果都被重复列历史失败打断。

我不建议现在另建 SSBD、Retire 全作者栈或更多“text-only/epoch-only”伪基线。它们不能直接保持本稿的原反馈合同，完整复现会成为另一项研究。当前最有价值的补强是：把同一三判断交错画清、短算法可执行、同任务因子实验和原生服务合为一条论证，并正面展示完整传统实现可得到同一能力。本文可以主张具体新组合及其可检验价值，无需主张每个组成思想从零诞生。

## 核验状态、来源与限制

- 工作流：按 `nature-academic-search` 的 citation-verification 路由。当前工具目录未提供 academic-search MCP；沿用已归档的作者/出版方全文核验，并以 web 主源重新打开 SSBD v2、PredGen v2/官方 COLM PDF、Retire v1、IU 出版记录、Adapton 作者页及 RPC 作者记录。没有绕过访问挑战。
- OpenReview forum 当前转为验证页面；官方 `pdf?id=2Kl8Ztw6wk` 被索引的全文首行确认 COLM2025。完整机制使用可访问 arXiv v2 与既有全文阅读记录，不将 forum 挑战当成论文不存在。
- OCC 与 ARIES DOI 当前 web 打开失败。OCC 的一般 validate-before-write 和 ARIES WAL 身份沿用现有已核验参考文献与 [20261028 审查](D:/VLA_QWEN/RevTrace/experiments/final_evidence_integration_20261028/RELATED_WORK_AUDIT.md)，本轮不宣称重新通读两篇全文。RPC 当前作者记录可访问；具体调用 ID 段落沿用已完成的全文依据。
- 复用的强原文记录：[ROUND3 近邻精读](D:/VLA_QWEN/RevTrace/experiments/dsn_manuscript_update_20261028/NOVELTY_NEIGHBORS_ROUND3.zh.md)、[ROUND4 贡献定位](D:/VLA_QWEN/RevTrace/experiments/dsn_manuscript_update_20261028/NOVELTY_POSITIONING_ROUND4.zh.md)、[StreamCorrect 正式全文阅读](D:/VLA_QWEN/RevTrace/experiments/physical_retirement_20261028/literature_review/streamcorrect_fulltext/READING.md)、[基线身份](D:/VLA_QWEN/RevTrace/experiments/physical_retirement_20261028/literature_review/BASELINE_IDENTITIES.md)。旧文档中的待做机会和旧数字属于当时状态，不当作今天执行结果。
- 本文没有证明不存在其他相同组合，没有获得任何外部系统新性能数据，也没有将未测量的能力写成不可能。没有超过单一来源 25 词的直接引文；机制与建议正文均为归纳和本项目定位。

# v15 独立语言审查

审查 ID：DSN-READABILITY-V15-LANGUAGE-20261105；日期：2026-11-05。

v14 的科学主线和证据边界已稳定。最值得做的是降低读者跨对象和跨执行实例切换的成本，不需大幅重构或机械词数配额。本次发现均可定点修复；未发现必须新增实验才能解决的语言层阻断项。

## 范围与方法

- 基线：`Paper_DSN/revisions/20261104_dsn2027_release_v14`；父任务给定 GitHub ref `3bcbb7638e6d9106965e4274a6c388a0186ab7ee`。本子任务核验本地文本，不把给定 ref 当作独立远端状态验证。
- 已通读 main.tex、18 个实际可达 section TeX、其引用的 native_reliability.tex、PDF 第 1–12 页，以及两份附件全文。
- 只读审查；仅写本报告及同名 JSON。未改稿件或运行时，未运行模型或实验。
- 方法：按读者问题顺序通读，建立术语表，逐句检查指代与主张边界，再扫描正文多于三位的小数。
- 不设机械改词配额；下面 10 项为可审核的定点替换。是否等长必须由实际编译决定。

## 术语表

| 保留/规范名称 | 决定 |
|---|---|
| avoidable withdrawal | 保留命名；结论回声用 prevent avoidable withdrawals，保留 compatible application 条件。 |
| complete-call input eligibility [EL] | 与 own prediction correctness、selected-result authority 分开；R 是实验保留动作开关。 |
| original selection authority [AU] | 原始 Correct/Update 决定完整选中结果；不得用 certified 来表示人工转写正确。 |
| whole-view support [SUP] | 用于实际 Consumer 的当前整视图；S 是实验保留动作开关。 |
| first delivery / continued availability | 保留区别；Figure 1 两臂独立轨迹且 RevTrace 首显晚 27.4 ms。 |
| predeclared Qwen, rho=1, staggered setting | 可用 setting 替 stratum；不能变 held-out benchmark 或泛化到所有负载。 |
| Alternative joint policy (positive control) | 共享 execution/commit substrate，不能称 independent implementation。 |
| metrics | 替 endpoints 作为实验测量统称；公式、聚合、时钟保持。 |
| right-censored | 普通英语解释停止观察且不据此声称恢复；不得以 bounded 代替。 |
| speaker-paired bootstrap / confidence interval / selected-trace refinement | 有精确技术意义，保留并解释，不因降低术语量而删去。 |

## 10 项优先替换

### L01 — 把全文最有辨识力的反直觉结果放在让步关系前；同时把 stratum 的实际条件说清。

- 优先级：high；PDF 第 1 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/01_progress_introduction.tex:36–41`。

原文：

> In a predeclared 24-speaker stratum,
> computation retention improves timely audio coverage while increasing
> backward movements of the displayed audio frontier, or \emph{frontier
> withdrawals}, from 12 to 17. Coordinating computation and view retention
> yields zero. RevTrace connects valid execution to continued availability
> at the actual Consumer without changing which original result is selected.

建议：

In the predeclared 24-speaker Qwen setting with $\rho=1$ and staggered arrivals, computation retention alone increases \emph{frontier withdrawals}, or backward movements of the displayed audio frontier, from 12 to 17. It does so despite improving timely audio coverage. Joint computation and view retention yields zero withdrawals in that setting, without changing original selection.

理由：先给 12→17，再给及时性改善这一让步，读者能先记住冲突。明确 Qwen、rho=1、错峰，避免把零撤回扩到所有 24-speaker 配置。

保护边界：仅为该预先声明设置；不暗示全负载零撤回或稳定速度优势。若第一页过满，可将条件压为对 Figure 3 的短参照，不能删除对应条件。

### L02 — 贡献第二项目前只说 argument connects，未告诉读者验证怎样支撑协调机制。

- 优先级：high；PDF 第 1 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/01_progress_introduction.tex:70–74`。

原文：

> \item A joint coordinator that preserves the original selected transition
>   relation while retaining eligible calls and supported whole views.
>   Its conditional selected-trace argument connects early execution,
>   durable selection and supported process failures
>   (Sections~\ref{sec:continuation}--\ref{sec:protocol}).

建议：

\item A joint coordinator that preserves the original selected transition relation while retaining eligible calls and supported whole views. Its conditional selected-trace argument is complemented by bounded normal- and failure-state exploration and receipt-based checks of actual executions (Sections~\ref{sec:continuation}--\ref{sec:protocol}).

理由：把论证、有界探索、实际执行收据检查三种支撑分清，比加入状态总数更容易评估可信度。

保护边界：保留 conditional 和 bounded；不合并 6,231 与 14,074，不称 whole-program proof，不把 36 trials 称为 36 fault injections。

### L03 — 先讲两种 worker 部署，最后才解释反馈依赖，增加首次阅读负担。

- 优先级：high；PDF 第 2 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/02_contract.tex:27–35`。

原文：

> An immutable audio stream supplies a protected selection path producing
> \emph{Canonical} facts and a \emph{Private} path computing and displaying
> provisional hypotheses. These are logical roles. The core runtime assigns
> them to separate Private and Authority workers. The native runtime uses
> two complete original recognizer--corrector workers; either can execute
> a selected-input or conditional full call. Selection can change the next call's
> input: StreamCorrect feeds its chosen correction into subsequent
> ASR~\cite{vu2026streamcorrect}. We coordinate this dependency as the paths
> advance asynchronously.

建议：

An immutable audio stream drives two logical paths: protected selection produces \emph{Canonical} facts, while a \emph{Private} path computes and displays provisional hypotheses. A selected correction can change later call inputs; for example, StreamCorrect feeds its chosen correction into subsequent ASR~\cite{vu2026streamcorrect}. We instantiate these roles in two execution settings. The core runtime uses separate Private and Authority workers. The native runtime uses two complete original recognizer--corrector workers, either of which can execute a selected-input or conditional full call. Both coordinate this feedback dependency as the paths advance asynchronously.

理由：顺序改为共同角色→依赖原因→两个实例。保留 Private display 和完整 recognizer–corrector，不把 native 写成顺序执行。

保护边界：不加 demonstrate generality、unified code kernel 或 universal portability；两者是不同充分实现与执行合同。

### L04 — 三个 lifetime 连续词典式定义且 Their decisions 指代抽象，不易形成具体因果。

- 优先级：high；PDF 第 3 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/02_contract.tex:89–93`。

原文：

> The \emph{dependency lifetime} determines usability under the current
> root; the \emph{visible lifetime} determines whole-hypothesis retention;
> the \emph{physical lifetime} ends only when execution finishes or drains.
> A new root can change the first two before the third ends. Their decisions
> therefore require separate evidence.

建议：

A feedback update can remove support for a displayed hypothesis while its producer is still running. An already accepted result may remain usable after that producer exits. RevTrace therefore tracks dependency validity, whole-view support, and the physical lifetime separately. That physical lifetime ends only when execution finishes or drains.

理由：用不同对象在不同时刻仍可用的例子解释为何要分开判断。全文其他地方不依赖这三个 lifetime 名称，可减少一次性术语。

保护边界：may 保留条件性；不写 terminate lifetimes，不把 unsupported view 当成未来输入已被 refuted；物理 drain 仍是释放条件。

### L05 — 两句短语的范围需说清：Used calls 容易误读，Telemetry and resources are separate 未说相对谁分开。

- 优先级：high；PDF 第 2 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/02_contract.tex:8–57`。

子锚点：第 10–11 行。

原文：

> Used calls must
> faithfully consume their frozen inputs.

建议：

Calls admitted for use must faithfully consume their frozen inputs.

子锚点：第 50–53 行。

原文：

> The adapter declares a conservative representation of \emph{all mutable
> cross-call state that can affect later model inputs, selection, or feedback}.
> Telemetry and resources are separate.

建议：

The adapter declares a conservative representation of \emph{all mutable cross-call state that can affect later model inputs, selection, or feedback}. Telemetry and resource accounting are recorded separately from this inference-relevant state.

理由：第一个替换保留 use 限定，第二个说明资源核算与推理相关状态的关系。

保护边界：不得改为 Every call；故意错输入控制不在忠实执行命题范围内。任何影响模型输入、选择或反馈的资源配置仍必须纳入合同，不因 separately 被排除。

### L06 — 在完整条件列举后，用积极陈述接计时，再明确时限界，读起来更自然。

- 优先级：high；PDF 第 6 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/04_native_resilience_working.tex:32–38`。

原文：

> and sufficient service budgets. This is not an RTO or D2/C8 guarantee;
> loading, replay and recomputation retain their original clocks.

建议：

and sufficient service budgets. Recovery keeps the original input clocks: loading, replay and recomputation all count toward the deadlines. These progress conditions establish neither a fixed recovery-time objective (RTO) nor a D2/C8 bound.

理由：把保证边界接到实际行为上，而非以 This is not 起句。RTO 在首次出现处展开。

保护边界：有限工作、有限支持故障、可读存储、最终释放/加载、终止并推进 frontier 的原调用、公平调度与充足预算全部保留。诚实计时不等于期限保证。

### L07 — endpoint 在本系统中易被理解为 RPC 节点；positive control 的共享底座比改成独立 reference 更重要。

- 优先级：high；PDF 第 6 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_evaluation_core.tex:1–45`。

子锚点：第 1–1 行。

原文：

> \subsection{Design, comparators and service endpoints}

建议：

\subsection{Experimental design, comparisons and metrics}

子锚点：第 40–43 行。

原文：

> The \emph{Alternative joint implementation} is our complete positive
> control: another policy instantiation of the same retention and Consumer
> conditions on the shared execution/commit substrate. External prior work
> and our author-built comparators have separate identities.

建议：

The \emph{Alternative joint policy} is a positive control that instantiates the same retention and Consumer conditions on the shared execution/commit substrate. It is author-built; external prior systems retain their separate identities.

子锚点：第 45–45 行。

原文：

> \paragraph{Endpoints}

建议：

\paragraph{Metrics}

理由：三个改动直接减少歧义，不更换指标定义；用 policy 更准确表明可变部分。

保护边界：禁止 independent reference implementation。若采纳名称变化，需同步 Figure 3 caption、后续 Alternative joint implementation 及 positive-control pairs 的称呼，底座共享说明保留。

### L08 — right-censored 需要普通英语解释；原句 Loss ends...or is censored 容易把观察停止读成真实缺口结束。

- 优先级：high；PDF 第 9 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_operating_boundaries.tex:44–51`。

原文：

> Loss ends when actual coverage returns or is
> right-censored at the next selected root.

建议：

Loss ends when actual coverage returns. If it has not returned by the next selected root, observation stops there without counting that boundary as recovery.

理由：拆开真实恢复与停止观察，保持统计含义。可在括号保留 right-censored，读者不必先掌握统计术语才能理解。

保护边界：不能用 bounded 代替删失；下一 selected root 不是证实恢复，也不是完整缺失时长上界。所有窗口计数与 audio-s×wall-s 缺口值保持。

### L09 — Discussion 直接从比较范围开始，缺少综合性的设计教训。

- 优先级：medium；PDF 第 11 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/07_progress_discussion.tex:1–5`。

原文：

> \paragraph{Evidence and comparison scope}

建议：

A retained computation and a retained view require different evidence. RevTrace coordinates both so that a compatible selected update need not erase still-supported progress.

\paragraph{Evidence and comparison scope}

理由：给读者一个能把方法和结果连接起来的主题句，再进入现有比较边界与迁移义务。

保护边界：compatible 与 need not 均保留；不以 valid/available 二分代替 [EL]/[AU]/[SUP]，不暗示所有条件都能持续服务或达标。若必须补空间，应删现有重复而非删条件。

### L10 — 结论应回扣引言命名的 avoidable withdrawal，而不是换成 unnecessary withdrawal。

- 优先级：high；PDF 第 11 页。
- 源锚点：`Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/08_progress_conclusion.tex:3–5`。

原文：

> Under the declared contract,
> these witnesses preserve selected-task legality and avoid unnecessary
> withdrawals at compatible applications.

建议：

Under the declared contract, these witnesses preserve selected-task legality and prevent avoidable withdrawals at compatible applications.

理由：最小术语回声改动，帮助读者准确复述论文贡献。

保护边界：保留 Under the declared contract 与 at compatible applications；不写 all withdrawals 或 global monotonicity。

## 小数精度

全文实际可达正文中，多于三位的小数仅发现以下两处。它们适合显示为三位，冻结数据及复算精度不变。

- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_native_retention.tex:95–96`：`coverage from 31.0 to 64.118875 of 66.33975~s.` → `coverage from 31.0 to 64.119 of 66.340~s.` 只规范叙述精度，冻结数据保留全部小数；96.7% 不变。
- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_same_source_validation.tex:62–64`：`concatenated as exact PCM into 228.51025/208.1003125-s streams without resets.` → `concatenated as exact PCM into 228.510-s and 208.100-s streams without resets.` 同样只改变显示精度，分开 and 也避免 slash 堆叠。

## 其余指代与名词链修复

这些是低成本可选修复，不要求另起一次结构重写。

- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/02_contract.tex:17–19`
  - 原：Their original input clocks continue through restart.
  - 建议：Accepted inputs retain their original clocks through restart.
  - 理由：Their 的最近先行词是 Supervisor/ledger/Consumer 等组件，而时钟属于 accepted inputs。
- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/03_native_extension.tex:21–25`
  - 原：When the parent installs, the Owner compares the call's complete frozen start state, actual frontier, contract, and session epoch with it.
  - 建议：When the parent installs, the Owner checks the call's complete frozen start state, actual frontier, contract, and session epoch against that installed parent.
  - 理由：明确 with it 的对象；这是比较 tuple 的简写，不改变 full-input witness。
- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/04_native_resilience_working.tex:29–30`
  - 原：Both policies share this coordinator, durability, recovery, and actual Consumer.
  - 建议：Conservative execution and RevTrace share this coordinator, durability, recovery, and actual Consumer.
  - 理由：此处尚未到两政策的 Evaluation 定义，读者无法从近邻找到 Both policies。
- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_operating_boundaries.tex:3–4`
  - 原：In the headline RevTrace arm, 18 of 368 updates encounter and retain one;
  - 建议：In the headline RevTrace arm, 18 of 368 updates encounter and retain a supported ahead view;
  - 理由：one 跨句指向 whole view，直接重复核心对象比代词更省认知。
- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_operating_boundaries.tex:40–42`
  - 原：Its continuity distinction is stable: compatible withdrawals are zero versus 16/17/12.
  - 建议：RevTrace's continuity benefit is stable across these repeats: compatible withdrawals are zero versus 16/17/12 for computation-only.
  - 理由：明确 Its 和对照计数归属；稳定性仅指这三次重复。
- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_native_retention.tex:100–102`
  - 原：The second S0908 repeat has D99 2.229~s.
  - 建议：The second S0908 repeat is the sole failed request, with D99 2.229~s.
  - 理由：与本段 7/8 对应；可选小修，非新结果。
- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_native_retention.tex:123–125`
  - 原：Its 0.817-s Consumer event-state holding interval spans that update and ends at legitimate supersession.
  - 建议：The Consumer retains that same whole view for a 0.817-s event-state interval spanning the update, until legitimate supersession.
  - 理由：简化 event-state holding interval 名词链；保留 event-state 以免误写成高频采样证明的连续物理时长。
- `Paper_DSN/revisions/20261104_dsn2027_release_v14/sections/05_same_source_validation.tex:67–69`
  - 原：Unpinned terminal and audit windows stay at most 64 entries; live dependencies, state/output bytes, RSS and cumulative logs are separate.
  - 建议：Unpinned terminal and audit windows stay at most 64 entries. Live dependencies, state/output bytes, RSS and cumulative logs are accounted for separately.
  - 理由：are separate 未说明计数与内存的关系；64-entry 只作用于 unpinned windows，不能读成全内存有界。

## 不可越过的语义边界

- 完整原始调用包括原始选择/更新或其声明的 buffer-only path；typed first-beam identity projection 不是完整选中结果。
- unknown 只表示无确认/否定见证；早期祖先不匹配可撤回当前视图，却不能否定未来 frontier 的完整输入。
- 已接受完整结果的原身份可跨 producer exit 保留，但 producer exit 不确认输入；新消息权限在 fencing 后结束。
- R/S 是保留动作开关，所有四臂仍共享安全检查；不能将动作关闭写成安全验证关闭。
- 连续性命题是兼容应用的局部性质；不是全局单调性、任意负载进展或期限保证。
- 6,231 normal states 与 14,074 failure states 分属两个有界模型；12-event depth 和 hand-written specification 保留，不转写为机械提取整程序证明。
- 36 trials、3,976 durable transitions、故障次数与声学来源数具有不同分母，不合并。
- 自然轨迹、受控交错/压力测试和条件性命题为不同证据层级；旧 native budget scan 不并入 core factorial 以制造视觉密度。
- 第一送达与当前持续覆盖分别评价；Figure 1 不是事件匹配反事实，joint 首显晚 27.4 ms；所有 primary core arms 仍 fail whole-run D2。
- 共享底座 comparator、adapter 完整状态义务、失败恢复时钟、排除故障范围及真实 AI 披露均不得因语言润色缩小或夸大。

## 对附件意见的取舍

采纳因果段落、术语解释、局部视觉自解释的方向；不采纳“Strong Accept 风格密码”、状态数相加、共享底座改独立实现、将未知输入写成永久失效、将局部兼容保留写成一般存活性、为异步图加虚假时间顺序等建议。摘要已有主效应及区间，不建议为填入验证数字牺牲方法和服务对象的可理解性。

全篇未见需要为了语言修订新增实验的阻断项。方法小节中的 confirmed/refuted/unknown、完整原始调用定义、命题及 proof 已有必要精度；不应仅为减少术语而改写这些核心定义。Related Work 的技术对象区分也已明确，不建议做无必要同义改写。

审查决定：`PASS_FOR_TARGETED_EDITORIAL_REVISION`。由主任务选择替换、核对语义并实际编译；本报告不是实验结果或发布验收。

## 输入身份

| 输入 | SHA-256 |
|---|---|
| main.pdf | `5462d73d98a711d94f04e852a1bfd028ed34cce1cf0aefd86a56418bec37d581` |
| main.tex | `dab62b9dcc62ef62be7913925932d0f9317ae4a89eac9aa9500d4aebffa682ed` |
| 附件 c702ca7d…（266 行） | `142339fa3b2a263e5f00c4d7c07109760f725a9b5d56c52c855bb808e85af55a` |
| 附件 6fe9e5ce…（202 行） | `358f5c242c9db1025906bc6932d82860154d912c5a0b1c1eb80954e7bc4eb915` |

既有 memory 仅用于提醒证据边界，相关限制均已在本次 v14 正文重新核对。

<oai-mem-citation>
<citation_entries>
MEMORY.md:43-48|note=[review boundary reminder checked against current v14]
</citation_entries>
<rollout_ids>
019fa2a6-578b-7772-9223-f74b0c3992ce
</rollout_ids>
</oai-mem-citation>


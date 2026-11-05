# v15 实际语义差异审查

审查 ID：DSN-READABILITY-V15-SEMANTIC-DIFF-20261105。

**结论：修复一处范围/主体歧义后通过；当前未留开放的实质语义问题。** 本轮核对实际改动，不追加润色提案。

## 身份与范围

- 冻结基线：`Paper_DSN/revisions/20261104_dsn2027_release_v14`。
- 最终候选：`Paper_DSN/revisions/20261105_dsn2027_release_v15`。
- 初审 PDF：`096ac710a07e1bb13e05fb7f0f671a3259d80d17d9ac04f589185039e3a6cda2`。
- 修复后最终 PDF：`b5c410b6c6fd08cec08535398910b49398dc0dc78cde497638eb537b661db750`，实际文本分页为 12 页。
- 两次 main.tex 均为 `bf8b49d0baa44d82bcbdca8f28b22450a573be745522d1d2cb1a484c17862754`；差异修复在被 input 的 operating-boundaries 节，不应以 main.tex 单文件哈希代替整份源身份。
- 每侧递归可达 TeX 共 20 文件（main +18 sections +1 included table）；11 文件存在改动。

## 发现并关闭的问题

### M01 — 已修复：质量/成本的设置范围与主体

位置：`Paper_DSN/revisions/20261105_dsn2027_release_v15/sections/05_operating_boundaries.tex:61–65`。

初审稿删除了 v14 的 RevTrace 主体与 Headline 限定，形成 “Outside the primary setting ... Board energy spans ...” 的相邻句，可能将主设置的 59.16–59.73 J/audio-s 误读为更广泛配置的范围。

父任务已经改为：

> For RevTrace outside the primary setting, requiring retrospective raw-text agreement excludes 2~s ...
>
> In the primary setting, board energy spans 59.16--59.73~J/audio-s across five arm medians.

已在最终 TeX 与最终 PDF 提取文本中复核两处限定；本子任务未改论文。最终该节源 SHA-256：`6199ccdfd31a5e600e92ccb10bd195e169296be6f6879fa7b8e8b9bc52e344af`。

## 逐项语义核对

| 项 | 状态 | 实际核对 |
|---|---|---|
| 具体评价设置 | PASS | 12→17→0 明确限定为预选 24-speaker Qwen、2-s feedback、staggered setting；rho=1 与 2-s 对应在评价设计中仍保留。未推广为全部负载或全 24-speaker 配置的零撤回。 锚点：`sections/01_progress_introduction.tex:30-40; sections/05_evaluation_core.tex:78-84` |
| 首次送达与持续可用 | PASS | Figure 1 图注缩短后仍写 computation-only 先在 D2 内送达但丢失 2.176 s；RevTrace 首显晚 27.4 ms、兼容安装保持覆盖；两者非 event-matched counterfactual 和双方 C8 保留。删去精确事件时间属于图注去重，非改变结果。 锚点：`sections/01_progress_introduction.tex:13-28` |
| 忠实执行的 use 前提 | PASS | Calls admitted for use must execute... 将前提限定在允许使用的调用；并未改为每个注入故障调用都忠实。紧邻 wrong-input injection 的故意违例、containment/release 用途与命题排除仍在。 锚点：`sections/02_contract.tex:8-24` |
| 两个执行实例 | PASS | 先共同逻辑路径后两种 execution settings；core 的 Private/Authority 与 native 两个完整 recognizer–corrector 角色保持。没有 unified code kernel、完整程序证明或普遍迁移保证。 锚点：`sections/02_contract.tex:26-35` |
| 状态捕获与资源核算 | PASS | 所有影响后续输入、选择、反馈的 mutable cross-call state 仍要求捕获；新增 any configuration affecting inference remains bound by the contract，防止 separately 将配置错误排除。 锚点：`sections/02_contract.tex:50-59` |
| 对象/生命周期与物理释放 | PASS | 新段用支持丢失、producer running、已接受结果跨 producer exit 的不同对象说明分别判断；没有永久 refute 未知输入。虽然不再逐项命名 lifetime，核心协议仍要求 all terminal rows + device synchronization 才 BatchDrained/复用，取消确认不等于物理 drain。 锚点：`sections/02_contract.tex:91-95; unchanged sections/04_protocol.tex:1-16` |
| 条件进展及恢复计时 | PASS | Conservative execution 与 RevTrace 明确共享 coordinator/durability/recovery/actual Consumer；有限工作与有限支持故障、公平性、可读存储、最终释放/加载等条件未删。原始输入时钟、loading/replay/recomputation 计入 deadlines、无 fixed recovery-time/D2/C8 bound 均保留。 锚点：`sections/04_native_resilience_working.tex:26-39` |
| 共享正控身份与动作开关 | PASS | alternative joint policy 仍为相同 retention/Consumer 条件在 shared execution/commit substrate 的正控，且与 external prior work 分开；R/S 仍只切换保留动作，四臂共享安全检查。无独立 reference implementation 声称。 锚点：`sections/05_evaluation_core.tex:32-45` |
| 右删失 | PASS | 真实 loss ends when coverage returns 与下一 selected root 停止 observation 明确分开；特别说明该边界不算 recovery。未将删失改成完整缺失时长上界；10/12/9、缺口积分与 D2 read point 数值未变。 锚点：`sections/05_operating_boundaries.tex:45-53` |
| 20/92 自身预测 | PASS | 92 promoted calls 的 recognition 早于 parent completion；20 指它们自身 successor prediction 与原始 selected result 不同。没有将 20 写成输入 eligibility 失败或取消 92 的已确认身份。 锚点：`sections/05_native_retention.tex:116-121` |
| 回顾文本 unknown 与输入 unknown | PASS | No timely coverage has unknown agreement 明确限定为 retrospective content agreement；confirmed/refuted/unknown 的输入定义未变。回顾内容匹配仍与在线 SUP、人工准确率分开。 锚点：`sections/05_native_retention.tex:70-76; unchanged sections/03_coordination_algorithm.tex:1-6` |
| R/K 描述 | PASS | R1 改写为 computation retention、K 为 covered exit，未变成安全认证或取消自身的能力。24-run 设计、675 paired controls、96 consumed rows、6/6/1、473–577 ms、双到达模式 credit 区间、无稳定正交互及物理 drain 区别保持。 锚点：`sections/05_execution_only.tex:5-16; unchanged sections/04_protocol.tex:10-16` |
| 结论条件与反例 | PASS | Discussion 加主题句而未删 evidence/comparison/adapter 义务；结论只将 unnecessary 改成已命名 avoidable，并保留 Under the declared contract / at compatible applications。全局非单调、过载 D2 失败、S0915 机会耗尽、长序列失败未被改写为胜利。 锚点：`sections/07_progress_discussion.tex:1-30; sections/08_progress_conclusion.tex:1-9` |
| 质量/成本范围与主体 | PASS_AFTER_FIX | 初审发现遗漏 primary energy 范围与 RevTrace raw-text 主体；父任务已修复，最终源和 PDF 均验证 explicit For RevTrace outside... 与 In the primary setting, board energy...。 锚点：`sections/05_operating_boundaries.tex:58-68` |

## 形式与书目不变量

- 3 个 proposition、3 个 proof、5 个 equation 环境，在统一换行后正文逐字一致。
- refs.bib、formal_refs.bib、coordination_refs.bib 和 main.bbl 均字节一致；31 个 bibliography items。
- 7 个 tabular 环境在只移除 textbf 呈现包装后完全一致。
- 三个命题的充分/条件范围、早期完成先缓冲再复核实际父输入、局部兼容连续性及 selected-trace projection 都未改动。

## 数值呈现与强调

- `64.118875` → `64.119`：three-decimal display rounding only。
- `66.33975` → `66.340`：three-decimal display rounding only。
- `228.51025` → `228.510`：three-decimal display rounding only。
- `208.1003125` → `208.100`：three-decimal display rounding only。
- `31.0` → `31.000`：trailing-zero formatting only。

正文未残留超过三位小数。Table III 只加粗 129.460、1.762、10/16；能耗 654.845 没有加粗。其他表格数值未变。

图注减少了图中已有的独立事件时刻，保留 2.176-s 缺口、RevTrace 首显晚 27.4 ms、双方 C8 与非事件匹配反事实限制；2-s feedback 是原 rho=1 设置的展开，不是新增结果。

## 方法与解释界限

- Recursive input traversal from main.tex; all 20 reachable TeX files on each side (main +18 sections +1 included table)
- Unified diff inspection of 11 changed TeX files
- Normalized-newline exact content comparison of proposition/proof/equation environments
- Byte comparison of all 3 .bib files and main.bbl
- Exact tabular comparison after stripping textbf presentation wrappers
- Targeted final-PDF phrase extraction and SHA-256 verification

- 本审查证明改写保持已有定义、条件和报告内容；不重新建立运行时正确性、性能效果或真实端点计时证据。
- 公式 A2,8 保持不变只验证测量定义未改；normal metric availability 的代数关系不能验证所有真实 endpoint events。
- 没有重新运行模型、实验、故障注入或全量日志审计；也没有以语言审查替代整包发布验收。
- 本子任务仅创建本 SEMANTIC_DIFF_REVIEW.zh.md/.json，未修改论文或运行时。

当前决定：`PASS_AFTER_ONE_SCOPE_FIX`。不建议因本审查继续改写；主任务可继续既定编译、视觉与发布验收。


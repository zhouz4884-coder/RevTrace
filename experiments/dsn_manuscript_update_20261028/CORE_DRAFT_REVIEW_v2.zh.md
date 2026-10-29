# 新核心稿第二次独立评阅：贡献单位、近邻区分与证据取舍

日期：2026-10-29。对象为 `Paper_DSN/revisions/20261028_dsn2027_progress/core_draft.tex` 及其实际可达的九个章节文件（八个逻辑章节，评价拆为两个文件）。本轮是全文论证评阅，没有改正文、检索新文献、运行模型或访问远端。近邻机制依据本目录已完成原文阅读的 [ROUND3 记录](NOVELTY_NEIGHBORS_ROUND3.zh.md)，不是从论文名字推断。

**总体判断：可以形成有竞争力的应用与组合论文；目前最需要改善的是把科学增量连成一个贡献单位，而不是再开实验矩阵。** 新稿已经有明确的问题、完整两秒真实内容病例、同可信任务的五臂确认及保留阴性的48格边界。它没有依赖“每个方法都从零发明”，也没有把完整 Standard 同效当成反证。这些取舍正确。仍有一个主要写作风险：C1 被单独列作“充分关系”，随后是很短的定义式归纳；审稿人可能只记住“相同输入可以复用”，还没有充分看见这个关系在受保护反馈服务中同时约束哪几次不同的转换，以及实际增加了什么能力。

## 1．优先改：新颖性应落到完整应用组合，而非单独一条归纳

`01_progress_introduction.tex:65–78`、`03_continuation.tex:21–43`。

不建议删除充分条件，也不建议为了显得复杂而制造新算法。它的作用是把接口前提、可继承的真实执行、在途输入和权限边界说清楚。建议将 C1 的题眼从“一个可执行充分关系”改为**受保护神经反馈接口及其执行资格关系**，把同 F、完整跨调用状态、实际执行路径和冻结在途输入作为具体内容；命题作为该接口的论证，而非独立的通用增量计算新定理。

随后用一段连接 C1 与 C2：可信选择继续推进，执行端必须判断旧工作是否仍能使用；Consumer 在安装短的新可信快照时，又必须独立判断当前完整假设是否仍能保留。只保留前者不能保证已经交付的进展继续可用；只保留后者不能补回已经被执行端废弃的后继。这不是声称两者对安全普遍必要，而是在保持原选择权的条件下提供额外服务能力。当前 `03:80–86` 已准确说明 R/S 是同一关系的**不同充分见证**，应保留，不能改成“两个相同 guard”。

**我会采用的贡献单位：完整反馈合同 → 旧执行资格 → 实际完整视图转换 → 同任务下已交付进展的持续可用性。** 取消和恢复是让这一能力可以落到执行协议上的支撑，不另行包装为第三个全新通用算法。这样既承认组合创新，也回答“为什么不是给已有缓存加一个名字”。

## 2．优先改：近邻承认已经到位，具体差别还需多走一步

`01_progress_introduction.tex:43–54`、`06_progress_related.tex:1–33`。

目前没有明显贬低 IU/Adapton/SSBD，方向正确；但反复说“我们的对象是完整反馈状态/完整假设”仍偏概括。建议用下面三个具体比较替换一部分泛化说明，增加约一个短段落即可，不需要新增跨论文速度表。

| 近邻 | 必须正面承认的已有内容 | 建议明确的本文增量，及不该作的推断 |
|---|---|---|
| IU | 独立的 newest committed NC / active RE、模块依赖和撤销闭包、异步处理已经存在。 | IU 的 commit 是不再撤销该 unit 的承诺；本稿“认证”表示受保护选择/安装接受，不保证其文本未来不修订。本文需给出的是完整神经跨调用状态下、独立新根到来时对旧执行及实际完整假设的资格判断。不能仅把 NC/RE 换名为 Canonical/Private。此区别是所用合同和证明对象的区别，不应写成 IU 无法表达我们的系统。 |
| Adapton / Nominal Adapton | recorded-read 检查、依赖图、按需修复和 names + arguments 已经使“版本变化不必丢弃全部旧工作”成立。 | 本文的新应用义务是：复用完整真实调用不能改写原受保护选择，且计算合法、实际视图仍可用、物理执行已释放是不同事件。依赖思想可以表达这些对象；我们增加的是这个接口、动作约束及其服务证据，不是证明它无法扩展到神经服务。 |
| SSBD | 不仅是普通固定输入推测解码；它已协调旧 draft 复用与 display-only mask-k，而且存在 β=0 的无偏版本。 | 它在更新输入上重新验证旧 draft；本文沿实际完整调用路径证明相同反馈边界下的依赖资格，保留整个当前兼容假设，同时保持独立选择权。区别不能写成“SSBD 有偏所以不精确”，也不能把计算/显示联合本身称为首次。 |

这一具体比较比多次强调“不是从头浮点重放定理”更能使应用创新被识别。也不要求重造 IU/Adapton/翻译系统来充当性能基线：当前四臂与作者自建完整 Standard 回答的是同一合同内的设计问题；它们不能支持“击败所有既有系统”的标题，但完全可以支持此组合的实证贡献。

## 3．优先改：把 DSN 价值写成可检验的服务属性

`01_progress_introduction.tex:9–41`、`05_evaluation_core.tex:186–208`、`08_progress_conclusion.tex:1–9`。

开篇病例现在足够有力量：完整2s非 EOS 音频、真实新增37字符、D1.444 → 兼容撤回1.544 → 原 D2 读点缺失 → C3.720 恢复相同文本。它比总回撤次数或旧 EOS 尾部更直接；**应保留为问题动机，不能升级为全工作负载通过或成对反事实**。

建议在病例之后或贡献前增加一句明确的服务需求：当下游实际依赖当前临时完整假设时，安装新可信结果本身不应丢掉仍有合法依赖的已交付进展。该需求允许后续有效修订和必要的不兼容撤回，不等同于内容正确、全会话单调或人类用户偏好。这样 DSN 对象是受保护修订下的服务可用性，而非“让字幕看起来更稳定”。无需虚构用户研究、故障发生率或安全关键应用来抬高意义。

必须同时保留：headline 的全部15格 D2 未通过；c16 连续性稳定而信用/时序交互混合；c12 强见证阴性；native 同资源双副本占优。这些数据意味着本文目前没有证明“只有联合能在某个显著机会区间兑现整轮 SLO”，但不推翻已经实际发生的交付后可用性损失及其条件性消除。**结论应卖这个已成立的能力，不再暗示总体容量或普遍端到端加速。** 当前结论基本做到了，可再用“compatible root application”替代宽泛的“addresses this loss”，使其闭合到命题的范围。

## 4．证据选择与篇幅：保留什么，压缩什么

1. **正文主脊柱保留**：真实完整区间病例；五臂 headline 表及作者自建 Standard 的身份；48格图及原始 first-credit/secondary continuity 分离；完整 Canonical 历史不变和同 F raw 支持差异。不要把零音频回撤换写成零文本修订，也不要用新连续性指标冲销负信用交互。
2. **110格的角色再说清一处**：`05_evaluation_core:20–30` 交代了构成，但主表只回答预定 Qwen/ρ1/错峰层。同步、Whisper、粗反馈和重复分别承担边界/敏感性角色，不是110个独立正例。可以把目前散落的几个控制结果并成很小的“主层—时序—后端/粒度”证据索引；不必再加大表。
3. **K 保留一条完整因果链即可**：实际请求→ACK→drain→同输入/同输出下一批→其中真正新增及时行，随后一句混合整轮结果。当前 `05_execution_application:13–48` 的内容正确，但细到多组逐行计数会与核心连续性争篇幅。完整96行/675对和 raw 支持细节可放补充材料，正文保留强链条和未普遍获益的结论。
4. **恢复机制压成支撑**：`04_protocol:48–81` 的 WAL、幂等和旧1154状态模型不应与 R/S 争“新协议”主位。保留故障边界和一小段必要实现；完整旧模型/恢复来源放 artifact 或补充。不能借旧模型替后来完整接口背书。相反，C1 的已有正反见证可用一张小接口/拒绝条件表替代部分重复边界说明，让“完整状态”可理解。
5. **native 定位迁移和成本测试**：`05_execution_application:50–118` 的完整原选择与同资源双副本是强点。17s 是处理前沿的 deadline credit，不是17s新增文字；已完成内容分析发现该臂原17s首次覆盖均伴随追加，可在正文补一句消除空文本触发疑虑，但保留两副本中1.5s无新文字触发的原信用，不重定义主端点。也不要把241引入/57撤除字符当作57个识别错误。
6. **neural69PASS 仍是 component**：当前可达正文尚未使用这项结果，正确。即便加入，也只能证明完整候选 packet 切面/保真资格或构件行为；不能据此说已经在在线纠错关键路径复用、解决 Authority 瓶颈或超过双副本。在线服务结果到来以前，最多在应用扩展一段标注，不能进入摘要收益。

## 最小协调修改顺序

先改 Intro 的贡献单位及邻近工作的具体连接，再改 Related 的三个机制对照；之后压缩 K/WAL 的叙述，给正文核心接口和服务属性留空间；最后核对摘要、结论是否仍只承诺已测能力。无需因本轮意见再发起新模型、更多 session 点或泛近邻复现。

## 可协调采用的三段英文建议

以下仅为替换建议，未写入 `.tex`；现有引用键、主指标和结果均不改。第1段可替换 Intro 的泛化连接句，第2–3段分别替换 Related 的两个近邻段落，不必三个位置重复完整说明。

```latex
% LOGIC (01_progress_introduction, Lines 50--63) [Priority: P1]
These foundations supply dependency reuse and revocation mechanisms.
RevTrace realizes them under a protected feedback contract in which the
selected correction becomes input to later inference. This contract governs
two distinct decisions: whether an executed continuation remains eligible
under the new root, and whether installing that root preserves the
Consumer's current whole hypothesis. Separate sufficient guards enforce
the same dependency relation at these two boundaries. The resulting
composition provides conditional continuity of already delivered progress
while leaving selection authority and necessary revisions intact.
% Changed: proposed replacement of the contribution bridge; no source edited.
% Protected: existing citations, labels, math, and numerical results remain unchanged.
% Meaning-Check: PRESERVED
% Risk-Flags: none
```

```latex
% LITERATURE (06_progress_related, Lines 1--13) [Priority: P1]
The incremental-unit model already separates newest committed information
from the active right edge and propagates dependency revocation
\cite{schlangen2011incremental}. Its commit promises that a unit will not
be revoked. Here, certification records acceptance by the protected
selection protocol; later selected facts may still revise the transcript.
Adapton checks recorded dependencies, and Nominal Adapton combines names
with arguments and dependency checks to recover reusable computation
\cite{hammer2014adapton,hammer2015names}. RevTrace instantiates these
principles for complete neural feedback state and frozen executed calls.
Its additional service obligation connects execution eligibility to the
actual whole view retained when an independently selected root is applied.
The witness establishes dependency validity along recorded calls; it does
not assume identical results from a new floating-point execution.
% Changed: proposed explicit mechanism comparison in place of generic positioning.
% Protected: schlangen2011incremental, hammer2014adapton, hammer2015names.
% Meaning-Check: PRESERVED
% Risk-Flags: none
```

```latex
% LITERATURE (06_progress_related, Lines 25--33) [Priority: P1]
SSBD already coordinates old-output reuse with display-only suffix masking
\cite{zeng2026ssbd}. It revalidates a draft under the updated input and
includes an unbiased configuration. RevTrace instead asks whether complete
calls that actually executed remain a lawful continuation of newly selected
feedback state, then checks whether the Consumer's whole current hypothesis
has that dependency witness. The distinction is the reuse object and its
protected feedback contract, rather than computational reuse plus display
coordination by itself. PredGen likewise provides a close precedent for
speculation while speech input evolves \cite{li2025predgen}; our measurements
keep the selected feedback task fixed across the compared policies.
% Changed: proposed concrete SSBD comparison, acknowledging its unbiased variant.
% Protected: zeng2026ssbd, li2025predgen.
% Meaning-Check: PRESERVED
% Risk-Flags: none
```

**最终判断：这不是“充分条件新定理 + 取消 + WAL + 一个应用”的四块拼盘；应写成既有增量思想在受保护反馈服务中的一个完整设计，揭示并修复“合法计算不等于持续可用的交付”这一可实测冲突。** 当前证据足够支撑这个有限但清楚的主张。投稿竞争力的下一步首先来自解释清楚这一应用增量及其必要取舍，而不是追逐全点支配或把已经阴性的容量试验再调成正数。

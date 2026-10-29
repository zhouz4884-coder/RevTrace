# C1 正文定义与条件性命题：保留仍合法的完整进展

状态：供 DSN 正文选择使用的技术表达准备；只整理已冻结实现和已有见证，不修改运行源、不新增实验。源码基准为 `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`，不是 legacy checkout 的 HEAD。

**建议正文主张。** 在声明的反馈状态合同下，RevTrace 给出跨认证根保留临时计算的可执行充分见证，并在应用新认证根时保留仍兼容的完整临时视图。计算端与 Consumer 共享“完整反馈状态与真实冻结依赖”的含义，采用不同的充分检查。这里的创新是具体反馈服务中的组合与应用，不是新的通用 memoization 定理、最小状态等价算法，或所有系统都必须采用的判定器。

## 1. 本节目的与段落安排

本节要让读者能检查：一次认证推进为什么既不能一概丢弃旧工作，也不能一概继承旧工作；保留哪一类对象，凭什么保留，以及保留不会赋予什么权限。

| 段落角色 | 应回答的问题 | 后续证据 |
|---|---|---|
| 对象与假设 | F、P、完整结果和一次实际调用分别指什么？ | 冻结 job、trusted render、row 身份、声明 adapter |
| 共同关系 | 什么叫新 Canonical 根下的合法临时 continuation？ | 记录的完整输入—输出依赖链 |
| 计算端 R | 哪些已完成节点与冻结在途输入可以继续？ | `eligible_chain`；针对性 CPU 见证 |
| 消费端 S | 哪个完整已见视图不会仅因兼容 Canonical 到达而退回？ | `_compatible`、kernel 实际申请/应用；CPU 与真实时序 |
| 范围与意义 | 与识别正确性、认证、机器检查和性能收益是什么关系？ | 独立选择边界；机器范围说明；四臂服务实验 |

## 2. 对象、完整状态和外层前提

固定同一 session、合同/epoch，以及该合同允许的 adapter 和运行配置。用

\[
C=(v,F,Z_C,P_C,T_C)
\]

表示已经真实安装的 Canonical 事实：版本 v、认证音频前沿 F、受保护选择的完整输出 Z_C、下一次调用的反馈状态 P_C、绑定的显示文本 T_C。事务身份、合同/epoch 与输入源身份在下文省略，实际检查不能省略。**认证**指遵守受保护选择和安装协议，不等于转写与人工真值一致。

**声明反馈状态。** P 是 adapter 声明、后续调用实际读取的跨调用可变状态的保守表示。P 可以包含比后续某次调用实际使用更多的字段，因此逐字段相等是充分检查，而不声称状态表示最小。音频内容、模型/分词器/adapter 版本、语言与解码配置等其余输入必须固定或逐调用绑定；不能把一个未记录、以后仍被读取的 KV、音频缓存、对齐游标或工具状态藏在 P 之外。f0 的跨调用反馈是 `prompt_tokens`；它不跨调用继承 KV。后续调用会从这些 token 构造实际条件前缀，所以完整 token 相等可以比“实际条件前缀相等”更保守。其他 adapter 的 P 必须重新声明，不能直接借用 token-only 结论。

一个完整临时节点 n 记录：实际冻结调用 q_n，输入状态边界 a_n、输入 P_n^-、目标前沿 b_n，以及完整结果 (Z_n,P_n^+,T_n)。a_n 表示该调用消费的反馈状态所在的音频边界，**不推断 token/audio 对齐**；模型实际读取的音频可以是截至 b_n 的完整前缀。P_n^+、T_n 由合同指定的 renderer/投影从 q_n 与完整 Z_n 导出。完成节点不包括取消的部分 token；在途 q 只有冻结输入，尚无可使用的完整结果。

命题依赖以下外层前提，而不是把它们藏在一个哈希或 `True` 中：

1. **输入与调用合同。** 已接受的音频不可变；session/合同/epoch 和逐调用音频、语言、运行配置正确绑定；P 包含后续实际读取的跨调用状态。
2. **实际输入忠实性。** 所讨论的正常调用实际读取其冻结描述中的状态和音频，结果确实来自该次调用。调用一旦开始，不因重根而改写其输入。此处不要求两次独立浮点执行产生逐位相同的输出。
3. **完整结果与身份。** 节点是可信 wrapper 接受的完整 row；job、worker/incarnation、结果和实际发布身份不被混换；trusted render 绑定完整 Z 到 P/T。Consumer 使用单 Owner 的声明 FIFO 流，并通过实际应用边界检查。
4. **独立的 Canonical 权限。** C 已通过受保护的选择、匹配 WAL 同步和安装；依赖兼容检查本身没有 Canonical 写权限。

其中第 2 条是明确的执行完整性前提。现有系统的 host wrapper/receipt 是 API 身份与操作边界，并非面对恶意 host Python 或任意 GPU 内部错误的硬件 attestation。实际输入/tensor 记录用于本研究的可审计观察；不能将 observer 记录升级成不可伪造的执行证明。

## 3. 一个共同的 continuation 关系

令 x=(F,P_C)。若一个**实际完整节点** n 满足

\[
a_n=F,\qquad P_n^-=P_C,\qquad b_n>F,
\]

且满足上述调用和身份前提，则记 x \(\xrightarrow{n}\) (b_n,P_n^+)。这里比较完整状态；压缩表示为哈希时，还依赖约定的精确序列化和抗碰撞假设。

对有限节点序列 n_1,…,n_k，若第一条边从 (F,P_C) 出发，随后每条边恰好消费前一节点的实际完整输出状态及其边界，则称该序列是 C 下的**合法临时 continuation**，写作 C \(\leadsto\) n_k。一个在途调用 q 若冻结在最后的 (b_k,P_k^+) 上、目标位于 F 之后，则是该 continuation 的合法在途后继；完成前不把它当成一个结果。

该关系只表达依赖合法性：这些实际调用仍是合同允许的临时工作。它不声称 Z_n 等于将来的受保护选择，不保证文本正确，也不把 Private 输出提升为认证状态。它甚至不需要重新执行 n_i；重根没有改变已经发生的调用或其输出。

这个定义允许直接从新根出发，也允许用一个旧 Private 边界节点 b 作为见证：若 b 的完整输出恰位于 F 且 P_b^+=P_C，则 b 之后的完整依赖链可以从新根重新解释。后者是 R 选用的保守见证，**不是共同关系的唯一证法**。

### 命题 1：冻结依赖的重根充分性

在第 2 节前提下，若一条旧分支在 F 处具有完整输出状态 P_C，且 F 之后每个完成节点的实际冻结输入恰为真实前驱的完整输出、边界相接、末端可达，则该后继链属于 C 的合法临时 continuation。若其在途后继还使用该末端的冻结输入且目标超过 F，则该在途调用也可继续作为临时工作。

**短证明。** 以 (F,P_C) 为归纳基。重根时它与旧边界节点提供的完整跨调用状态相同，其他绑定输入不变。若第 i 个节点已由新根合法到达，第 i+1 个节点的实际冻结输入就是该节点完整输出所在的边界和状态，故它满足定义中的下一条边；重根不改变其实际音频、配置或输出。有限归纳到达真实末端。在途调用同样满足下一条输入边，但没有完成输出可供继承。证毕。

这是条件性输入/依赖论证，既不是任意神经内部状态的等价证明，也不是“同输入独立浮点重跑必然 bitwise 相同”的命题。Private 与 Authority 可以使用合同允许的不同运行模式；本命题没有把 Private 的数值结果等同于 Authority 的选择。

## 4. R 与 S 各自提供什么充分见证

### 4.1 计算保留 R：完整边界节点、实际链与在途输入

f0 `continuity_proof.py::eligible_chain` 在安装新 C 后检查：

1. 结果表中有当前 session 在同一认证边界 F 的完整 Private 节点；对应 job 的边界与 generation 匹配，其完整 `state_tokens` 逐 token 等于 P_C。
2. 从该边界按后继结果推进，每个 job 的 `chunk_id` 和实际冻结 `prompt_tokens` 与当前游标/状态相接，节点属于当前 generation。
3. 最终游标和状态恰好到达真正的 `branch_chunk`/`branch_tokens`，而不是在一个中间匹配节点处提前宣布成功。
4. 若分支有在途后继，则当前跟踪槽中恰有一个匹配任务；它的冻结输入来自已到达末端，且目标音频前沿大于新 F。

这些条件连同外层前提构成命题 1 的一种可执行充分见证。通过后更新分支的根元数据，不改写已发生调用的输入/输出。完整性、合同/epoch 和实际执行输入真实性不是该纯函数单独重新验证的。

唯一在途槽、当前 generation 和额外边界节点是此实现对可保留集合的约束。它们帮助拒绝歧义或未追踪对象，不证明所有实现必须拥有同样字段或同样 guard。特别地，没有额外边界节点时，本实现可以保守拒绝，而下一节的直接输入见证仍可能成立。

### 4.2 消费保留 S：为完整已发布视图证明一条实际路径

f0 `ContinuityView._compatible` 处理的是完整已发布节点 h，不负责保留未完成行。它可接受两种见证：

- **直接见证：** h 本身的输入状态边界就是 F，实际冻结输入状态等于 P_C；无需另有一个 Private 完成节点停在 F。
- **祖先见证：** 沿已发布节点的真实输入/输出投影反向追溯，同 session/generation、边界严格递增，直到直接见证，或到达 F 处完整输出等于 P_C 的节点。实现拒绝缺失、循环或不唯一的匹配祖先。

`KernelView.consume` 先在副本上预演完整视图，再调用 kernel 的 `apply-request`。kernel 独立检查 durable root、实际 Private result、绑定的全文/前沿与实际节点依赖；获准后才替换真实视图并记录 `view-applied`。因此一个调用方的兼容布尔值或文本哈希不能代替真实祖先记录。Consumer 与 R 使用相同状态合同，但**不是逐字相同的检查器**。

### 命题 2：兼容 Canonical 应用不会自行撤回已见完整进展

考虑一次已经获准并实际应用的 Canonical publication。应用前完整临时视图 h 已位于新 F 之后，并且 S 的实际依赖检查证明 C \(\leadsto\) h；同一事件不触发独立的撤回模式。在 `two_lane` 下，此次应用推进认证 lane 到 C，同时保留 h 的完整文本与临时前沿，故该次事件不会仅因新根到达而撤回 h 的音频进展或擦除 h 的字符。

**短证明。** canonical 分支先更新认证 lane 的版本、F、P 和绑定文本。由于 h 超前且兼容，`retained` 为真，临时 lane 直接使用原 h 的完整 `audio_end_sample`/`text`，不是新旧文本拼接。kernel 对预演状态的实际依赖与全文绑定检查成功后，才实际应用该状态。故认证前沿推进与原临时视图保留同时成立。证毕。

这是**单次兼容根应用的非退化性质**。今后新的合法临时结果、真正不兼容的 Canonical、其他撤回模式或恢复流程仍可改变视图；不承诺所有事件下的单调显示。S 关闭时，安全地退回认证快照仍然可能；R 关闭时，之后重算也可能发布较短的合法视图。因此 R/S 联合不是安全性普遍必要条件，而是有机会保住特定进展的协调设计，其实际价值由四臂服务实验测量。

## 5. 哈希绑定、实际执行与 F2 必须分开写

| 机制 | 实际能支撑什么 | 不能由它推出什么 |
|---|---|---|
| frozen job 与 `protocol_dispatch` 的 identity | 所跟踪 job 的输入描述、role、parent、合同/epoch 等未被换成另一个描述 | GPU 内核实际读取了描述中的每个输入 |
| `RowBinding` / inbox / 完整 row receipt | 同一 worker/incarnation、batch、job 与排他完整终态的身份；重放/混配防护 | 神经输出正确、硬件无错或 Byzantine GPU attestation |
| `validate_bound_text` / trusted render | 从绑定的 job 和完整 Z 重新导出 P/T；拒绝另造 state/text | Z 的输入依赖正确，或 Z 与正确转写一致 |
| kernel `apply-request` | 实际已登记节点、durable root 和完整可见文本/前沿具有被允许的结构依赖 | 任意未观测实际执行错误已被排除 |
| 独立受保护 Authority 选择与 WAL/安装 | Private 不能凭依赖兼容获得 Canonical 写权；认证事实来自受保护选择路径 | 所有合法 Private 都会被选中，或所有认证转写都零错误 |

源码 `tc_live_worker.py` 明示实际输入记录是 “Observer instrumentation; not a trusted execution attestation”。`composed_kernel.py` 同样说明它是 host API ownership boundary，不对恶意 host Python 提供隔离。

F2 特意令 `fault_actual_prompt_tokens` 替换真实模型输入；即使声明的 `prompt_tokens`、输出和 renderer 可以自洽，也已经破坏了正常 continuation 的实际输入忠实性前提。F2 不能被命题 1 宣布为正常合法计算，不能因为其 token/text 恰好匹配就宣称已经证明 GPU 按声明输入执行。受控 F2 可以用来检验物理退出、错误输入产生的长尾，以及独立 Canonical 选择边界，但不能混作“合法长计算”的自然证据。合法长计算应另由未启用替换、实际输入一致的调用见证支持。

这层限定无需削弱论文：保持受保护选择独立，正是允许临时端承载不可信、可能错误的工作而不将其写入未来认证反馈的前提。C1 提供条件性的保留规则，没有代替完整的故障检测或认证规则。

## 6. 两个粗观察不足以普遍判断的最短反例

以下是定义层面的反例，不是新实验，也不声称具有某个自然发生率。

**只看版本是否相同。** 旧分支生于 v=1；新 Canonical v=2 在 F 处得到 P_C=p。旧分支恰有完整边界输出 p，其后继也确实冻结消费 p，故版本虽不同，后继仍可由新根合法到达。反过来，一个带 v=2 标签的调用若实际冻结输入为 q≠p，且没有从 (F,p) 到该输入的实际链，版本相同也不能证明它合法。版本可用于身份/排序，但单独用来决定保留会分别造成不必要丢弃或错误继承。

**只看可见文本是否相同。** 在允许多个内部状态投影成相同显示文本的 adapter 中，两个状态都显示 “turn left”，但 P_a 与 P_b 的保留 token、控制信息或对齐状态不同。若下一次实际调用读取这些差异，消费 P_a 的旧任务就不能仅凭全文相同被当作消费 P_b 的任务。即便完整 P 相同，也还必须核对同一音频边界 F 和实际边；本轮 `sameP_wrongF` 与 `broken_frozen_edge` CPU 见证分别拒绝这两种缺口。这个反例支持“显示文本不是普遍充分证据”，不证明某个实现必须使用特定字段集。

## 7. 正文可直接选用的英文短段落

> We represent each feedback boundary by its audio frontier and the adapter's complete declared cross-call state. A provisional continuation is valid under a newly certified root when its recorded calls form a complete dependency path from that root: the first call consumes the same state at the same frontier, and every subsequent frozen input consumes the preceding complete output. The unchanged audio, adapter, and execution bindings are part of this contract. This is a sufficient condition for dependency validity; it neither certifies provisional content nor assumes bitwise reproducibility across independent floating-point executions.
>
> RevTrace uses two conservative witnesses for this relation. The computation side requires a complete private node at the new certified boundary, a reachable chain to the actual branch tip, and any in-flight successor's unchanged input. The consumer can instead prove a whole published view directly from its frozen input at the new root, or follow complete published ancestors to that root. When a compatible whole view is already ahead, applying the certified update advances the certified lane while retaining that view unchanged. The property concerns this compatible update only; later revisions may still replace or withdraw provisional content.

可紧接一个短命题，不必在主文重复全部清单：

```latex
\paragraph{Conditional continuity.}
Under the declared feedback-state and execution-integrity contract,
the complete dependency witnesses above permit an old provisional
continuation to be rebased without changing any recorded call.
If its whole visible view remains ahead and passes the consumer's
dependency check, applying the new certified root preserves that view.
The proof follows the frozen input--output edges by induction;
neither retention decision grants canonical write authority.
```

若篇幅只容纳一项命题，保留“共同关系 + 条件性重根/不撤回”即可。API 级绑定范围和 F2 限定放威胁模型/实现/评估相应位置，不能完全省略。

## 8. 逐项证据与自查

| Claim | Evidence | Status / limit |
|---|---|---|
| R 具有同 F/P、完整链、可达末端与冻结在途检查 | f0 `continuity_proof.py:2–24`；12 例中的前 9 例 | supported；纯函数依赖外层完整性前提 |
| S 可用直接冻结输入见证，不必要求额外边界节点 | f0 `certified_display.py:125–136`；`sufficient_is_not_universally_necessary` | supported；合成 CPU 条件，不是自然轨迹发生率 |
| 兼容 Canonical 应用保留完整临时视图 | f0 `certified_display.py:83–95`；`two_lane_retains_compatible_whole_hypothesis`；真实服务时序见证 | supported；单事件条件性性质，不是全程单调性 |
| 实际 Consumer 应用经过结构与全文检查 | f0 `kernel_runtime.py:19–55`；`composed_kernel.py::apply-request/view-applied` | supported；可信 host wrapper 作用域 |
| 选择、写入、显示与执行完整性是不同边界 | f0 renderer/row/kernel/Authority 路径；F2 实际输入替换 | supported；不宣称任意硬件错误已被检测 |
| 现有机器证据穷举整个 C1 | `C1_MACHINE_SCOPE.zh.md` | unsupported，正文不得这样写 |
| 现有检查是最小或普遍必要 | 两种实际 guard 的直接见证差别 | unsupported；只写充分性与具体服务互补 |

12 个针对性 CPU 例子的实际结果为 12/12 通过；源提交 `79f1f0997687450aca464356c59bc46d346f3be8`，逐例原始结果在 `C1_WITNESSES_v1/CASES.json`。它们使用逐字节复制的三个 f0 模块，不是整栈集成或模型正确性证明。1,154 状态有限产品检查 durable-root、实际应用与物理 lease 等接口交错，没有表示完整跨根多节点/在途保留；64 role 单元检验的是受保护选择边界，不能替代本节证明。本文命题依靠明确合同与依赖归纳，针对性源级见证及实际交错提供不同层次的验证。

自查：本文件未增加数字收益、普遍必要性、最小性、全栈穷举或浮点重放等价主张；未把合法依赖等同于正确识别；未把哈希绑定等同于实际执行证明；未借新 adapter 扩张 f0 合同；未修改正文、运行代码和冻结计划。

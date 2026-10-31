# RevTrace：中心论点、可实现算法与读者路线

2026-10-31；只读写作审查，无 NN 调用、无实验启动。已读 v2 的 `main.tex`、全部 14 个 section TeX 和 reliability 表；算法依据最终 NN4f 的实际调用、Owner、Consumer、storage、channel-close 路径及其针对性控制，不把旧 CK5 的物理批次规则移植为 native 规则。下述状态名是对现有代码的说明性归纳，不是新增策略。

## 1. 一句论点与第一页的四拍

> **RevTrace preserves valid service progress across trusted feedback revisions by independently validating complete call inputs, retaining original selection authority, and checking support for the Consumer's whole view.**

中文：可信反馈修订时，分别判断完整调用输入、原选择权威和完整消费视图的支持关系，才能把仍合法的计算保留为持续可用的服务进展。

第一页按四拍推进：

1. **具体损失。** 直接用同一个实际区间开场：完整假设在 1.444 s 到达实际 Consumer，1.544 s 被兼容根更新撤回，3.720 s 以同文返回；首次 D2 与最终 C8 均满足，仍留下 2.176 s 可用性空洞。随后一句交代其来自过载 c16，不能外推自然发生率或整体可行负载。先让读者看到问题，再给“feedback-driven inference”的抽象。
2. **缺口。** 原任务的可信纠错会递归改变后继调用输入。保住计算不自动保住已显示进展；出生版本、预测终点或 producer 生死，也不能独立决定一个完整调用的资格。三件事必须分别判断：完整输入现在是否被确认、原 C/U 是否提供完整结果、当前整视图是否仍有因果支持。
3. **方法。** 用一个协调器描述三种判断怎样共同驱动 retain / withdraw / install / recover。把短算法、8 行判定表、生命周期图放在同一概念模型下；WAL、RPC fencing、CAS 类检查作为支撑。原可信 C/U、完整输入、原 UID/birth/incarnation 均保留。
4. **证据与贡献。** 三贡献后只留一条结果预告：因子实验揭示组合的服务机会，最终 native 对照证明真实端到端机会，受控故障证明已接收成果与 producer 生命周期可分离。将密集数字留给 Evaluation。

| 三贡献 | 正文落点 | 直接证据与结论边界 |
|---|---|---|
| 服务正确性缺口：首次及时交付与持续保留是不同义务 | Introduction；Contract；Eval 1 | 实际区间；Qwen 因子组 computation-only 撤回 12→17，联合为 0；零前沿撤回不等于文字不变 |
| 原任务保持的组合机制：输入资格、选择权威、整视图支持分别判断 | Coordination；Conditional properties；Implementation | 下面算法；原 selected-prefix 条件论证；完整同前沿匹配与 UNKNOWN 控制；不是新的 WAL 理论 |
| 可测的实机能力及边界：提前执行、实际消费、失效后证据存续 | Eval 2–4；Lessons | 最终 4f：30→65.821625 / 66.33975 s，0/8→6/8；resident 0/8→7/8；buffer 2 匹配安装/消费、2 失配拒绝；保留 EOS、冷恢复、长流与容量负结果 |

## 2. 统一符号、权限与生命周期

| 符号 / 对象 | 唯一含义与权限 |
|---|---|
| `C_s=(F_s,P_s)` | Owner 当前已安装的 selected cut；`P` 是充分的完整跨调用状态，含绑定文本；`F` 是实际处理前沿，不是 token 对齐 |
| `q_j=(s,e,a_j,P_j^-,b_j,χ_j)` | 不可变完整调用输入；`χ` 绑定 source/audio、target/EOS、模型/解码/runtime。native 中完整 start 相等能确认输入，前提是其余已冻结输入不变 |
| `u_j=(owner epoch,serial)`；birth；`(slot,inc)` | 原调用、出生根和物理生产者身份；输入后来被确认不重命名、不重签、不改写历史 |
| `W_s[e,f]` | 本会话在同一实际前沿 `f` 的 selected cut 见证；只有相同 `f=a_j` 的完整失配才能反驳这个未来输入 |
| `J`；`B` | 在途 owned calls；已严格接收完整原 C/U 结果的 buffer。typed ASR identity projection 另有类型，不是完成的原 C/U |
| `D`；`C`；`V`；`L` | durable selected facts；Owner install；实际 Consumer 应用/整视图；物理占用。四者分别记时、分别授予权限 |

输入分类必须采用同一个优先次序：会话 epoch 已变为 **FENCED**；否则完整 start 等于当前 `C_s` 为 **CONFIRMED**；否则若 `W_s[e,a_j]` 存在且完整状态不同则为 **REFUTED**；否则若 `b_j≤F_s` 为 **COVERED**；其余为 **UNKNOWN**。UNKNOWN 是“尚无本调用输入前沿的决定性实际见证”，不是“输入正确”，也不是 REFUTED。更早祖先失配可以打断当前链，却不能排除未来完整输入重新收敛。

`S(C,h)` 检查已发布完整节点到当前根的连续完整状态/前沿路径。它独立于上述输入分类：可以撤回失去支持的 `h`，同时让未来输入 UNKNOWN 的 `j` 继续等待或执行。兼容且 ahead 的应用保留整视图；不拼接未经授权的后缀，不赋予其 certified 身份，也不承诺全会话文字单调。

core Qwen 的 `R` 还要求显式同前沿匹配边界节点和唯一 tracked successor；native Full-call 直接确认本调用完整输入。二者是同一依赖原则的不同充分实现，不能把 native 的 UNKNOWN 取消规则反写为所有旧 core 路径已经具备的行为。独立 TeX 算法明确描述 native Full-call。

| 情形 | 调用 / durable 权限 | 整视图与物理处理 |
|---|---|---|
| 同前沿完整输入匹配 | 在途继续；已完成可按实际父序进入选择；保原 UID/birth/inc | `S` 另判，不由输入匹配直接认证其预测终点 |
| 同前沿实际完整输入失配 | 不得 append/install；在途只凭已签发实际见证在安全点退出 | 撤回无支持整视图；未支持视图不是取消任意未来调用的证明 |
| 未来输入 UNKNOWN，包括更早祖先失配 | 不得 commit；也不得作为 REFUTED 发取消证明；完整结果先 buffer | `S=false` 时撤视图；调用输入仍可在以后同前沿收敛 |
| 目标 COVERED 或会话 FENCED | 不再选用；只退休严格匹配的旧调用 | 不清除别的 busy job；输入义务与原时钟不减少 |
| 完整原 C/U 且 CONFIRMED | sync 新事实 `D` → Owner install `C` → publish | Consumer 验事实顺序/父状态后实际应用 `V`；每个根携带自身 view snapshot |
| producer 确认退出 | 先封存并严格接收旧通道完整尾部，再 fence；保已接收 `B` 与原身份 | 退休未完成工作；exit/readers/CUDA release 才允许替换；支持视图可保留 |
| foreign/fenced/精确重复；当前 owned 内容矛盾 | 前者局部拒绝无授权；后者冻结写入并恢复 | 局部 drop 不释放当前/新 lease；合法旧 epoch terminal 仅退休其精确旧 lease |
| Owner 恢复 / 实际 Consumer ACK | 验证并重放既有 `D`，不再选择一次；新 Owner namespace | ACK 释放 outbox 引用，仍可见依赖继续 pin；旧事实重现不是新推理 |

**物理语义不得合并。** core 批次是全 terminal rows + device sync 才 `BatchDrained`；native4f 的普通 busy slot 在严格匹配 `completed/abandoned` 后释放，死亡替换另要求实际进程退出、readers joined、旧 CUDA 占用释放、sealed-channel 验证。逻辑撤回、取消请求、行完成、进程退出、CUDA 释放不是同一事件。

## 3. 条件性质怎样写才成立

**Selected-prefix 性质。** 假设：(i) adapter cut 覆盖所有会影响后继模型输入、原选择和反馈的可变状态；(ii) 可信原调用忠实执行冻结输入，原 C/U 与其完整结果绑定；(iii) 单 Owner 串行选用、当前会话/owned receipt 身份正确，完整输入和已选父状态完全相等；(iv) 输入、模型、解码合同不变，编码/摘要绑定可靠；(v) 存储兑现成功 sync，所有安装与 certified 应用以该事实为前提；(vi) 恢复只接受验证后的连续既有事实前缀。则从执行中只投影**不同身份的 durable selected facts**，所得状态序列是原程序允许的一条轨迹；原程序可以非确定。取消、等待、投影、局部拒绝、回收、重复递送和 replay 不增加 selected edge。Owner 在 sync 后、install 前崩溃的事实可在 replay 首次到达 Consumer，但只计一次。

这不证明任意 GPU 重跑逐位一致；实际 reference 配对是独立实验事实。也不覆盖 provisional UI，UI 用另一个充分性质：在一次 authorized Canonical application 前，若完整 ahead `h` 满足 `S(C,h)`，且没有另行触发的 withdrawal，则该次应用保留 `h` 的节点/全文/前沿。后续原纠错可合法撤回。两个性质都不蕴含人工转录正确、期限通过、无界 liveness 或整 Python/CUDA/OS refinement。

**来源和代码锚点。** 最终 NN source=`4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`（当前本地 HEAD，clean；59 files）；a13=`a13fa0a335529dc188f7e738877a3acd027ce4a7` 是 paired/resident 外层编排，依赖原 Owner，无新 C/U；buffer execution=`4eb03d6f4f9a918cce693c979e9cfa07e3d6bb28`；b867=`b8670073141a94a550abe5113222a508b63b5624` 仅新离线 reader。后者不能成为原 NN source 或撤销旧 CLI/compound FAIL。

- 输入 / UNKNOWN / ordered commit：`source_v2/fullspec_policy.py:29,48,139,151,166`；原输入 key：`stage_packet.py:55`；完整 state：`feedback_contract.py:15`、`native_bridge.py:37,47`。
- 原调用 / typed projection：`candidate_bridge.py:20`；durable-before-install：`resilience_policy.py:150`、`resilience_storage.py:97`；实际消费：`resilience_consumer.py:26,48`。
- 死亡/封存/权限：`resilience_owner.py:73`、`resilience_channel_close.py:58`、`resilience_policy.py:274`。resident 请求边界：`paired_resident_source_v2/resident_supervisor.py:57,62`。
- buffer reader 区分 registered job UID 与 physical READY：`buffer_fixture_source_v2/audit_buffer_witness.py:35`；机制与原失败分列于 `FINAL_R1_EXECUTION_RECORD_20261031.json`。

## 4. Evaluation 做推理，Lessons 解释边界

每节用“问题→公平比较→观察→可推出的结论→具体边界”，不要按实验日期或文件到达顺序组织。

1. **保住计算为何还会丢进展？** case + 四臂 factorial 同页承接；12/17/0 与 +26.645 s 支持组合服务作用，再用 negative repeat 和 ahead incidence 解释何时有价值。技术正文保留原信用定义及 subsequent continuity 的独立身份。
2. **这能保留原任务并改善最终服务吗？** 最终 4f 主行先于历史版本；544 selected transitions 核对、0/8→6/8、共同 drain 能耗 −6.52%。bdfa 独立确认与版本回归分开；resident 7/8 是单 outstanding、独立 EOS、closed-loop，不能替换无 reset 长流。
3. **结果资格是否依赖 producer 活着？** 2 match / 2 mismatch 完整 buffer 控制回答核心反事实；旧 36 格的 3,976 durable transitions、实际 consume、必要撤回和拒绝支撑组合路径；故障后的期限失败紧邻结果。原 reader 失败与新 zero-NN 重建一句披露，完整调试历史在 artifact。
4. **代价与适用边界是什么？** 长流状态压力证明 cut 在 buffer/context 变化下保持原任务，但质量与实时失败；协议条目相对 active dependencies 有界，不等于总内存常数。core K24 只留一段执行支持，不与 native producer death 混成新故障算法。

**Lessons 用三条可迁移认识收束。** (a) eligibility、selection 与 availability 是三项义务：input-confirmed call 可以有错误 predicted end，合法 UI 也不等于人类正确；(b) 保留依赖有效的旧成果与资源准入是不同问题：实际 ahead opportunity 决定收益，负 repeat/长流/双客户端未稳健损害限制性能外推；(c) 故障隔离的是新消息权威，已经接收与持久的证据分别延续，但恢复旧事实不会恢复原期限预算。不要把 Lessons 写成下一轮新算法计划。

**移入 artifact：** 完整 commit/SHA、source 激活和 CURRENT 流水、每次 CLI/CPU 失败、READY reader 具体调试、queue/cleanup PID 轨迹、逐格数字与样本清单、所有原能耗终点。**正文必须保留：** 最终 6/8、resident 7/8、原输入/EOS/期限合同、buffer 复审身份及旧失败一句披露、长流质量/时延失败、冷 Owner 新事实恢复慢、单链非饱和容量、formal/checker/runtime 三层覆盖区别。移走的是日志形态，不是关键反证。

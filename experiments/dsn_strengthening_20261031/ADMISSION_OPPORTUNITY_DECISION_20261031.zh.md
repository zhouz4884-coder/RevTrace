# Admission 是否值得进入当前论文：机会裁决与事前硬门

日期：2026-10-31。裁决 ID：`ADMISSION_OPPORTUNITY_DECISION_20261031`。

**裁决：值得保留一个最多 4 格的真实干扰机会门；现在不启动 16/20 格策略套件，也不预写一个新调度算法贡献。** 先完成正在执行的 paired32、resident4 与完整 buffer 跨 producer 死亡的两正两负控，并独立收束。若 resident 连续独立请求本身没有实质服务机会，或者原协议仍有未解决的语义/物理释放失败，本窗口不再增加 admission 实验。

本次仅做本地只读源码/计划/有界结果审阅，并写本文；没有远端访问、NN、代码修改、CURRENT 变更或队列操作。本文是未来实验的选择与停止规则，不是已冻结可发车的 config，也不是新 serving 结果。

## 1. 为什么这个问题有实际内容

`dsn_native_resilience_20261030/source_v2/resilience_owner.py:161–172` 先遍历空闲物理 slot，再按 `sidlist` 遍历会话；`fullspec_policy.py:95–103` 的 `next_full_start` 只在同一 sid 内先找缺失的 current-Canonical，再找条件 tail。因此可能在 A 的 Canonical 已有 live job 时，为 A 派发一个新的条件 tail，而 B 的下一 current-Canonical 输入已经 accepted、合法且缺少等价工作。资格检查不出错，资源优先级仍可倒置。源码说明这条交错可达；**尚未说明真实运行中它发生了多少次、造成多少延迟**。

这比笼统地说“应该自适应”更具体：原机制回答已执行工作何时仍有资格，Owner 还必须回答新的可选工作何时值得占用有限物理资源。拒绝新增可选派发，不要求撤销已有结果的资格，也不要求取消尚未被反证的工作。

当前可复查快照 `PAIRED_POLL_v2_1793434686191349800.json` 为 24/32：bdfa Full-call 6/6 原整场 gate 通过，final Full-call 4/6，两个失败是 S0908 的 EOS D2；四组各 6 格，共 408 个 selected state/C/ID 步均通过合法参考，C8 miss 均为 0。这是单 sid 配对的中途快照，不能变成最终 32 格或多会话可行性结论。它提示最终实现仍有真实短链服务机会，也提示 D2 边缘很紧，不能许诺两个 500 ms 流共享两 GPU 后 B 仍整场 D2。

既有 actual-dispatch 重配的正常短流 40/57、长流 96/924 与 166/830 也不能充当此处 admission 收益估计。旧无 reset 长流的内容/期限失败继续有效。

## 2. 能加强的科学命题，以及不能偷换的保证

建议只检验这个命题：

> 在固定的原始反馈转移、完整输入资格和物理生命周期下，保留已有合法工作与限制新增可选工作可以分别控制；在一个明确可行的共享资源合同上，前者的收益能否在减少跨会话必要工作干扰时保留？

最小候选机制是 **global current-Canonical-first Full-call**：每次物理 slot 真正可用后，先在全部已 admitted sid 中找缺失的 current-Canonical 调用；只有不存在这种候选时才考虑原有条件 tail。两层内部沿用原确定性 sid 顺序，不添加预测器、阈值学习、预算控制或新的取消规则。每次派发后重算候选，沿用原 `_has_work`、accepted、完整 cut、max-ahead、worker lease 和 authority 条件。

可验证的协议性质是：**在同一次 Owner 派发决策上，存在可派发的缺失 current-Canonical 时，不新派发条件 tail。** “可派发”包括输入已到、没有等价 live/completed 工作、物理 slot 已释放；已经在跑的 Canonical 不重复算 ready。这是一个明确的无倒置性质。它不要求抛弃 Owner 已接收的合法 buffer，也不赋予旧 producer 新消息写入权。

它不能给出下面更强的结论：

- **非抢占隔离。** B 到达前已开始的 A 条件调用仍可占住两块 GPU。Canon-first 不能把 ASR 提前输出当作 full 已物理结束，也不能为赶期限取消 unresolved 工作。必须按原实现确认的 physical terminal/lease release 继续等待。
- **D2/C8 无条件保证或开放到达容量。** 神经调用时长、输入到达和物理残余均无已证明上界；两条必要链本身也可能超过双 GPU 能力。
- **新调度理论。** 全局优先级本身过于简单；本地先例审阅只支撑当前组合主张，没有完成一个新 scheduler 的新颖性检索。若成功，论文贡献是该具体服务组合的实证与边界，不能改称通用自适应调度创新。

## 3. 固定一个确实可运行、也允许失败的合同

用两个 closed-loop 客户端，每个依次发两个不同原请求：A=`S0908/W0369 → S0913/W0313`，B=`S0905/W0246 → S0916/W0463`。四 source、音频 bytes、reference、500 ms/8000 samples、真实尾帧 EOS、D2/C8、FP32、原 C/U、guard、warmup、allocator 均沿用当前冻结条件。两个模型/worker 与 Owner 在一个 cell 内驻留。

- A 第一请求 origin 为服务开始；B 第一请求 origin 固定晚 250 ms。这个半 cadence 相位在任何并发 NN 结果前冻结，不搜索最佳 offset。
- 各客户端下一请求只在**自己的**前一请求真实 certified EOS 被 Consumer 消费后释放；其他客户端是否完成不影响它。所有未 admitted sid 的 accepted 保持 0。每个 sid 只用一次，不复制波形、不造 alias、不读识别文本决定 reset/端点。
- Owner 的 `settings.sources/sidlist` 保留现有 metadata 次序 `S0905,S0908,S0913,S0916`；A/B 是客户端名称，不能把它们当成 Owner 优先级，也不为制造受害者重排 sid。
- 每请求独立记录 origin、offer、ingress 接受、真实 Consumer、EOS 完成；原全部 offered 包括 EOS 都计分。第二请求 origin 随本策略的上一真实完成而变化，是这个 closed-loop 合同的真实后果，不能宣称各策略具有完全相同的外生到达轨迹。
- 预注册总共 4 个 sid、最多 2 个 outstanding；这是有限并发闭环，不证明动态 session 创建、无界 GC、自然到达率或自然干扰流行率。

发现阶段先用字节相同的 4f Owner/核心和新外层双客户端 ingress。若机会门通过，才另建只改变 Owner 候选次序的干净 fork。新 harness 与 Owner fork 分别绑定实际完整 commit/manifest；不能把 fork 的运行冒记为 `4f4c3c...`。模型、C/U、资格/失效证明、inbound、FactStore、Consumer、物理 lease 及 guard 必须保持原语义和 bytes；合法 source marker 映射必须明确绑定实际来源，不删除其它状态字段。

## 4. 最多 4 格的机会门：先证实问题，不先造控制器

所有 4 格和停止分支一起冻结；先执行前两格，满足继续门才执行后两格：

| 格 | 策略 | fresh 重复 | primary GPU |
| --- | --- | --- | --- |
| G1 | Conservative：只派 current-Canonical | r0 | 0 |
| G2 | AlwaysFull：当前原 Full-call admission | r0 | 0 |
| G3 | AlwaysFull | r1 | 1 |
| G4 | Conservative | r1 | 1 |

四格使用完全相同的请求分配、源顺序和 250 ms 首次相位；r1 只反转策略顺序并轮换 GPU assignment。每格 fresh-process、相同 preload/warmup、真实双板独占窗口；cell 内不重新加载模型。Conservative 不是预期 D2 成功基线，它用来测必要 Canonical 工作在此有限合同下是否有 C8 可行性。

记每格 `W_C=max(四个请求各自 all-offered C99)`，`Q=四请求 dual-deadline audio credit 总和`，`T=固定四源音频总秒数`。每请求原 D99/C99、EOS/non-EOS misses、全部 coverage、每客户端 Q、整个序列 wall/双板能量均完整报告；不只报告 W_C/Q。

**G1/G2 后继续、G3/G4 后 GO 必须同时满足的硬门：**

1. 全四请求完整 selected state/C/IDs 与原合法参考一致，全部原义务完成，clock/PID/model-load/source/physical gate 通过。任一语义/身份/时钟失败为 STOP；必要时做原同输入、重复、合法参考定位，不能先当调度慢。
2. Conservative 的四请求 C8 miss **为 0**、无缺失结果，且没有超时。这里比原 C99 gate 更严格地检验必要服务的有限可行性，不要求 Conservative D2 成功。若本身 C8 也不可行，记 `NO_GO_CONCURRENT_CONTRACT_NOT_FEASIBLE`，不调慢 cadence、不加人工请求间隔、不削期限继续找成功。
3. AlwaysFull 至少出现一个完整可追溯的实际派发倒置：新条件 job 开始时，另一 admitted sid 的缺失 current-Canonical 已 ready。记录两者完整 cut/UID、accepted 与 Canonical snapshot、worker lease，区分“决策时已 ready”和“之后才 ready 的非抢占残余”。只有后者不算这个门通过。
4. AlwaysFull 的 `W_C` 比配对 Conservative 至少增加 **20% 且 1.0 s**；同时 `Q_AlwaysFull−Q_Conservative ≥ max(1.0 s, 0.10 T)`。这组事前工程阈值要求真实的“早显示收益与必要服务干扰”两面同时存在，避免为一个无实际代价的倒置加机制，也避免仅证明关闭一切推测更好。它不是统计显著性阈值或性能定理。
5. r0、r1 各自满足上述条件；不能池化后互相掩盖。前两格未满足就可以在 2 格停止；若前两格通过但重复不通过，在 4 格停止并保留全部结果，不追加第三次、换来源或扫相位。

倒置事件和实际 endpoint 回归共同支持一个待检验的调度解释，仍不是证明所有延迟差由该事件造成。原 host `model_seconds` 可能含等待/重叠，不能除以音频秒数就宣布双 GPU 容量。若新增 CUDA event 测量，须所有策略同样配置并单列为设备区间；它不替代实际 Consumer C8/D2。现阶段不为得到一个 GPU utilization 数字修改神经路径。

## 5. GO 后只做一次局部因果检验，不自动扩成 16/20 格

只有机会门 GO，才冻结 global Canon-first Owner fork。建议再限定 **4 格**：AlwaysFull / Canon-first × 两 fresh，r0 正序、r1 反序及 GPU 轮换；仍使用同一双客户端合同。与旧 4 格完整身份分开。共最多 8 格并发实验已经能回答当前窄问题；本窗口不默认加入 quota、预算或第二相位。

这一轮成功必须在两次重复中均：

- 原完整语义/任务/clock/physical gates 全通过；候选派发倒置为 0；合法已有工作的保留/反证/安装规则未变。
- 相比当轮 AlwaysFull，`W_C` 至少减少 20% 且 1.0 s；每请求 C8 miss 为 0。若只是待 ready 后的非抢占残余决定尾延迟，priority 可以正确却性能无效，按实测 NO-GO。
- 相比发现阶段**对应重复**的 Conservative，保留 `Q` 增益至少 `max(1.0 s,0.10 T)`，且每个客户端 Q 均不低于该 Conservative。这个跨阶段筛选只证明有限机会；全部原始值必须展示，不能当同一随机 block 的正式显著性比较。

若要论文声称跨相位稳定性/一般公平性，必须另外预注册匹配的完整实验与必要原始文献核验；这不在本次机会门自动授权的范围。一个固定 1-worker/client quota 仅在论文实际声称优于资源隔离时才有必要；当前两客户端/两卡时它基本撤掉了会话内并行机会，还会在只有一客户端工作时空置另一卡，不能换名冒充一个同等资源使用的独立算法基线。预算控制目前没有必要：非抢占残余若压倒收益，应记录这次简单 admission 失败，而不是不断加阈值。

## 6. 对 11 页主线的实际价值与投入上限

**若全部成功：** 当前论文可增加一项窄但有内容的发现：完整结果的资格保留无需与贪婪新增派发绑定；一个直接的全局 Canonical 优先实现，在同一原始反馈任务/资源下保留早显示收益并降低必要服务干扰。正文用一张小表和一个实际派发交错，放在“保留资格与物理资源准入”同一节；不另立一套控制器理论，不挤掉 actual-pairing、whole-view 与跨 producer death 的主证据。预计控制在约半页正文，详细 ledger/失败放补充材料。

**若没有机会或候选无效：** 保留“资格不等于新增准入”作为限制，并报告这个固定合同下的容量/非抢占/收益失败。它补充主线边界，却不值得占一项新贡献。失败不抹掉已完成的单 sid、resident 或跨死亡证据，也不能把原失败长流覆盖为成功。

建议投入上限是事前资源预算，非完成时间承诺：双客户端 harness 开发/CPU 反例及独立审阅最多 1 个工作日；4 格发现运行沿用每格 720 s outer process cap（4 格进程上界合计 48 分钟，额外 preflight/cleanup 另外记录）；分析裁决最多半个工作日。只有 GO 再给 Owner fork/独审最多 1 个工作日及 4 格实机窗口。超过该界仍需改协议、模型状态或引入新控制变量，停止此扩展。不能以“还剩 25 天”替代科学机会判断，也不据此自动宣判应另写第二篇。

本文使用历史研究记录提醒“不把少算几次或旧事实可见变成服务赢”，但本轮具体缺口、代码身份、快照和实验合同均来自当前本地文件；没有把旧 scheduler 或恢复数字当成本次结果。真正发车前仍须 Rule 2：实验 ID、全部 config/环境 hash、实际 source 完整 commit/manifest、8TB raw 路径、summary/decision 路径及 root no-argument preflight。此处没有执行这些未来 launch。

## 本地依据

- `README.zh.md`；`CLAIM_EVIDENCE_PLAN_20261031.zh.md`；`ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.zh.md`。
- `PAIRED_AND_RESIDENT_DESIGN.zh.md`；`TARGETED_PRIOR_ART_AND_CLAIM_REVIEW_20261031.zh.md`；`RESIDENT_INDEPENDENT_REVIEW_v2.zh.md`。
- `paired_resident_source_v2/README.md`、`endpoints.py`、`freeze_plans.py`；`paired_resident_inputs_v2/RESIDENT4_v2_FROZEN.json` 与 `resident4_v2_configs/SC_RESIDENT4_V2_fullcall_r0.json`。
- `../dsn_native_resilience_20261030/source_v2/resilience_owner.py`、`fullspec_policy.py`、`resilience_policy.py`、`stage_worker.py`；`PAIRED_POLL_v2_1793434686191349800.json`。

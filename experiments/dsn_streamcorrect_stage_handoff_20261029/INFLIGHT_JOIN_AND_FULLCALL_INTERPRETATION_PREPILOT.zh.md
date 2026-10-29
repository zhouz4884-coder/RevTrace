# Pilot 前的解释约定与有界 in-flight join 假设

2026-10-29，在线三臂 pilot 尚无结果时记录。本文不增加执行臂、不修改代码、不要求 GPU 运行；用于避免把 ready-only 的预设当成 RevTrace 能力上限，也避免把我们自己组装的 full-spec 实现误当成外部已发表方法。

## 1. full-spec 是我们完整原则的一种实际实现

`two_full_spec_early` 是本工作新组装的控制/实现：原 full A+C+U、真实 ASR identity projection、冻结完整输入、已拥有的在途任务保留/完成结果缓冲，以及同 whole-state Consumer 共同组成。它不是原作者公开调度器，也不是外部论文已经实现的强基线。称它“strong control”是为了检验执行粒度选择，不能因此抹掉其中属于本工作的组合。

它实际落实 C1 的部分是：旧 birth/job/epoch 与真实 start 不改；未来父输入未知时可以继续算；实际 complete start 与当前 Canon 相等后保留在途或已完成 full 调用，不重新算、不只比文字；只有实际同-F 完整 start 被否定、已覆盖或 epoch 改变才给 C-entry 取消许可。更早祖先失配只证明 tracked visible chain 失去支持，不证明 future complete input 永不可能收敛。当前 owned policy 的直接输入 override 和收敛 CPU 控件正是这个区分。

它落实消费侧的部分是：未认证的 identity projection 与实际 full conditional closed node 保持不同 provenance；只有当前父输入确认、原 C/U 完成并 WAL/install 后才有 certified 进展；Owner 和实际 Consumer 对完整 branch/cut 独立协调，保留仍支持的未来视图。当前 native 三臂没有重新做完整 R×S 交互分解，因此不能凭它单独宣称在新应用又证明一次 C2 必要性；C2 的交互证据仍来自核心已完成实验。

如果 full-spec 胜过保守执行而 ready-handoff 未胜过 full-spec，可把 **full-call retention 选作 RevTrace 原生应用的优选实现**，stage handoff 保留为另一种受保护粒度及神经可行性证据。论文应透明命名两个作者构建的设计。此时需要停止的是“stage 粒度额外加速”的主张，不是“整个原生反馈协调贡献已经结束”。

## 2. ready-only 与 in-flight full promotion 的能力差异

现有 ready-handoff 明确只接完整已收到的 packet；遇到未完成 A 就立即 full fallback。full-spec 则会把完整 start/epoch 已经被确认的在途 full job 提升为当前 Authority，等待其残余 A/C 完成。二者是有意的不同策略，并非相同的执行保留能力。

以组件均值做一个 **说明性假设时序**：A≈0.435 s，C≈0.269 s，父步骤约在 0.70 s 完成；下一 A 可能已在另一卡执行，但要到约 0.87 s 才产生 packet。在 0.70 s 的 dispatch 时刻，ready-only 会再做一次同输入 A；full-spec 可以继续已经在算的匹配 full call。这个示例不是已测服务收益，但足以说明：如果 pilot 的实际瓶颈是这种重复 A，不能把它直接解释成“阶段交接已到上限”。

## 3. 何时值得考虑一次窄 join 修复

先完整完成和保留原三臂 pilot。只有 raw 事件实际出现以下链条，才讨论另一版本，而不是现在增加一臂：

- Authority 准备 fallback 时，已经拥有且已启动的 protected A job，其完整 start、source/target、is_last、runtime identity 与当前实际 Canon 调用完全匹配，epoch 也相同；
- 这个 A 尚未完整到达 ready cache，因此被 ready-only 忽略，Authority 又启动同输入 A；
- 实际 packet receipt 与重复 full A 的结束时刻显示有可观的 residual-A headroom，且有机会传到原 D2/C8 或实际内容/延迟端点，而非只省内部 GPU 时间。

如果 key/epoch 不同、只是预测输出相似、A 已失去当前输入支持、或者实际残余比重新跑还慢，join 不构成修复理由。也不能通过挑新来源或延后 dispatch 人为制造 join 命中。

## 4. 合法 join 的最小合同

join 只是等待 **已经拥有的、完整输入已被实际根确认的合法在途 A**。它不是等待某个预测未来“可能算对”，也不是允许不完整 packet 进入 C。

1. owner 留存 producer worker/job、原 birth、真实 start/target、epoch、dispatch/start 时间；current Canon 完整 key 与它相等。为该 source 记录明确 joined-work 状态，不改 producer 的出生身份。
2. 等待期间 ingress、其它 source、Consumer 与结果队列继续运行；不能用阻塞全 owner 的 Queue.get 把整体服务暂停。Authority 可继续调度其它源上的合法工作。
3. 只在 packet 完整收到并验证后恢复 open M/B/locals；在真正消费前再次检查 current Root/epoch/key。其后执行同一原 C/U，未执行 C 之前不授 certified 权限。
4. Root/epoch 改变、worker 死亡或有界等待终止时，撤销 join 并进入原 full fallback；不能把超时当成内容不合法，也不能拿 deadline 给未认证输出通行证。源输入/截止期限/all-offered 分母保持。
5. 必须先冻结一个简单 wait bound/fallback 规则。根据原 A 分布给出有界工程参数是允许的，但不是原生服务收益；不能看 pilot 最佳点后调一串 τ。若没有这样的稳健机会，不实现 join。

量级判断是 `residual A + complete transfer/restore < fresh fallback A`，而不是单看 A/C 内核加速。full-spec 的匹配在途 full 本来可能仍更快：它无需跨 worker 交接且 C 已共置。因此 join 既不保证超过 full-spec，也不应被当作一定必须完成的论文分支。

## 5. 如果触发，最少控制与决策

先只加 CPU 的 exact matching in-flight join、foreign key/epoch 拒绝、packet 未完整不进 C、timeout/death 安全 fallback、birth 不改、异步 Consumer/其它源不被阻塞，以及实际消费前 revalidation。再用一个冻结原输入比较 joined packet C/U 与原 full：完整 C 对象、IDs、全闭合状态/文本一致。现有 65 组 packet 等价可复用其相同神经核心证据，但新调度路径/等待行为需要自己的记录与控制，不能重标旧结果。

只有控制通过并且实际 headroom 仍成立，才做原 source0 同 offered/cadence 下的一次 fresh 对照，与强 full-spec 及原 ready-only 的完整记录比较。新代码/配置/门另存；保留原 ready-only 负结果。若 join 仍不改善，就停止阶段粒度加速分支，按已观测的最佳完整组合实现组织原生应用。

这是一条预先写下、由实际瓶颈触发的有界研究判断，不是为了让 stage 必须胜出而无穷追加算法。最终应选择最能支持完整 C1/C2 论文论证的实现和实验，透明报告作者构建的控制、真实结果与边界。

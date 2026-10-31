# 方法叙述与派发作用域修订

2026-10-31。范围：只读检查冻结 NN4f 源，编辑新写作稿的 `sections/03_coordination_algorithm.tex`。旧 release、runtime、原始日志、服务配置、CURRENT 均未修改；没有执行模型、SSH 或新的实验。附件是编辑建议，本文采纳其中有源依据的局部派发表述与层次调整。

## 结论与实际修正

原表中 “prefer missing selected work on a ready worker” 可以被读成跨会话优先派发必要工作。实际实现只保证**在已考虑的某个会话内，先尝试该会话的缺失 Canonical 调用，再尝试其条件尾部**；Owner 的外层顺序仍是 worker→sidlist。不能将这概括为全局 Canonical-first 或公平调度。

这是原伪代码的作用域表述过强，不是新发现的 runtime 缺陷，也不改变已经报告的两客户端 probe。修正文字即可；不需要重跑或为表格另造调度器。

已改成五行 Event / Required evidence / Action 表。caption 为 “Event-driven coordination of confirmed calls and supported whole views.” 对每个读者动作只留一个入口：派发、typed ASR 结果、完整原结果、选中安装、Consumer 应用。完整输入三值、同 session 规则与全局顺序在表前后各用短句解释；producer 死亡和物理退出交给已有执行章节，避免算法表同时承担全部故障说明。

## 源码证据与确切边界

实际神经执行源仍是 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，下列路径均相对 `experiments/dsn_native_resilience_20261030/source_v2/`。归档 GitHub `696bc889…` 不是该执行源。

| 检查对象 | 实际锚点 | 可写入论文的准确意思 |
|---|---|---|
| Owner 扫描范围 | `resilience_owner.py:161–172` | 每次循环先检查 full0/full1 是否 ready 且不 busy，再依次检查 sidlist。第一个合法 start 派发后 `break` 结束此 worker 的 sid 扫描，不先遍历所有会话的必要工作。 |
| 单会话选择顺序 | `fullspec_policy.py:95–103` | `next_full_start(sid,…)` 对给定 sid 尝试 `(canon, tail)`；目标必须已接收、未完成，条件目标满足 max-ahead 且没有重复 owned/buffered work。 |
| 完整输入确认与反驳 | `fullspec_policy.py:29–46` | session epoch 改变可隔离；完整 start 与当前 Canonical 相等可继续；只有实际选中状态在调用自身 start frontier 不同才构成输入反驳。目标已覆盖另判。无此证据返回 unresolved，不把祖先失支持当成已知失配。 |
| 祖先失支持的独立诊断 | `fullspec_policy.py:48–61` | 早期依赖丢失可以记录 `tracked_chain_lost_support_future_complete_input_unresolved`，显式 `c_entry_cancellation_authorized=False`。 |
| 原完整结果接收与 buffer | `fullspec_policy.py:151–178` | 冻结 start、target、完整 record 的 start/end binding、原 authority path 全部检查。已确认结果可选中；未知父输入的完整结果缓冲；已反驳、覆盖或失效 epoch 结果丢弃。 |
| 完整结果替换 typed 预测 | `fullspec_policy.py:123–137` | 原 Correct/Update 可以改变其早期 identity prediction；只保留真实输出能连续支撑的后继，不能重命名不相容后继。 |
| 同步先于安装 | `resilience_policy.py:150–186` | 完整 input 与实际 parent 相等后绑定原 transition；`before_commit` 同步返回 receipt 并再次检查 parent/epoch，才调用安装。未确认结果不能 journal 成事实。 |
| 实际 Consumer | `resilience_consumer.py:26–43,48–76`；`feedback_contract.py:55–70` | fact 顺序、实际父状态、原 record 绑定分别检查。兼容完整路径保留 ahead whole hypothesis；失支持时回退已安装 state。临时 private publication 不能向更短 tail 回退。 |
| producer 死亡后的对象区别 | `resilience_owner.py:74–83`；`resilience_policy.py:274–315` | 先确认退出并验证封闭旧通道完整尾消息，再 fence；未完成 owned jobs 退休，但先前已接受 `completed_full` 和合法视图保留原 identity。这个事实属于故障章，而非派发优先级。 |

## 一个足以否定全局优先级读法的最小交错

这是从分支条件直接构造的**逻辑示例，不是新增实测数据**。

1. 两个会话的 sidlist 顺序为 A、B；full0 正在执行 A 的当前 Canonical 调用，full1 空闲。
2. A 已有合法条件尾部，下一段音频已接收、在 ahead bound 内且尚无重复调用。B 的必要 Canonical 调用也已经 ready、尚未分配。
3. Owner 给 full1 扫描到 A。A 的 Canonical start 因已有 full0 作业而被 `_has_work` 排除，随后 `next_full_start(A,…)` 返回合法条件 tail。
4. Owner 在第172行派发 A 的条件任务并 break，因此本次没有比较 B 的必要任务。

这个交错同时满足单会话 Canonical-before-tail 和跨会话条件任务先于必要任务；两者不矛盾。实际双客户端 probe 的观测属于原冻结试验，应保持其原顺序、阈值和 NO-GO，不能把本逻辑例子冒充另一项 GPU 证据。

## 供 Root 采用的 running example 文字

> Call $j_3$ starts on predicted parent state $\widehat P_2$ while the original correction of its predecessor is unfinished. When the installed parent is the same complete state $P_2=\widehat P_2$, RevTrace keeps the already executing call. The call still runs the original Correct/Update and returns $P_3$, even if its early prediction $\widehat P_3$ differs. The Consumer separately checks whether its entire current hypothesis has a continuous dependency path from the new selected state. A missing path withdraws that view without proving that every later, still unresolved call input is wrong.

该例子要在正文注明“same complete state”包括实际 frontier 与冻结音频/target/EOS/model/decoding 合同，不能只比较转录文本。producer 死亡另用 accepted-before-death 与 newly arriving fenced message 作具体区别，不把两条交错强行画成一条实测时间线。

## 符号与阅读次序建议

- Canonical/selected state 保留 $C$；纠错动作在解释与图中写 **Correct/Update**，避免相邻 $C$ 与 C/U 误读。
- $P_i$ 是完整反馈状态；其 frontier 与剩余绑定由 contract 给出。$\widehat P_i$ 是预测状态，不能用字体颜色暗示已获选择授权。
- $h$ 固定为实际 Consumer 当前完整假设，$S(C,h)$ 固定为整视图支持检查；不要同时用 $S$ 给 selector 命名。
- root 是完整依赖路径的起点，frontier 是已处理音频边界，durable fact 是一次原选中转移的持久记录；它们不是 state 的文风同义替换。
- 解释次序宜为：一个原调用→条件输入→后来确认→原 Correct/Update 结果→独立显示判断→事件表→充分条件与 selected-trace argument。

## 主张—证据核对

| 表中动作 | 依据 | 状态 |
|---|---|---|
| 不改输入身份而保留已确认调用 | `_refresh_active`, `_reason`, `register` 原 job 不重建 | supported；不是承诺所有 speculative calls 均成功 |
| 未知父输入缓冲且不授权选中/反驳式取消 | `_reason`, `complete`, `pop_ready_commits` | supported；覆盖/epoch 改变仍可合法退出 |
| typed ASR 不直接产生选中事实 | `admit_asr` 与 `complete/_commit` 分路 | supported；不声称其文字人工正确 |
| 原完整结果同步后才安装 | resilient `_commit` | supported conditional guard；没有新全Python/CUDA证明 |
| 视图保留与回退按完整支持路径 | actual Consumer + Reconciler | supported；对不支持的 ahead view 必要撤回仍发生 |
| 跨会话全局 selected-first、公平性或成本最优性 | 不由当前循环提供 | unsupported，不写入算法 |

本次使用 latex-paper-en 的 method/section-writing 与 IEEE pseudocode 指南。没有调用编译器；全稿排版与字体/overfull 检查由 Root 最终构建完成。本地只做源码阅读、锚点和新 TeX 的静态语义核对。`tab:coordinator` 和 `sec:protocol` 锚点保持不变，无新 citation、runtime 参数或实验结论。

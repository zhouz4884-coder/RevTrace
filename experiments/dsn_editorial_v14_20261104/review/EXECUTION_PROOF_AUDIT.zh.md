# v14 选定轨迹证明与执行路径审计

结论：冻结 NN4f 的实际路径支持补充早完成子调用的交错说明。没有发现需要修复运行时代码或重开 GPU 的真实正确性缺口；当前 Proposition 3 的问题是证明未显式展开这一交错，而表 I 已描述相同处理。此次只读源码和稿件，新增本审计两份文件；未修改运行时、稿件、旧数据或旧归档，未运行测试、GPU 或远程任务。

审计 ID 为 `REVTRACE-DSN-EDITORIAL-V14-EXECUTION-PROOF-20261104`。审查基点是用户给定的 v13 修订计划及 `Paper_DSN/revisions/20261103_dsn2027_release_v13/`。执行源码为 `experiments/dsn_native_resilience_20261030/source_v2`，实际 HEAD 为 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`；该完整 commit 在本地可解析，`git status --porcelain` 为空。对 `packages/SOURCE_v2.json` 的 59 个条目逐一重算 SHA-256 和字节数，全部一致；Git 跟踪集合也恰为这 59 个文件。manifest SHA-256 为 `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457`。这是一致性审计，不是新实验或环境/GPU 门。

## 实际交错与精确锚点

以下 `source_v2/` 锚点均相对于 `experiments/dsn_native_resilience_20261030/`。

1. **未知父输入的完整结果先缓冲。** `source_v2/fullspec_policy.py:151–164` 先绑定原 job、完整输入/输出 cut、原 authority 记录和时钟。`_reason` 在 `29–46` 仅凭实际同前沿不一致、已覆盖目标或 session 改变提供拒绝理由；更早祖先失去支持不自动反证未知未来输入。完整 start 尚非当前 Canonical、且无上述拒绝理由时，结果进入 `completed_full`。因此不应将证明写成“所有早完成结果必定一直等待，最终均会选中”。

2. **缓冲队列按实际父状态释放。** `fullspec_policy.py:166–179` 每轮重新检查拒绝理由，只有 `item['job']['start'].same(self.canonical(...))` 才调用 `_commit`；`139–142` 在安装入口再次要求同一完整父状态及 session。到达时间决定先检查哪个候选，不决定投影边顺序。`feedback_contract.py:15–33` 的 `FeedbackCut.same` 比较包含 frontier/contract 的完整声明状态的规范字节，而非文本或 birth version。当前父状态装好后下一轮才可能使子结果就绪。

3. **append 前检查实际父，sync 后才安装。** `resilience_policy.py:150–186` 在同步 hook 前校验当前完整父状态和 session，将完整 parent/next、原完整 C/U 记录和原 job 绑定到 transition；hook 返回后在 `175–176` 再查父状态和 session，然后才进入 base `_commit` 安装。`resilience_owner.py:33–48` 的实际 hook 同步调用 `store.commit`，获得 receipt 后才安装/发布。

4. **持久层也检查真正的 durable parent。** `resilience_storage.py:71–81` 校验 parent 等于 store 当前 root，完整 job start 等于 parent，record 的 frontier、start/end digest、authority 和 complete C/U 字段一致。`82–102` 将 framed/chained fact 写出，执行 `flush/fsync` 后才推进 durable root 并返回 receipt。写结果不确定时冻结 writer；hook 不确定或持久事实未完整安装时也冻结 Owner。durable root 与 Owner installed root 是不同阶段；Owner 在 sync 后崩溃可以由恢复安装该事实，不能把安装当成第二次选定边。

5. **串行是明确前提和具体部署约束。** `resilience_owner.py:113–151` 的一个 Owner 事件循环串行处理 ingress 与 `pop_ready_commits`，其 `33–42` hook 为同步调用；`51–66` 把入站事件交给该 policy。此路径支持现有“exclusive serial selection”前提。代码没有原子 CAS，也未证明允许任意多个线程同时写入同一 FactStore。

6. **完整输入不仅是 mutable state。** `fullspec_policy.py:105–117` 冻结原 job；`stage_policy.py:25`、`stage_packet.py:55–59` 的 key 绑定完整 start cut、source hash、target、EOS、新增音频字节和 runtime identity。`stage_policy.py:39–44` 维持物理 channel/job/source/session 绑定。append 时重新核对当前完整 start；其余输入继续使用已经冻结的不可变绑定，不是在选定时重新执行模型。可信完整原执行、声明状态充分和不可变音频/模型配置仍是必要前提。

7. **重复交付/恢复不增加选定边。** `resilience_storage.py:61–80` 重放时仍校验每条实际 durable parent。`resilience_consumer.py:26–47` 要求连续 durable sequence、完整当前父状态和原结果绑定，已应用事实的 replay 不再应用。它补充支持现有稿件按“distinct durable facts”定义投影的边界，不把 provisional view 也放入该投影字母表。

## 稿件最小补充

v13 `sections/03_coordination_algorithm.tex:23–30`（表 I）明确“confirmed 才选定、unknown 缓冲、refuted/covered/fenced 拒绝”和“sync 后安装、重查 pending”。`sections/03_native_refinement_working.tex:21–40` 的 Proposition 3 保留这些条件，但证明没有明写提前完成子结果的等待与重查。建议在 “Deleted actions do not extend the prefix.” 之后插入：

> A complete result that arrives before its parent is installed is buffered while its input remains unknown. Under exclusive serial selection, the actual parent and complete frozen input are revalidated before appending and synchronizing the child's fact, so completion order cannot introduce a parentless projected edge.

其中 “while its input remains unknown” 保留 actual mismatch、covered target 或 fencing 可拒绝的情形；不能解释成未知就是被反证，也不能解释成所有未知最终都会确认。该文字仅展开现有归纳步骤，不改变命题的充分条件。

必须保留原任务允许关系可非确定、原完整执行可信、全部相关 mutable state 充分、消息身份与权限正确绑定、排他串行选定、存储兑现成功同步等前提。这里没有普遍活性、RTO、D2/C8、全局文字单调或任意 GPU 重跑逐位确定性的保证，也不是整个 Python/CUDA/OS 栈的机器证明。

## R/S 是动作开关的准确措辞

v13 `sections/05_evaluation_core.tex:33–38` 已写共享 validation/durability 及关掉 retention 后的动作。可以增加一行：

> Here $R$ and $S$ enable retention actions; all four arms share input-admission and view-application safety checks.

EL/SUP 是判据或安全义务；R/S 是研究中的动作选择。R=0 从选定反馈重建工作；S=0 使用经过检查的 installed snapshot。它们不会授权无效调用写入 Canonical，也不会授权不受当前根支持的实际 ahead view。

技术精度需要注意：**不能把上述话解释为四臂逐字执行完全相同的可选 retention 函数。** 补充查看的 core `experiments/physical_retirement_20261028/source_v3/runtime/src/revtrace/live_qwen.py:651–670` 表明 R=0 会跳过 `eligible_chain` 的保留分支；`certified_display.py:81–93` 表明 checked snapshot 在 Canonical application 时不尝试保留，但对新 provisional view 仍做路径兼容检查。共同的 `kernel_runtime.py:26–55` 在真正替换 view 前走 kernel gate；`composed_kernel.py:179–203` 执行选定输入/原结果/持久化检查，`218–240` 对任何实际 ahead view 验证完整支持路径。准确说法是保留动作可关，输入准入与实际视图应用安全门保留，不能声称“R=0 关闭 EL”或“S=0 关闭 SUP”。

core 的上述本地路径由 `experiments/dsn_service_stability_20261028/PLAN_v1.json:6–7` 指向；此次完整 manifest 校验仅针对 NN4f，没有重新认证整个 core 档案或重跑四臂。NN4f 的 native 两臂本身是 fullcall/conservative，并非 R/S 四臂接口。此补充不能混淆两组研究。

## 证据层级与 gate

条件证明建立选定投影的安全性质；本次静态阅读与 59 文件身份核验支持“实际冻结代码与该证明前提相符”的有限结论。已有 `test_fullspec_policy.py` 中 future buffer/matching-parent、wrong-parent、ordered future-node，以及 `test_resilience_policy.py` 中 hook-before-install 等测试定义此次只读，没有运行，不能报为新的 PASS。稿件已有有限状态/独立 trace checker 计数没有在这里重算，不能由本审计升级为全栈机器证明，更不是新服务结果。

Gate：**允许最小证明补充和动作开关澄清；保持运行时代码、旧实验、分母、期限和统计结论冻结。本次未发现触发修复或新增实验的正确性缺口。** 结构化锚点和边界见同目录 `EXECUTION_PROOF_AUDIT.json`。

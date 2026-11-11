# UIR：保留已派发计算，继续验证使用资格

**Safe UIR 不是无条件使用结果。** 新增 `uir` 臂与 RevTrace 共享完整输入分类、原实际父状态 AU、durable-before-install、整视图 SUP 和真实 Consumer；唯一差异是 Owner 对已派发调用不发送协作式 before-C skip 提示。已确认输入失配、已覆盖或会话过时的调用可以继续耗用其物理 worker，直到真实完整终结或实际故障；结果仍按原规则被拒绝、缓冲或选择。

这项对照回答“已知失效后提前停止计算是否有实际资源/期限价值”。它不能单独回答“输入确认是否可以移除”。即便 UIR 与 RevTrace 性能相同，两者仍共享 end-use 实际父输入检查，因而不能据此写成 EL、AU 或 SUP 冗余。safe UIR 和 unsafe UseAll 必须分别命名。

`UnconditionalInflightCoordinator` 不覆盖 `_reason`、`_commit`、view admission、ready selection 或 SUP。共享 `process_c_entry_hints` 仍调用原 `invalidations()` 分类；UIR 仅禁止把理由转发给 worker。日志记录 `input_or_coverage_reason_observed_without_C_entry_skip`，并显式给出 `c_entry_skip_hint_sent=false`；调用失配不能被重新表述成输入合法。

CPU 负控 `test_unsafe_UseAll_CPU_fault_model_exhibits_wrong_parent_transition` 故意直接调用低层 Reconciler.install，展示去掉使用权守卫会允许错误父输入的转移。它不创建授权持久事实，也不导出新的服务臂。live exact 模式中不存在 unsafe UseAll。

## Ready-only 的严格时刻

冻结定义：**在每次实际 canonical install 之前，Owner 已完整接收、验证并放入 ready bank 的完整原始结果**。worker 的 `model_end`、终结 frame 已发送/到达 reader 但仍未被 Owner 处理、以及 Consumer 最终 apply，都不是这个 ready 边界。相同时间戳或同一批队列中的消息按 Owner 串行 dequeue 顺序处理。

为避免靠粗略日志顺序猜测，新源码统一记录：

| 阶段 | 字段与含义 |
|---|---|
| 原模型/worker 完成 | 原 `model_end`、`worker_job_end_perf`；保留原计时作用域，不能冒称硬件 attestation |
| worker 发送 | 原终结事件 `sent_perf` |
| reader 完整接收 | `channel_received_perf`，来自绑定 FramedReader envelope |
| Owner dequeue | `owner_dequeued_perf` 与递增 `owner_dequeue_sequence` |
| 完整结果验证 | `complete_receipt_order={sequence,observed_perf}`，完整绑定校验通过后记录 |
| 实际 canonical install | `canonical_install_order`，低层 install 后立即记录，早于后续 publication/Consumer apply |
| 其他 ready bank 快照 | 每次 install 的 `other_ready_full_receipts_before_install`，逐 job 列出其他先前已验证的 receipt；本次选中 item 可能已从 bank 取出，其 receipt 单列于结果的 `complete_receipt_order` |

policy execution sequence 在一个 Owner 协调器内统一涵盖 dispatch registration、完整 receipt 验证与 canonical install，数值顺序是同时间戳的因果判据；恢复后的 Owner 用其 owner epoch 区分序列。`validated_full_receipt` 诊断 journal 行在 receive_event 返回后才写出；其中可能已经完成实际 install，因此不能按该 journal 行的时间推定 receipt 与 install 的顺序，必须使用嵌入的两个 policy sequence。诊断 Owner journal 另有单调序号。消息内容本身不加入可变接收序号，保持原 inbox semantic fingerprint 和重复消息语义。

## 固定比较合同

所有长度层仍为16 kHz音频、500 ms输入释放、每次原完整调用至多推进8000 samples，所有臂相同；长度不是调整调用粒度的理由。两完整FP32 worker、模型、Correct/Update、warmup/READY、AU、SUP、WAL、Consumer、D2/C8与功耗作用域不变。

主臂建议：Conservative、dependency-versioned、ready-only、RevTrace、safe UIR。strict birth-root 保留为清楚命名的附录控制。新增源码位于 `baseline_source_v2`，由已冻结v1实际提交 `23538150798378c6629c8f75ec87426bb05574b4` 的62文件逐字节复制后修改；v1没有编辑。v2实际执行提交必须重新冻结，不能复用v1或NN4f的身份。

状态：实现与命名CPU控制已完成；等待根代理新版计划写完后，再冻结并执行正式CPU验收。未启动GPU。

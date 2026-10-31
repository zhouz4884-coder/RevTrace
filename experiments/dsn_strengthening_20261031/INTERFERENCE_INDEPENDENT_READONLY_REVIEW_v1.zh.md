# 两客户端 interference source 简审 v1

日期：2026-10-31。审查 HEAD：`61abb744b90dda3fa4dd976e5deca75fd6e10d00`（当前 clean development/review commit，尚未正式冻结）。范围为新增 contract/observer/supervisor/analysis/campaign/prerequisites/plan 和相关 CPU 控制；未执行完整 73 控、远端、NN、CUDA、signal、CURRENT 或 Git 写操作。仅新增本报告。

结论：**发现 1 个前置证据接口阻塞，已立即通知 root 与 `paired_source_design`。** 暂未发现返回值篡改、调度替换、NN59 文件编辑或将观察 proposal 直接算成实际干扰的实现。此简审不能替代正式 freeze 后的全部 CPU、源身份和进程清理门。

## P1：当前 prerequisite 无法直接消费冻结 reader v2 的真实 posthoc 输出

位置：`interference_prerequisites.py:11-14` 对照 `buffer_fixture_source_v2/reaudit_buffer_witness.py:108-130`。

interference 前置证据要求四个 `buffer4_gates` 顶层 status 中恰有两个 `PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MATCH`、两个 `PASS_CONTROLLED_REAL_NN_BUFFER_POST_PRODUCER_DEATH_MISMATCH_REJECTED`。但原执行 `BUFFER_WITNESS_GATE.json` 按要求保持 FAIL；新冻结 reader v2 输出的是每格 `PASS_ZERO_NN_POSTHOC_MECHANISM_REAUDIT` wrapper，机制 status 位于 `mechanism.status`，aggregate gate 则是 `PASS_COMPLETE_ZERO_NN_BUFFER4_POSTHOC_REAUDIT`。因此目前已定义的正确输出都不能直接通过这个前置门槛。

已进行纯内存复现：用正确 shape 的两个完整 prior summaries 加四个 `PASS_ZERO_NN_POSTHOC_MECHANISM_REAUDIT` wrapper（其 nested mechanism 为两个正/两个负，complete raw/watchdog unchanged 为 true），仅 mock receipt 读取，`validate_prior_scopes()` 拒绝并报 `real buffer two-positive/two-negative scope not complete`。0 NN、0 文件写入。

最小修复：显式支持并严格绑定新的 posthoc 证据类型，检查 wrapper PASS、nested mechanism、两个正/两个负的真实 cell UID/重复身份、analysis source/config/input provenance、原 raw/watchdog unchanged，以及原 gate 保留。若依赖 aggregate analysis gate，也必须 hash 绑定该 gate 与四个 case 文件，不能只读取任意含 PASS 字符串的对象。文档与 PRELAUNCH schema 同步说明这是原真实 NN 证据的独立复审；不得覆盖原执行 FAIL，不得生成冒充原执行结果的旧式 PASS 文件。

## 已核对的关键路径

- `TwoClients` 固定 A/B partition、B 首次 planned origin = A origin+2s；late poll 不重设 origin，后续请求仅本 client 的 actual canonical Consumer EOS 推进。未使用私有 EOS 释放请求。Ingress 保持每 request 的 500ms/原始 EOS。
- `attach_observer` 只包装原类的 `next_full_start/register`，调用各自一次、返回原 proposal/job 对象，不调用另一 sid 的 scheduler。快照读取 canonical cuts/live jobs/completed jobs 与已接受 frontiers；其日志开销被明确计入新实验条件。没有实现新优先级、quota 或 cancellation。
- 原 Owner 的 sid/slot dispatch 循环、C/U、eligibility、facts、Consumer 与 worker 入口仍来自原 NN59。新 Supervisor 负责双客户端 ingress/observation，`maximum_owner_restarts=0`；Owner 内原失败替换若发生，会被最终 continuity 检查拒绝，不能成为成功 trial。
- `audit_dispatch` 要求 observation、raw dispatch 和原 worker terminal UID 集合一一对应，并检查完整 start/source/epoch/slot、物理工作起止、原 ingress 前缀、Canonical install/durable facts 与 lease；proposal 本身不能算实际 inversion。B 在 decision snapshot 之后才接受的输入不能计为已经 ready。
- 原状态/C/IDs reference 与原 request clocks 保留；all-offered D2/C8、EOS/non-EOS、held views、authority 和两块板的 energy 都保留。GO 使用每个 repeat 的实际 B-ready inversion 加配对 B 服务退化，不把两个重复池化，也不声称已实现 scheduler 改善。
- 四格 queue/固定2s/原4来源/门槛为预先固定条件；首对 NO-GO 后留存两格 unrun，最多 4 actual attempts。720s 外墙钟与40s本次进程组清理存在；清理继承 a13 的 PID generation/session/descendant 证据，不全局 kill CUDA PID。正式运行仍需已授权独占 GPU、完整 assets/READY/allocator/source 门。

## 限制

这是 reader 审查后的补充源码简审，未实际重跑 73 控、真实 coordinator differential、Linux cleanup control 或双客户端 NN。正式冻结前需完成接口修复和回归；后续若出现真实 service/reference 失败，应保留失败而不能调整 phase/source/阈值获取 GO。

# Interference prerequisite 修复独立复核 v2

日期：2026-10-31。结论：**NO BLOCKER，可以提交本轮稳定 development 修复；正式冻结/源身份/Linux 控制/实验窗口仍由 root 分别执行。** 本次仅本地只读源码、实际下载结果和纯内存函数控制；0 NN、0 CUDA、0 remote、0 signal、0 scratch 文件。仅新增本独审报告，未修改源码、NN、CURRENT 或 Git。

复核文件：`interference_source_dev/buffer_reaudit_prerequisite.py`、`interference_prerequisites.py`、`PREREQ_ROOT_CLARIFICATION_20261031.md`，并对照实际 `FINAL_CPU_AND_POSTHOC_RESULTS/posthoc_v2`、reader31 与原 buffer/resident bounded 下载证据。审查期间修复尚未提交；正式提交后的完整 commit/manifest 应由 root 再冻结。

## 已关闭的接口阻塞

旧前置门槛只接受旧式顶层机制 PASS，无法消费 b867 的实际 posthoc wrapper。本修复显式区分 posthoc PASS、nested real-NN mechanism、原任务/reference PASS 和原 reader/CLI/watchdog/compound FAIL，没有改写原执行结果。

`validate_buffer_reaudit():92-117` 的 runtime 绑定链覆盖：

- 固定 b867 完整 commit/manifest、原4eb manifest、固定原 plan SHA 与 analysis frozen-config SHA；analysis dependencies 的 manifest/clean checkout 字节验证。
- input-index remote config 路径、analysis run record、actual config/environment 独立 SHA 与 whole JSON、aggregate output 路径。
- 固定原 plan 的四格身份/正负/request order、四个原 config SHA、原 run-record 中 actual config/environment SHA 与 dependencies。
- per-case wrapper 与 aggregate summary 对象相等；完整 before/after raw/watchdog 索引相等；mechanism 输入 SHA、原 gate SHA 与完整索引交叉绑定。
- 当前每格 raw/watchdog 目录全部文件重新枚举并哈希，要求与 posthoc 前后索引完全一致；原 resident/buffer/watchdog gate 的当前 body/hash 再校验。
- 原 compound gate/summary 保持 `NO_GO_COMPLETE_BUFFER4_NEGATIVES_PRESERVED`；原 buffer 失败必须是已知 receipt-reader failure，CLI exit1、未 timeout、watchdog FAIL 与实际 cleanup 证明均保留。

`audit_schema():51-82` 还要求完整原任务/reference/clock/all-obligations、全状态历史前提、旧 UID/incarnation/fence 时序、正例 actual install+consume 或负例同 frontier discard，以及两个原始正/负重复。只提供 wrapper 顶层 PASS 不能放行原任务、协议或物理释放失败。

## 本次实际控制

实际下载四格 schema 正控通过，返回 `PASS_ORIGINAL_REAL_BUFFER4_MECHANISMS_VIA_B867_ZERO_NN_REAUDIT`；原执行状态仍为原 compound NO_GO。每格完整索引为 raw 31 个文件、watchdog 4 个文件。

另以实际下载对象的深拷贝运行 8 个独立内存反例。修改 case 后同步 aggregate case，避免仅因 case/aggregate 不一致而提前失败；以下全部被对应实质检查拒绝：

1. 原 task/reference FAIL。
2. 原 request clock FAIL。
3. 原 cleanup 的 CUDA release 未确认。
4. nested real protocol/mechanism FAIL。
5. 原 reader buffer FAIL 改成 PASS。
6. 原 compound NO_GO 改成 PASS。
7. raw before/after SHA 不同但 wrapper boolean 仍为 true。
8. mechanism 输入 SHA 与完整 raw 索引不符。

本次未重新执行作者所报 98 控，也未访问远端完整 raw；runtime 全树复核的实际 Linux 执行结果应由正式 prelaunch receipt 提供。以上正控/负控是本地真实下载 schema 的独立验证，不称为新的神经实验或远端当前全树验证。

## Resident 7/8 澄清

新 root 澄清在任何双客户端输出前接受完整任务/reference/clock/PID 和既定强 E2E 机会作为前置门槛，保留实际 SLO misses；不再要求假定的 8/8。代码与这一澄清一致。

对实际 resident summary 执行 `useful_resident_scope()`：r0 Full-call 4/4、Conservative 0/4，实际 credit 增益 17.2080625 秒；r1 Full-call 3/4、Conservative 0/4，实际 credit 增益 15.9108125 秒。结果显式记录不要求每个 request 的 D2/C8 全过、保留实际 misses。原 task/reference、request clock、missing frontier 或 continuous PID 字段失败仍会阻塞。双客户端 fixed2s、原4来源、all-offered D2/C8、NN59/C/U、原 proposal、最多四次与首对 hard stop 未因本次修复改变。

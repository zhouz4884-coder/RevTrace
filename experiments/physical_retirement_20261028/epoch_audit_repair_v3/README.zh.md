# Staggered 空 epoch root 的记录级审计修复

原始运行是 `confirmation_dev_v2/dev-qwen-rho1-staggered-two_lane-r0`，真实执行提交 `1d8c30804a945570429d85d934b3bfcba6171a43`，runner returncode 为 0。原 v2 源码、raw、STOP 和失败 GATE 未修改。

提前于 source arrival 的 14 条实际 Consumer 记录均为 session 1–7 的 `view-mode` 控制，各有 RECOVERY/NORMAL 一条。它们全部为 version 0、certified/visible frontier 0、两个文本严格为空、所有 certified identity 为 null、`no_certified_snapshot_yet=true`，提前 0.1505–1.6554 秒。它们表示已声明会话的空根，不是已接收或展示音频。

修复只允许这种严格空 genesis 控制越过“source 尚未出生”的断言；保留实际观察与服务器发布的因果检查。任何正音频、非空文本、非零 canonical version、已有 selected identity 或实际 suffix/retention 仍被拒绝。空根不计入任何正 frontier，原始音频 release、2/8 秒期限、D1、input/WAL 和 Consumer 检查保持。

本目录完整记录一次通过远端 stdin 在内存中执行新审计函数的只读复算：

- `retirement_audit_snapshot.py` SHA256：`7d3cccc7d58f604a1a5af426b9b31256749630e5921b55c7dfd130f02ff6f9f8`。
- `read_only_epoch_reaudit_program.py` 是完整只读程序，导入仍冻结的 v2 `x_service_metrics`，没有运行推理。
- `read_only_epoch_reaudit_stdout.json` 保存 14 条实际提前空根记录和完整审计结果。

复算通过全部独立 retirement/input/Consumer 检查：132 个完整行、50 个物理批次、66 个 offered frontiers、8 个来源、最终覆盖率 1.0、没有未完成输入。display P99 1.83193 秒、commit-view P99 2.30808 秒、双 P99 通过；WER 10/340 = 2.94118%。该变化是纯审计解释修复，不需要重跑原 GPU 来证明这些已有数据。

这次内存复算按文件 SHA 标识，不能冒称原 v2 运行自带的新 gate。主线程随后将同一审计修复冻结到 v3 提交 `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`；正式新身份的完整审计和新的 H3 执行应另建输出。v2/v3 的 runtime、actuator、Consumer 和 service 文件逐字节相同，变化仅在独立审计与针对性测试。

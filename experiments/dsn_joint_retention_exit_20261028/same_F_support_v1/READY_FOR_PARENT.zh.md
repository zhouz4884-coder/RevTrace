# READY：全 24 格首次消费的后验同 F 完整文本支持

**仅本地方案、源码与 controls 已完成。没有 stage，没有读取远端，没有真实质量重计结果，没有新 GPU。**

实验 ID 为 `REVTRACE-DSN-RXK-SAMEF-SUPPORT-20261029-v1`。事前冻结范围为原 24 格、全部 offered、原 first D2/C8 credit，以及 c25b0655 诊断的六 sync 后继批全部 96 行。unknown 单列；不截更长 Canon，不换期限或 first-credit。

- 质量 CPU 计划：`PLAN_v1.json`，SHA256 `35dfd8739cfedc594217406695d72c5d36e23b6fac7a6f18cd513c0d41bd155d`。
- 主重计直接复用 **fde6272b494db43a66eebea7444d7c9d1037e687** 的完整干净源与 manifest，`run_analysis.py --components usefulness`；脚本字节没有改动。
- 独立 orchestration/96 行补充源：**5d1de66a31fb0921206da33256a93f5d29552e58**，完整 `SOURCE_v1.json/.bundle`。它区分自己的执行 commit 与 fde 的实际主分析 commit。
- 11 个本地 synthetic CPU controls PASS，覆盖同 F 缺失为 unknown、更长文本不得截断、公共前缀不等于全文一致、raw/norm 分离、已选中与 future 分离、首次 Canonical 覆盖、原信用完整分区和真实 fault flag 缺失/矛盾。不是 24 格真实质量结果。
- `NEURAL_PLAN_v1.json` 与原 d5da… 神经计划字节相同；`TARGET_BATCHES_v1.json` 固定全部 96 行；`PRIOR_INPUT_RECORD_v1.json` 固定旧 v2 已读原始输入 SHA。运行时至少重验 216 个 core 原输入/metadata hash 的交集。

## 未来一次短 CPU/IO 窗口

等待 root 明确分配：**完整 native scope + postanalysis 结束之后、12 格中点 GPU 之前**。当前 native 计时期间不运行下面的 execute。

`stage_launch_v1.py` 默认只是本地 dry-run，不打开 SSH。root 在窗口分配后，提供两个实际完成 gate 的路径和精确最终状态；允许已完成的有证据负结果，不要求 native 科学结论为正。

```text
python -B experiments/dsn_joint_retention_exit_20261028/same_F_support_v1/stage_launch_v1.py --execute --native-scope-gate <actual native scope GATE path> --native-scope-status <exact final status> --native-postanalysis-gate <actual native postanalysis GATE path> --native-postanalysis-status <exact final status>
```

它先检查原 C3 三门完整 PASS、native 两门精确最终状态与 GPU 全空，才传有界源码/配置、在 8 TB 盘独立目录 clone，并 detach CPU runner。运行前写实际 config/env/raw/summary/gate 记录及资源窗口记录，stdout/stderr 由远端持久日志持有，给出 PID/start_ticks/cmdSHA handle。

远端执行源/输入：`8TB/projects/revtrace_physical_retirement_20261028/dsn_joint_same_F_support_v1/`。

远端新结果：`8TB/results/revtrace/physical_retirement_20261028/dsn_joint_same_F_support_v1/`。原大日志仍是旧 `dsn_joint_v1/`，不会复制或覆盖。

完成后用 `poll_remote_v1.py` 经既有 remote.py 读取精确 handle/gate；`fetch_results_v1.py --execute` 仅在新质量 gate PASS 且 GPU 空闲时有界取回，逐文件比远端 SHA。默认也是 dry-run。

预期关键输出：

- `primary/usefulness/`：原 fde 全 24 主重计，保留所有 offered/first actual view、所有 ahead view、raw/norm 同 F 状态与未来/已选中区别。
- `ALL24_SUPPORT_PARTITIONS.json`：每个原 first-dual-credit 的已认证/完整 ahead 一致/不同/unknown 分区，分区和必须等于原 credit。
- `SYNC96_COMPLETE_VIEW_SUPPORT.json/.csv`：六批全部 96 行，包含原 miss→hit 分类、完整 same-F 比较、实际 worker fault flag，不按结果删行。
- `SYNC96_SUMMARY.json`：每批及其 miss→hit 子集的 raw/norm 相同、不同、unknown 和实际 fault 数。
- `INPUT_BASELINE_REVALIDATION.json`、config/env/run record、完整 gate 与原输入 hashes。

不同/unknown 都是完整科学结果；仅缺失证据、源身份/原输入/原信用矛盾才 FAIL_PRESERVED。后验选中 Canonical 一致不是在线认证、groundtruth 或语义正确，也不能用最终 WER 相同替代它。

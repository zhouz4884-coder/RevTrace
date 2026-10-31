# Resident cleanup v2 独立复审

结论：`PASS_CODE_REVIEW_NO_ADDITIONAL_FREEZE_BLOCKER`。可按新来源身份冻结/交付当前 harness。v1 的已注册 dead-Owner 跳过清理缺陷已在实际 `run_resident` CPU 控制流中修复；本次没有发现新的具体阻塞缺陷。本结论不替代 Linux 真实孤儿进程组控制或真实 CUDA/NVML 释放测量。

审查 ID：`RESIDENT_INDEPENDENT_REVIEW_CPU_20261031_v2`。实查来源为 `D:\VLA_QWEN\RevTrace\experiments\dsn_strengthening_20261031\paired_resident_source_dev`，HEAD `a13fa0a335529dc188f7e738877a3acd027ce4a7`，复审时 `git status --short` 为空。没有修改该 source、NN4f、CURRENT 或 root Git；报告位于 source 父目录。CPU 环境仍为 Windows 11 / `E:\Anaconda\python.exe` / Python 3.13.5。

核查与实跑结果：

1. 独立重跑 `python -B -m unittest -v test_controls test_supervisor_cleanup`：28/28 通过。注册后、READY 前、leader 已死的反例现在调用 group cleanup 一次；cleanup 抛错时写 `FAIL_RESIDENT_OWNER_CLEANUP_RELEASE_UNVERIFIED`、`confirmed_physical_release=false` 并抛 `CleanupError`。对应 `resident_supervisor.py:186-205` 与 `test_supervisor_cleanup.py:30-40`。
2. `process_cleanup.py:59-81,89-118` 先验证启动 PID generation；live leader 必须匹配自身 PGID/session；leader 消失时，必须存在同次运行已记录的精确 worker PID/start_ticks 才授权 group signal。外来 session、复用 PID、未知 worker generation 均有拒绝控制。未注册且尚未 setsid 的分支只杀精确 launched leader，不推断其继承 group 属于本运行。
3. `process_cleanup.py:82-104` 对每次 CUDA owner CLI 调用设置 timeout，并对整体 release loop 设 deadline；CLI 失败、格式错误或超时不能退化成空 owner 集。失败路径不再用 leader-only kill 伪造 group/CUDA release。
4. 独立额外执行 4 项 mock 控制，全部通过：未注册但精确自有 session 委托完整 group cleanup；pre-setsid 分支只杀精确 leader；outer watchdog 在 release 检查前先对全部已证明 groups 发 signal；outer release 错误传播为 `CleanupError`。这些控制不执行 OS signal、模型、GPU、CUDA 或 NVML。
5. paired/resident 外层都在 Popen 后立即捕获 `child_start_ticks`；异常时把 READY worker 的 PID/start_ticks 传入同一 cleanup API（`run_paired_campaign.py:145-164`、`run_resident_campaign.py:23-47`）。`stop_owned_processes` 先保存精确 live Popen 后代 session 证明，停止 Supervisor，再重读 metadata，再 signal 所有已证明 Owner groups；最终 release 失败会保存独立 FAIL 记录并终止队列（`run_paired_campaign.py:9-57`）。没有“cleanup 不明但继续下个 cell”的分支。
6. 对比 v1 的 Git 差异确认：`endpoints.py`、`audit_results.py`、`common.py`、`resident_analysis.py`、`external_power.py`、`resident_entry.py`、`test_controls.py` 未修改；本次 cleanup 改动没有改写先前审查的请求原点、500 ms/EOS、C/U 或静态 source marker 映射逻辑。

保留的证据边界：

- `linux_cleanup_control.py` 明确使用真实 POSIX 进程组、synthetic CUDA owner response；Windows 复审没有执行该脚本。root 后续应单列其实际结果，不能把该 PASS 写成真实 NVML/CUDA 释放证明。
- 32 个 CPU 控制（28 + 4）验证的是代码控制流及反例，不是 GPU serving、性能、四请求任务成功或自然 fault prevalence。
- v1 的 reference audit 与完整物理 trace refinement 的范围区别继续成立，本次没有扩张其声明。

冻结决定：当前代码未见新增 blocker；使用 `a13fa0a335529dc188f7e738877a3acd027ce4a7` 的完整 manifest/新 plans，保留 78b92f 的历史身份。进入真实模型 launch 前仍执行既定 source/environment/asset gates，并记录 root 的 Linux OS 控制与真实 GPU 观测。

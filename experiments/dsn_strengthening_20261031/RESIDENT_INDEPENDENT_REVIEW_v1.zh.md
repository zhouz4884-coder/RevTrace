# Resident 独立正确性审查 v1

结论：`HOLD_FOR_OUTER_SUPERVISOR_CLEANUP_FIX`。发现 1 处可复现的异常清理缺陷；未发现正常路径改变原始 C/U、提前释放下一请求、重置请求时钟或提前复用物理作业的具体缺陷。修复只需要新的外层 harness 来源，不需要修改 NN4f。这里没有 Linux/GPU、性能或任务成功的新结果。

## 身份、范围与检查结果

- 审查 ID：`RESIDENT_INDEPENDENT_REVIEW_CPU_20261031_v1`。
- E：`D:\VLA_QWEN\RevTrace\experiments\dsn_strengthening_20261031\paired_resident_source_dev`，实查 HEAD `78b92f2b2b2c67d3650c744204838f4a5ad76e7a`，15 个 tracked files；审查前后 `git status --short` 为空。
- F：`D:\VLA_QWEN\RevTrace\experiments\dsn_native_resilience_20261030\source_v2`，实查 HEAD `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`；审查后 `git status --short` 为空。
- 环境：`E:\Anaconda\python.exe`，Python 3.13.5，Windows 11 build 26200。不是冻结 Linux GPU 环境，也不能代替其环境/资产/READY 检查。
- 实读 E 的 `resident_supervisor.py`、`resident_analysis.py`、`endpoints.py`、`audit_results.py`、`freeze_plans.py`、`common.py`、两个 campaign、entry、observer 与 CPU tests；沿 F 的 Owner/worker/Consumer/storage/policy/inbound/transport 核查委托边界，并核对 timing fixture 的 observer 调用方。
- E 的 `python -B -m unittest -v test_controls`：15/15 通过。
- F 的 `python -B -m unittest -q test_resilience_inbound test_resilience_policy test_resilience_consumer test_resilience_channel_close`：61/61 通过。首次使用默认 sandbox TEMP 时触发临时目录 `PermissionError`；把 `TEMP/TMP` 指向 workspace 内的独立 scratch 后复跑全通过。这是环境路径问题，不是 Consumer 协议失败。
- 独立 cleanup 分支反例：`RESIDENT_CLEANUP_COUNTEREXAMPLE_v1.py`，无真实子进程、无 Torch/CUDA/模型；输出中 `registered_dead_owner_group_cleanup_calls=0`，而失败原因是 `Owner failed before initial neural readiness`。
- 只有本报告、旁边的 CPU 反例脚本及独立 scratch 被新增；没有修改 E/F 的执行源码、CURRENT、root Git 或旧来源。

## 发现 1：已死亡 Owner 会跳过仍存活进程组的清理（P1，外层 harness）

位置：E/`resident_supervisor.py:201-205`，尤其是第 203 行的 `if owner is not None and owner.is_alive():`。

触发路径：Owner 已经 `setsid()` 并完成 `owner_group_started` 注册、已经启动一个或两个模型 worker，但在初始 `owner_ready` 之前被 OS fail-stop/OOM 杀死。主循环在第 137-139 行识别到退出；因为 Consumer 尚未建立，直接抛出异常。`finally` 看到 Owner leader 已死，跳过 `kill_owner_group`。POSIX leader 死亡不会自动杀死同进程组的模型子进程，因此这些子进程仍可能执行或持有 CUDA。异常分支写 FAIL gate 本身不会弥补物理清理。

可控反例：脚本将 Owner 替换为 `pid=24680 / exitcode=-9 / is_alive=False` 的 CPU 对象，只往 inbox 放入合法 group 注册事件；把 `kill_owner_group` 换成计数 mock。主循环确实走到上述真实异常分支，但 cleanup 调用数为 0。这证明的是控制流缺陷；没有把 mock 当成真实 OS/GPU 泄漏观测。

影响边界：成功运行的 C/U、请求时钟和 Consumer EOS 结果不因此自动失效。`run_resident_campaign.py:40-43` 的外层 `stop_owned_processes` 能在标准 campaign 异常时提供第二层 group kill；直接 `run_buffer_fixture.py` 调用只在 finally 关闭 controller，没有这个外层兜底，因此共享 `run_resident` 的 cleanup 合同仍然不成立。

最小修复（只改新版本 E）：

1. 异常退出时，只要 group 已经注册，就调用 `kill_owner_group(owner, True)`，不依赖 leader 的 `is_alive()`；该 helper 已经扫描整个 pgid 并等待 executing members/CUDA 全部释放。成功终止路径可保留现有正常 drain，避免不必要的额外采样开销。
2. 不要把 group/CUDA 释放确认失败吞成仅 `owner.kill(); owner.join()`。可以尝试最后的 leader kill，但要记录/传播 cleanup failure，并阻止后续 GPU cell 复用窗口。
3. 对 registration 尚未被 Supervisor 消费的异常，只有在验证已记录 PID/start_ticks 与实际 pgid 后才允许 group kill；仅杀 leader 不能宣称完成 group cleanup。
4. 加入两个 CPU 回归控制：已注册且 leader 已死时仍调用 group cleanup；group cleanup 抛错时不得写出或推导 `confirmed physical release`。随后在 Linux 用短寿命独立 process group 做真实 OS 控制；不需要启动模型即可验证孤儿进程被清除。

必须给修复后的 E 新 commit/完整 manifest/bundle；不能把 78b92f 的 manifest/identity 贴到修复源码上。

## 正常路径核查

| 合同 | 核查证据与结论 |
|---|---|
| 四个独立预注册 EOS 请求 | E/`freeze_plans.py:7,32-39` 固定四个原始 source，warmup 加四源；原始 model_sources 顺序实查 warmup 在首位。每个 source 保留自己的原始 input hash、frames、reference 与 genesis，没有把上一请求输出作为下一请求初态。E/`resident_supervisor.py:57` 拒绝重复 request_order 或漏源。 |
| 下一请求只能在真实 certified Consumer EOS 之后 | E/`resident_supervisor.py:79-85` 只接受 `consumer.apply/replay_fact` 返回的 applied row，以对应 source 的 `certified_frontier==frames` 完成，然后即时 admit；不是 owner_finished、provisional visible 或录制 runtime 触发。F/`resilience_consumer.py:26-47,57-80` 的 certified progress 来自校验后的 durable original fact。 |
| 每请求原始时钟持续存在 | E/`resident_supervisor.py:74-77,88-102` 原点只在 admit 时赋值，recovery 不改 origins/accepted；每个 offer 为本请求 origin + F/16000，尾部短 EOS 原样接受。E/`resident_analysis.py:8-27` 对完整 ledger、每个 ingress frontier、offer 与 Consumer witness 重算；E/`endpoints.py:19-26` 保留所有 500 ms/EOS 分母。 |
| 模型驻留与物理作业归属 | F/`resilience_owner.py:161-172` 只有 ready 且 busy 为空的物理 slot 可派发；early ASR 不清 busy，terminal 必须绑定同 job；第 51-66 行保持这一区别。F/`resilience_inbound.py:117-167` 绑定 physical slot/incarnation、Owner job namespace、source 和 session epoch。死亡替换必须先 stop/join、drain 原 channel、CUDA release，再提升 incarnation（F/`resilience_owner.py:73-83`）。正常 resident campaign 还检查恰好两个初始 worker、无替换和 dispatch PID 连续（E/`run_resident_campaign.py:33-38`）。 |
| full C/U 与 source marker 映射 | 所有实际派发为 full；F/`candidate_bridge.py:20-37` 包装原始 full call，F/`native_bridge.py:151-179` restore 完整 start、运行原 infer、CUDA synchronize、导出完整 end/IDs/C。E/`audit_results.py:29-39` 对每个原始 frontier 检查完整 start/end、returned token IDs 和 selected correction；E/`common.py:52-56` 只改 `contract.stage_execution.source_commit` 这一静态元数据，其他字段不被投影掉。 |
| 来源与环境 gate | E/`common.py:28-42` 验证独立 checkout、完整可解析 HEAD、clean、完整 tracked manifest 和每个文件字节；resident 的 harness 与额外依赖在 E/`resident_supervisor.py:50-58` 再校验。NN entry 在 `resident_entry.py:5-8` 验证 F 后才导入 Owner。campaign 的 `validate_plan` 在 GPU launch 前核对 frozen config hashes、引用/环境/资产 hashes、actual interpreter/packages，worker READY 后核对实际参数数量/dtypes、warmup/reset、board 和实际 allocator（`run_paired_campaign.py:33-84`）。 |
| 成功退出的物理 drain | F/`resilience_owner.py:158-189` 先 canonical 全完成、busy 全空，再 stop/join 两个 worker、确认 CUDA release、排空 channel tail，最后 owner_finished。E/`resident_supervisor.py:169-180` join Owner 且要求 exitcode 0；external observer 再给独立 PID/CUDA 空窗口上界。以上不修复发现 1 的异常路径。 |
| fixture observer API | E/`resident_supervisor.py:126-130,193,211` 顺序为 start → 循环 poll → Owner 完成后 finish → finally close；finish 位于独立 analysis 之前。fixture 的 controller 可读取已经 flush 的 dispatch/results/policy/publication 文件，在 frozen barrier 上触发真实 worker fail-stop；失败通过 raise 终止共享服务。未发现 hook 顺序阻止该 fixture 的具体缺陷。 |

## 测试覆盖缺口，不计作额外运行时 bug

1. E 的 15 个 tests 没有实际执行 `run_resident` 的启动、recovery/finally 或 observer 生命周期；所以全绿不能覆盖发现 1。应补上述 cleanup 控制与最小 observer 顺序/异常测试。
2. `selected_trace` 的定位是完整 state/C/IDs 的 reference audit；它没有独立重演 dispatch 的 Owner/session/incarnation 关系（E/`audit_results.py:15-19` 只校验部分 owned-job 字段）。实际运行时这些绑定由 F 的 inbound/policy/storage 控制维持，相关 61 个 CPU 控制通过。不能把这个 reference PASS 单独表述为完整物理 trace refinement 的独立证明；如需要该级证据，应使用现有 diagnostic/refinement 审计或另加绑定反例，不能从当前审计结果扩大结论。
3. 本次没有运行 Linux group kill、真实 nvidia-smi/NVML、真实 CUDA 或实际四请求 resident sequence。CPU 测试及静态通过只能支持 launch 前代码检查，不能充当这些实测结果。

审查决定：先修复并重新冻结外层异常 cleanup，再进入 Linux/GPU launch；不需要更换四个源、插入人为 gap、调整阈值、修改 NN4f、改 C/U 或重写既有负面结果。

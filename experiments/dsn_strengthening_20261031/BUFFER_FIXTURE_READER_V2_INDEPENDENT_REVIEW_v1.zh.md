# Buffer fixture reader v2 独立复核

日期：2026-10-31。结论：**NO BLOCKER，可对已静止的原四格证据执行独立 zero-NN posthoc reaudit。** 这不是原 CLI/watchdog/compound FAIL 的撤销，也不是新 NN 结果。审查仅本地只读及 4 个无磁盘写入的内存 receipt 控制；0 NN、0 CUDA、0 signal、0 remote、0 CURRENT/Git 写操作。仅把本报告新增于 E 父目录。

## 身份和改动面

- v2 HEAD：`b8670073141a94a550abe5113222a508b63b5624`，当前 checkout clean。
- manifest：`buffer_fixture_packages_v2/BUFFER_FIXTURE_SOURCE_v2.json`，SHA256 `bd5160ac716084beeaf3280a958b1eb0320e2d970a9253dc2857bfb4f34c9e74`，13 文件全部实际字节匹配。
- 原 v1：`4eb03d6f4f9a918cce693c979e9cfa07e3d6bb28`，实际 12 文件也全部匹配原 manifest。
- 两版间仅 `audit_buffer_witness.py`、`test_buffer_fixture.py`、`README.md` 改变，新增 `reaudit_buffer_witness.py`。其余 9 项均逐字节一致：`.gitignore`、`buffer_fixture.py`、`buffer_controller.py`、`build_buffer_plan.py`、`cpu_spawn_probe.py`、`fixture_paths.py`、`fixture_watchdog.py`、`run_buffer_fixture.py`、`run_development_cpu.py`。

## receipt 分类与严格性

`audit_buffer_witness.py:35-72` 将 `asr_early/completed/abandoned` 绑定到原始 registered UID，并要求 receipt 的 physical slot/incarnation 与原 job 匹配，source 与 dispatch epoch 匹配。缺 UID 的 completed 直接失败，不会当成无关事件跳过。`ready/drained/failed` 则必须没有 job UID，并绑定原 launch 的 slot/incarnation/PID，key 为该物理身份加 kind；同一物理身份的矛盾控制事件仍失败。重复判断使用原 `semantic_fingerprint`，仅排除原定义的 transport clock/channel 注记，不忽略 record/state/contract。

独立实际执行以下 4 个纯内存控制，全部通过；未调用测试 setup/teardown，未创建 scratch 或启动进程：

1. initial 双 READY、replacement READY 与两个实际 incarnation 的 drained 同时保留；owned completed 独立索引。
2. completed 缺真 UID 必须拒绝。
3. 同 UID completed 的 end-state 矛盾必须拒绝。
4. 同 physical control 的 contract 矛盾或 foreign PID 必须拒绝。

先前审查的 release-child 交叉绑定在 4eb 中已经修复，本版保持不变：audit 以原 dispatch 中的 cjob、原 launch 和 child marker 调用 `validate_release()`；controller 要求 release 完整对象与这组可信对象相同，再校验原 fence。

## 原配置与原始证据绑定

本地原 plan SHA256 为 `c0258c50088c1cccf8f47de782fdda7b9c69d2a7e393a7e2720779df6d86552d`，与新冻结 analysis config 一致。逐一校验四个原冻结 config，SHA 均匹配 plan，均以 LF 结尾，原 `expect_match` 均与 plan 相同。

`reaudit_buffer_witness.py:27-42` 的处理正确区分两个字节文件：原冻结 config 必须匹配 plan 的原 SHA；actual raw `CONFIG.json` 必须匹配原 `BUFFER_FIXTURE_RUN_RECORD.json` 中记录的 SHA；二者还要完整 canonical JSON 对象相等。原 Supervisor 省略末 LF 的差别由两个独立字节 hash 覆盖，不能靠重写 raw config 和 hash echo 来改变实际配置。原 ENVIRONMENT 也必须匹配原 run record。它同时限定原执行 code commit 为 4eb，并核对完整 execution dependencies。

`run():62-85` 验证原 plan/hash、四格完整数量、NN commit、原 fixture manifest/hash，检查 timing/controller/paths/watchdog 等保护文件的 manifest 行相等，并拒绝 raw/watchdog symlink 与新输出目录重叠。四格正负决定仍由原 spec、全状态 SHA 与完整状态相等决定，且必须等于原 plan 的 `expect_match`；没有调整边界或 historical hash。

`run():97-130` 在每格 audit 前后，对该格 raw 与 watchdog 树全部常规文件记录相对路径、长度和 SHA256。树中 symlink 被拒绝，任何增删/改字节都会使该格 FAIL。新结果只用 `xb` 写到 fresh analysis 目录；`audit()` 是无旧目录写入的函数调用，不会调用其覆盖旧 gate 的 CLI main。原 resident/buffer/watchdog gate 的 body/hash 保存在新结果里，原 v1 compound gate 当前本地副本仍为 `NO_GO_COMPLETE_BUFFER4_NEGATIVES_PRESERVED`。

## 实际验证范围与小注

本地只有 bounded 下载副本，未含全部原 raw 文件；依照任务要求没有访问远端，因此没有在本次审查中实际重算远端四格 raw/watchdog 的全树 SHA，也没有实际执行正式 reaudit。前后完整字节不变应由新 analysis 结果本身交付验证。报告中的“代码会检查”与“本地已实际校验”已分别列明，不把前者写成真实运行 PASS。

一个不阻塞当前静止证据复审的小问题：`reaudit_buffer_witness.py:130` 的 `original_execution_gates_unchanged=True` 是固定值；若并发外部写入导致某格 before/after 不同，状态会正确 FAIL、`all_complete_raw_and_watchdog_bytes_unchanged=False`，但这个单独布尔字段仍为 true。当前流程不写旧文件、只复审静止 raw，因此不影响本次 PASS 判定。后续 reader 维护可令其由实际原 gate 前后 hash 推导，避免失败输出中的元数据歧义；无需为了这一点修改已冻结 v2 或重跑 NN。

# 旧 v8 全 69 调用保真检查：本地已冻结，等待窗口

**后续执行已完成**：实际 10:24:47 UTC 全 69 PASS，CPU/IO 释放。结果见 `OLD_FIDELITY_RESULTS_v1.zh.md`；以下保留原准备状态和冻结命令，不表示当前仍在等待。

本文件不代表分析已运行。新的 99e83a4 神经 69 输入门正在独占远端；此准备阶段未做远端读取、stage 或 CPU 分析。

- 独立实际 analysis source：`analysis_old_fidelity_source_v1`，clean commit `64ba03e56aaee752bd962f123a125750e34ad71e`，5 个完整 tracked 文件。
- plain snapshot：`analysis_old_fidelity_snapshot_v1`；bundle：`packages/OLD_FIDELITY_SOURCE_v1.bundle`，SHA `527445a751a911809d2cef8fe2b75693dc716b440f5d2b56ef95e132cebea34f`。
- 完整 source manifest：`packages/OLD_FIDELITY_SOURCE_v1.json`，SHA `0556f18f3bef6deae7e1e982929eba189556a4725c263dcb9b88ea64ec3bbad1`。
- 冻结实际配置：`OLD_FIDELITY_PLAN_v1_FROZEN.json`，SHA `dc47323bd2db4103f99ea0432bec2b5e92c072dc58fe7addd43c469549ea3d2f`；绑定新的 `99e83a466fee7f1d16830b640cc99e0040d2f147`/`equivalence_v2`，不会读取失败的 c7 不完整输出当作 69 对。
- `OLD_FIDELITY_LOCAL_PREFLIGHT_v1.json`：显式 source/manifest SOURCE_IDENTITY_PASS，5/5 字节通过。实际 commit 已经从 bundle 导入当前证据仓库 `refs/revtrace/stage-old-task-fidelity-64ba03e`，没有改变 legacy HEAD 或 CURRENT。

比较的是旧 v8 `formal/A,B/sequential/r0` 两格的全部实际 canonical histories、WAL selected C 和 actual jobs，对新神经 DETAILS 的 original-full 结果。旧 prior audit 的每行完整 state hash 是独立锚点；旧 A history 的原 raw SHA 也严格校验。每个新状态只在要求 `stage_execution` 整项与预期值全等后，移除 `contract.stage_execution`。source_sha、模型/配置、audio、tokens、context、cursor、Z/P/文字及所有其它状态字段不能省略。全 C 对象（包括 prompt/候选顺序/前缀/空结果）、returned IDs 和 appended text 独立比较。

新旧未投影 hash 各自核对其原完整对象；显式报告二者是否不同，绝不声称因合同标签不同的 raw cut hash 原本相等。normalized cut hash 必须等于旧 audit 所记录的原 hash。69 个完整调用起点也逐个比较，而非只比较最终输出。

17 项有意义的本地开发 CPU 控件通过，包含被合法重算 hash 掩盖的状态变化、未经允许的 contract 字段、C prompt/候选顺序变化、returned IDs 不同、缺失/重复调用、input/end hash 绑定错误和 None 路径。正式执行会在该 clean source 上重新运行全部 17 项且禁止 skip，再读取真实保存结果。开发控件不是实际神经保真结果。

获得 root/SC 明确释放之后，唯一待执行命令为：

```powershell
python -B experiments/dsn_streamcorrect_stage_handoff_20261029/ops/run_old_fidelity_v1.py --execute
```

该 wrapper 首先要求 `equivalence_v2` 完整 69 输入 PASS、source commit 相符、GPU compute 列表为空；只执行标准库 CPU，不导入神经模型。预计 CPU/IO 本体数秒，连同 SSH、源码 stage 和 bounded 收集约 10–30 秒。它保留失败、记录 config/environment/run/source/input hashes/CPU logs/69 comparisons/summary/gate，取回 bounded 输出并逐文件核实远端 SHA。执行结果固定到 8 TB 盘 `results/revtrace/dsn_streamcorrect_stage_handoff_20261029/old_native69_task_fidelity_v1`。完成 CPU 和全部取回后，立即报告 gate 路径/SHA并释放窗口。

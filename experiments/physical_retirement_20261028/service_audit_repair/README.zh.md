# v1 F2 原始证据的独立审计解释修复

本目录保存已有原始运行的只读复算证据，没有改写其执行源码、原始结果或原失败 gate。

- 原始运行：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028/service_pilot_v1/row_complete-F2-r0`
- 实际执行提交：`c9c2469ba2ca38db5b7d9a3f1a7ea35052e57d68`，runner returncode 为 0。
- 原冻结 fixture SHA256：`88760ed3481cbd71c874ac7a88742c6600c2816ecb1c697dfae1479b64dbc0f1`，与运行配置记录一致。
- 本次独立审计组件源码 SHA256：`a8df7aecf1cb8e8444501b4e1e69f00bd3a5d277e38647d05c45658285674118`。源码快照为 `x_service_metrics_reaudit_snapshot.py`。
- 审计组件运行时通过 stdin 在远端内存中执行；入口是 `audit_episode(E, manifest)`，不导入或运行 GPU 推理，不在远端写入文件。
- 这次 PASS 只表示该独立组件完成记录级 input/WAL/row/actual-Consumer 重计数。完整 `retirement_audit` 的新源码身份审计由主线程另行运行并另存，不能将本目录改称原运行的原始 gate。

## 错误原因

fixture 的明确动作以及实际 F2 hook 均使用 `donors[fault_plan[key] % len(donors)]`。故障计划保留逻辑 donor 索引；12 个 donor 下，逻辑索引 12、14 实际选择 donor 0、2。

旧独立审计错误要求逻辑索引小于 donor 数量，并在另一处直接用逻辑索引读取 donor，导致有效实际运行被拒绝。修复仅恢复冻结 fixture 已有的 modulo 语义，不改变 fixture、实际输入或输出。审计仍要求逻辑索引为非负整数、source/window/chunk/原逻辑 donor 身份完全匹配，以及实际 job override、真实执行上下文和 donor token 逐项相同。原始 D1、音频和输入义务检查保持。

八个实际 F2 job 的输入检查全部通过，包含逻辑 12→实际 0、逻辑 14→实际 2；具体逐项检查见 `readonly_f2_input_checks_20261028.json`。

## 复算数据与边界

`readonly_x_service_metrics_20261028.json` 是完整只读复算 stdout，摘要为：16 个来源、135 个 offered frontiers、265 个完整行、8 个真实输入替换、0 个未授权 admission、0 个 stale publication、0 个根不兼容实际视图；最终认证音频覆盖率 1.0。

WER 为 14/687 = 2.0378457%；all-offered goodput 为 10.7033683；display P99 与 commit-view P99 均为 3.6705648 秒。因此原始双期限 P99 gate 仍为 false，审计修复没有把性能失败改成通过。两板累计 GPU 能量为 8627.5574 J。

修复这项纯审计解释错误无需重新执行旧 GPU 运行。新的 H3 实验仍须使用新冻结执行提交和新输出目录。

## 文件校验

- `readonly_x_service_metrics_20261028.json`: `965084e6f3000b313a3cbb0899fde94b51e9ec576bd20abbff026a8adc15ac67`
- `readonly_f2_input_checks_20261028.json`: `88ddb22cbe7011798712068952864bc8fbb7bc88184fc5a37c615cd0306dfbbb`
- `x_service_metrics_reaudit_snapshot.py`: `a8df7aecf1cb8e8444501b4e1e69f00bd3a5d277e38647d05c45658285674118`

`read_only_reaudit_program_20261028.py` 保存传给远端 Python stdin 的完整只读程序，其中嵌入上述审计源码。

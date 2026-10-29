# R × K 小型联合实验已准备

本分支没有启动 GPU。root 已确认在 36 格服务稳定性矩阵结束后，串行执行本实验 24 格。

- `PLAN_v1.json` SHA256：`d5da167c84b185dc38c2f5db345b7ba9bd0b501b087fcb06216e8f449a7a7f8e`。
- 实际神经执行源码仍为 frozen-v3 `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`，manifest SHA256 `19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625`；未改 runtime。
- 独立 CPU 分析源码：`analysis_source_v1/`，干净提交 `aa4e01af1a9c49df435fdefd479b9ed50cc45fbe`，6 files。
- `ANALYSIS_SOURCE_v1.json` SHA256：`b7f31431d15c30534c342aca5bbae6315bd4e58ac0e8ac1d9069c63ee0c92c8a`。
- 完整 `ANALYSIS_SOURCE_v1.bundle` SHA256：`582afbebaa798cbe5c7d375d730b4a5c77f4c4cc4fd3b0045784eb9ce8798a64`。
- 5 个 adversarial CPU tests 通过；计划中的四臂确实共享执行器，未来才发布/错误 actual prompt 不能充当祖先兼容证据。

`DEVELOPMENT_PRESSURE_v3.json` 由上述干净源码实际重算，保存全部 8 个原始输入文件的 SHA256。旧四格 pilot 中，真实 decode 与 Canonical 安装重叠且 targetF 仍未覆盖的非 F2 行，分别有 7/15/9/12 个精确兼容见证，最长实际模型阶段到 terminal 为 0.7756/1.1881/0.7612/0.7762 秒。它证明开发素材含合法未覆盖计算压力，不证明新 24 格的所有时序条件都激发保留机会。

推荐 staging：

```text
P = /media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_physical_retirement_20261028
O = /media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028
PLAN = P/DSN_JOINT_PLAN_v1_FROZEN.json
ANALYSIS = P/dsn_joint_analysis_source_v1
ANALYSIS_MANIFEST = P/DSN_JOINT_ANALYSIS_SOURCE_v1.json
```

导入完整 analysis bundle 后，在远端 clean clone，逐项验证完整文件 manifest；实际 runtime 另行验证 frozen-v3 的完整 manifest。计划 argv 已完整冻结为24格命令，标准 `source_v3/retirement_campaign.py` 可执行；使用 `--out O/dsn_joint_controller_v1`，不能覆盖旧输出。

完成24格且 GPU 空闲后运行：

```text
PYTHON -B ANALYSIS/joint_recount.py --source-manifest ANALYSIS_MANIFEST --plan PLAN --out O/dsn_joint_analysis_v1
```

该分析不导入生产策略，不执行新推理。输出 `RUNS.json`、`FACTORIAL_EFFECTS.json`、`MATCHED_ROWS.json`、`ANALYSIS_RECORD.json`、`SUMMARY.json`、`GATE.json`。实际批次、同行和输入匹配率均单列；R 导致的不同合法后继输入不会被强制当成同批对照。每个取消链保留请求、安全点 ACK、实际 drain、下一次 dispatch 与下一批 Owner outcomes。

三次时序重复报告每次结果与范围。交互接近零、收益可分离或某点未激发机会，都是完整结果；无需新取消原因或寻找更好看的点。

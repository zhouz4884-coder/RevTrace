# 原任务保真：旧 v8 与新阶段版本全 69 调用一致

实际 gate：`PASS_ALL_69_OLD_NATIVE_TASK_RESULTS_AFTER_EXACT_DECLARED_STAGE_TAG_PROJECTION`。2026-10-29 10:24:47 UTC 启动的标准库 CPU 重计在 0.639 s 完成；连同 stage/有界收集本地调用约 2.8 s，没有推理、模型加载或 GPU 使用。完成后已向 root 和 SC 释放 CPU/IO 窗口。

| 核对项 | 实际结果 |
|---|---:|
| 原来源/原完整调用 | 4 / 69 |
| 完整调用起点一致 | 69/69 |
| 完整调用终点一致 | 69/69 |
| 完整 selected C 对象一致 | 69/69 |
| returned IDs、appended text 一致 | 各 69/69 |
| 其中 non-None C / None C | 64 / 5 |
| frozen comparator CPU 控件 | 17/17 PASS，无 skip |
| 原始新旧 cut hash 直接相同 | **0/69** |

逐来源为 `BAC009S0764W0209` 17、`BAC009S0765W0203` 17、`BAC009S0767W0329` 18、`BAC009S0768W0136` 17 个调用；没有筛选有 packet 或有纠错的调用。

方法是以原 v8 formal/A、B/sequential/r0 的 histories、canonical WAL 和 actual jobs 交叉校对，再比较新 `equivalence_v2` 保存的 original-full 调用。旧 prior-audit 的每行完整状态 hash 为独立锚点。对新起点/终点只允许删除值完全符合预期的 `contract.stage_execution`；其余所有状态字段、source/audio、tokens、context/cursor、模型/配置身份、文字不变。新旧各自原 hash 与原对象独立检查，normalized 新 hash 才等于旧原 hash。因此这里的“状态一致”明确是这一个声明标签投影后的一致，不能把 0/69 raw hash 相同写成 raw hash 全等。

新神经 69 输入门 SHA `41221280007d94581a640ec329bf5634ccb6012efbc44ab60fca302c51c6849d` 已作为本次 CPU 输入实读并记录。它的 stage C/U、投影等价是另一层控制；本次补上的是“新版本 original-full 没有悄悄换掉旧任务”这一层。两者结合，支持在保持原固定任务行为的条件下研究 protected A 与原 C/U 的组合。此处未计算服务延迟、goodput 或能耗，也未把保真对照当作服务收益。

证据身份：

- 实际 analysis commit：`64ba03e56aaee752bd962f123a125750e34ad71e`；新神经 runtime：`99e83a466fee7f1d16830b640cc99e0040d2f147`。
- 冻结 plan SHA：`dc47323bd2db4103f99ea0432bec2b5e92c072dc58fe7addd43c469549ea3d2f`；完整 source manifest SHA：`0556f18f3bef6deae7e1e982929eba189556a4725c263dcb9b88ea64ec3bbad1`。
- 实际 gate：8 TB 盘 `results/revtrace/dsn_streamcorrect_stage_handoff_20261029/old_native69_task_fidelity_v1/GATE.json`，SHA `79f9355a41f42660fb16c3f002b3052551a547dbe6dafd89cdb0a0205c8d1411`。
- 本地 `old_native69_task_fidelity_RESULTS_v1`：11 个有界文件，127,609 B，逐文件与远端 SHA-256 相同；`INPUT_MANIFEST.json` 记录全部 15 个真实输入及各自字节 SHA。
- `COMPARISONS.json` 含所有 69 行的原/new/raw/normalized hash、完整 C 值、returned IDs/text；不是只保存 PASS 布尔。
- 完整 source、plain snapshot、bundle、freeze record、local preflight、config/environment/run record、正式 CPU 日志、summary/gate 均保留；旧 raw 留在原 8 TB 路径。

可用于正文的英文句子：

> We additionally checked task fidelity against the original native experiment: all 69 calls across the four fixed sources preserved the complete input and output feedback states, selector results, returned token IDs, and appended text, after removing only the newly declared stage-execution contract tag. The original and new unprojected state hashes remain distinct because they bind different execution contracts.

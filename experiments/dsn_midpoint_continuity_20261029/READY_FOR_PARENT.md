# 唯一12会话开发中点：本地冻结就绪，未启动

当前只完成本地冻结方案、完整analysis源码和17项CPU控制；**没有远端staging、环境安装、模型调用或GPU启动**。没有修改CURRENT或f0运行源。执行必须等根任务分配。

冻结计划`PLAN_v1.json`，SHA256 **fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84**。真实神经源码仍为 **f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf**；完整manifest SHA256 **19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625**。

原16开发manifest前12来源，原始顺序；前8与既有c8逐项核对一致，12个source/path/audio hash均无重复；offered **185.300秒、101个原始前沿/格**。完整选取身份与hash在`SOURCE_SELECTION_v1.json`。这是开发点探索，不新增独立speaker、不宣称纯并发capacity curve。

只做R/S四臂×3fresh=12格，rho1、sid×0.25s错峰、row_complete、原D2/C8、完整EOS、质量、能耗均不变；没有fixture/取消/模型/机制新增。固定seed **2026102905** 随机三块顺序和三个不同Latin rotations；每臂只覆盖四位置中的三个，称近似平衡，不称完全counterbalance。

强见证冻结为：Joint和R-only各3/3原整场P99 D2/C8通过；R-only至少2/3重复出现≥1个原dual-credited完整2s非EOS区间的实际兼容Canonical撤回；Joint三次所有compatible及时损失窗口为0。**精确定义是`audio_seconds==2.0`且`frontier<该source总samples`，整2s的最后EOS段也不计强见证。** 它不从原主指标或secondary中删除任何EOS。首次信用无需Joint赢；原D2读点缺失、单根面积和必要不兼容撤回另列。缺少任何强条件都是完整STOP，不试10/11、不加重复追正结果。

analysis独立干净提交 **fb8a429d95ab682002bc39aedca8bcbec8942b67**，15文件；完整manifest **bfc3d1a3fe0d819c93e3cda4a4959491efb520ba06cf8b304aec47223a5388c0**，完整bundle已导入root的`codex/midpoint-analysis-v1`。五个既有core recounter逐字节复用；timely `analyze_cell`逐字节复用，只有测试import namespace修补；新wrapper负责12格完整覆盖、非EOS强见证和STOP决定，见`analysis_source_v1/UPSTREAM.json`。17项CPU控制已通过，逐项原始输出/配置/环境/运行记录/gate在`CPU_TESTS_v1/`；这些不是神经或服务证据。

## 执行顺序与分配门

固定顺序：**已有R×K24+其CPU分析 → native既定scope（2witness，只有其gate通过才12formal）+其分析 → 本12点**。若原生曝出更有意义机会，由根任务重新分配候选profiling和本点时序；不得根据本点结果换点。不能为插队而中断冻结native scope。

`ALLOCATION_TEMPLATE.json`刻意为`root_allocated:false`且留实际路径/hash占位符，不能直接启动。待上述scope实际结束后，根任务把四类实际结果/decision证据的路径、SHA和必须匹配字段写为远端`ALLOCATION_v1.json`，并注明native是2witness失败关闭还是2+12全部完成。还需当前no-argument source preflight的真实f0 receipt。这个分配文件只管资源顺序，不修改冻结实验参数。

## 待分配后可执行的命令

1. 在本地根目录重新运行no-argument repository preflight，确保CURRENT指向这次真实执行的f0源与完整manifest；不重标native或旧运行。如果CURRENT在原生期间变动，先由根任务按本地source identity流程切回f0，再生成新receipt。`stage_remote_v1.py`是有界准备脚本，只有根分配后运行；会拒绝正在计时的GPU、上传计划/完整bundle并核对字节，不启动GPU。
2. `P=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_midpoint_continuity_20261029`，待实际分配文件就绪后，使用8TB现有环境执行`P/analysis_source_v1/launch_midpoint.py --allocation P/ALLOCATION_v1.json`。该launcher再次验证前置scope证据、分析源全字节、f0源242文件、所有输出路径未使用和GPU空闲；不import模型。实际campaign在第一模型调用前记录原始config/env/run record。
3. controller输出在`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028/dsn_midpoint_controller_v1`，句柄在`P/GPU_HANDLE_v1.json`，包含PID/startticks/command SHA。原始单格在同结果盘`dsn_midpoint_v1/`。
4. 全12结束后且没有计时GPU，再用同一Python调用`P/analysis_source_v1/midpoint_analysis.py --plan P/PLAN_v1_FROZEN.json --plan-sha256 fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84 --source-manifest P/ANALYSIS_SOURCE_v1.json --output /media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028/dsn_midpoint_analysis_v1`。

CPU analysis会先执行四项完整core recount，再计算所有四臂的及时连续性和强见证。`GATE.json`表示完整分析可用，`STRONG_WITNESS_DECISION.json`单独表达是否观察到强见证；负效应不伪装为执行失败。完整history不同会阻止same-task/强主张，原始性能仍保留。模型/数据/环境/缓存/原始log始终留8TB盘，只同步有界审计证据。

本目录暂不画新结果图。数据完成后若合并图，既有三个36格工作点和新12点均保留各3次真实重复，即使中点为负也不删除；图题明确不同来源组合的开发工作负载，不暗示纯并发容量曲线。

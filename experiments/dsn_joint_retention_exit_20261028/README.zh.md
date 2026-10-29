# 计算保留 R × 覆盖退出 K：完整 24 格

**已完成 24/24 双 GPU 执行、独立重计、逐行实际输入与 Consumer 补充审计、有界逐文件 SHA 取回及论文图。**

结果与论文取舍见 [RESULTS_FINDINGS.zh.md](RESULTS_FINDINGS.zh.md)。同步 K 的服务信用有重复收益，且存在严格同输入/同批/完整输出→实际 Consumer 的链条；错峰端点及 R×K 交互符号混合。当前将 K 定位为执行支撑，不主张稳定正交互或新增复杂取消算法。

主要入口：

- `PLAN_v1.json`、`PROTOCOL.zh.md`：事前冻结 24 格设计；实际执行源始终为 f0a8e7bc。
- `RESULTS_v1/analysis/`：最终 v2 主重计；保留原失败的 `preserved_analysis_failure_v1/`。
- `RESULTS_v1/detail/`：实际 tensor/prompt 存在性、完整 fixture target/donor 身份、Owner→实际 Consumer 对应、合法跨 Canonical 计算与退出后继。
- `RESULTS_v1/cells/`：24 格冻结配置、环境、命令、gate 和完整 all-offered/frontier/batch 审计；大原始日志留指定 8 TB 盘。
- `RESULTS_v1/DOWNLOAD_VERIFICATION.json`：317 个远端文件、8,595,792 字节，全部 SHA 相同。
- `DIAGNOSTICS_v1/`：全部 12 个 K0/K1 的 gained/lost 前沿；同步六批共 96 行按真实首次 Consumer D/C 分类，区分 obsolete 与 deadline miss。
- `FIGURES_v2/`：全部 24 格原始重复的 7.15in PDF/SVG/PNG，最小 8pt、Type3=0；原始端点及效应 JSON/CSV。
- `ANALYSIS_SOURCE_v2`、`DETAIL_SOURCE_v2`、`FIGURE_SOURCE_v3`、`DIAGNOSTIC_SOURCE_v1`：各有完整 manifest、干净 commit 与可解析 bundle。

三次时序重复与两个相位不是新来源确认；固定 F2 fixture 不是自然故障发生率；未改 prompt 的正常跨根计算不能与 F2 无用长尾合并。全部原 D2/C8、offered 分母、质量和能耗均保留。

当前图四臂使用明确 R0K0/R0K1/R1K0/R1K1 标签，S 在全部臂开启；`FIGURES_v1` 保留，v2 只改 legend/caption，八个原始数据表逐字节不变，详见 `FIGURE_LABEL_REVISION_v1.json`。

质量侧补强已完成：`same_F_support_v1/RESULTS_FINDINGS.zh.md`。原 first-credit 不变；固定六同步后继批96/96首次完整内容与未来严格同F Canon原文一致，全部实际无fault override；同时保留整场first-view raw/norm差异。

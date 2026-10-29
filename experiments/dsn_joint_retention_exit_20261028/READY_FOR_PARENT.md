# R × K 24 格已完整交付

当前论文图为 `FIGURES_v2/retention_coverage_exit.pdf`。四臂标签明确为 R0K0、R0K1、R1K0、R1K1；caption 首句为 **S is enabled in all arms.** S 在所有臂始终开启，避免与 R×S 主图中的 Joint 混淆。

- 新图源：`figure_source_v3/`，干净提交 `7c07e20ad504acefd7a98448f7fb5d5eee6e978c`；完整 manifest/bundle 为 `FIGURE_SOURCE_v3.json/.bundle`。
- 原 `FIGURES_v1/` 保留。此次只改 legend/caption；八个数据表逐字节相同，axes 和绘图逻辑不变，见 `FIGURE_LABEL_REVISION_v1.json`。
- 7.15in、最小 8pt、Type3=0；已实际查看完整导出 PNG 和 PDF 渲染整页，`FIGURES_v2/VISUAL_QA_FINAL.json` PASS。
- 实际 24/24 双 GPU 执行、主重计与实际输入/Consumer 补充审计均已结束。原始数据、数字、所有正负结果均未改动。
- 完整结论：`RESULTS_FINDINGS.zh.md`；正文素材：`PAPER_PARAGRAPH.en.md`；全前沿/96 行服务分解：`DIAGNOSTICS_v1/`。
- 历史 pre-run 说明原样保留为 `READY_FOR_PARENT_PREFLIGHT_HISTORICAL_v1.md`。

没有远端读写，没有新推理。K 保持执行支撑定位，不宣称稳定正交互。

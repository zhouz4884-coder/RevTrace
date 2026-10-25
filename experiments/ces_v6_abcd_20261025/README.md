# RevTrace CES V6 A/B/C/D


本轮完整结果从 [RESEARCH_REPORT.zh.md](RESEARCH_REPORT.zh.md) 阅读；机器可读裁定为 [FINAL_DECISIONS.json](FINAL_DECISIONS.json)。研究方案与原始建议分别在PROTOCOL.md和USER_PROTOCOL.txt，不能把建议当结果。

复核顺序：collection/COLLECTION.json → 全分片SHA → unpack_v6.py → LOCAL_BYTES_VERIFIED.json → local_event_review_v6_v2.py → local_review_v2/SUMMARY.json。GPU原始记录仍在8TB路径；压缩分片可按字节恢复全部发布证据，不含模型或音频。runtime、runtime_A、runtime_D及三个.bundle分别绑定各正式版本。

CPU入口为run_focused_cpu.py，明确运行本轮协议用的聚焦测试。冻结目录包含部分历史报告测试，但未附其旧工具脚本；不可把直接pytest所有历史测试的19项收集错误说成通过。见D_WIRING_REPAIR.md与CPU_REGRESSION_D.xml。

不包含论文改写、不声称录用、不声称穷尽topic。所有失败与NO-GO保留。

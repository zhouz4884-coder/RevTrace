# 全16服务终端收集完成

原冻结 bdfa 计划 `cab424783f30ff9b53db8deef5eba482d3b101f15336b65de8b1c7d9ced3679a` 全16格于 2026-10-29 13:32:20 UTC 完成；13:35:20 UTC 观察原 PID1833614/start502958286/cmdfc1828… 已不存在，campaign GATE 为 PASS_ALL_FROZEN_NATIVE_SERVICE_CELLS_AND_COMPLETE_TASK_FIDELITY，16/16且原完整task审计均过。

随后既定收集器再次验证同一 handle 已退出、全16门及实际 GPU empty，再取回 `SERVICE_RESULTS_v1` 的 437 个文件，共29,998,654字节。每个文件均与收集时远端 SHA256 和字节数相同。COLLECTION_MANIFEST SHA `598a30d07422d12f328990a4acd926bda8f91e78a6f3ab5c46c10fc547d15607`，campaign GATE SHA `4e70e2c74c319cafb18bb7b6a964209eddcf62e8ec2c2ef9a9f942054862a152`，campaign SUMMARY SHA `8b96c3fc4f26efc60cd0f6234b6f963ba4e11f9909699dbada9723577e25b729`。

收集 receipt 保留旧兼容 schema：顶层 all_bytes_equal=true、source_commit=bdfa，files含path/remote/bytes/sha256；路径为cell_id/file、campaign/file，另有CPU/file六份前置核验。packet原始payload、模型、数据、环境和未选取raw仍在8TB盘。所有CPU/远端IO均释放。

本收集门还不是本轮严格无字段投影的独立 full-state/start/C/IDs 门，也不是主要效应或文本支持的重计结果。已通知root和SC；实际独立分析由root明确分配给SC的冻结 b473d9d 源完成后再判读方向。

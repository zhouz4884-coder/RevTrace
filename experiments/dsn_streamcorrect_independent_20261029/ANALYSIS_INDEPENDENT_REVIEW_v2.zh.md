# 窄修后二次独立复核

冻结分析源 `b473d9dc47c21d5cc7f88d7871f37497398895fb`（analysis_source_v2）已消除 v1 的 provenance 字典/配置 Path 同名覆盖。实际检查源码及逐文件字节差：除 `analyze_confirmation.py` 的配置路径变量改名、README 和新增 `test_primary_driver.py` 外，其余原文件一致；三个 c128 内容算法文件原字节不变。

新增控件真实调用 main 的配置/provenance读取及第一格 source-object比较，随后在调用真实 fidelity函数的位置用显式 sentinel退出。若原 shadow错误存在，此控件会先 TypeError，无法达到 sentinel。其余无关外部I/O/source/collection门以明示 CPU fixture stub隔离，没有将fixture当科学证据。本地完整23/23项CPU controls独立重跑通过。

v1复核中的统计单位、完整 state/tag/start/C/IDs、实际 model-active计时及内容 actual-G全文语义保持成立。可在完整16格及SHA收集门后冻结机械输入配置并运行；此note不是新16格结果。

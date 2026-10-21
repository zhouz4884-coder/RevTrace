# RevTrace Phase D — certified state-to-display continuity

这是完整研究归档，不是论文正文、匿名镜像或自动GPU任务。协议：`PROTOCOL_USER.md`。先读中文结项报告及Claim–Evidence Matrix，再看数字。

- [完整结项报告](FINAL_RESEARCH_REPORT.zh.md)：方法、结果、负结果、证据层级与停止原因。
- [DSN创新裁定](DSN_NOVELTY_DECISION.zh.md)：哪些能成为主贡献，哪些只是工程修复/适用边界。
- [Claim–Evidence Matrix](CLAIM_EVIDENCE_MATRIX.md)：14项主张的来源、对照、反例、条件与GO/NO-GO。
- [失败与修订历史](FAILURE_AND_REVISION_HISTORY.md)、[指标口径](DATA_DICTIONARY.md)、[证明与假设](PROPERTY_D_PROOF_AND_ASSUMPTIONS.md)。
- `phases/R0`至`R6`：逐阶段冻结设计导航、源码清单、运行矩阵、审计裁定。R3/R4复用同批实验，不重复计数。
- `tables/`、`figures/`：机器可读全结果与只读可视化；不是筛选过的成功样本。
- `EVIDENCE_INDEX.json`：完整大日志位置、逐文件哈希索引、环境、模型/音频身份、源版本和配置导航。

## 最关键的科学结论

在固定canonical内容历史的干预中，认证交付时序能改变可见音频回撤。在匹配机制实验中，状态连续性与消费策略**联合**使用，而不是单纯隐藏输出或只保留私有状态，取得Fine音频回撤67/61/77→0/0/0及配对Display P99中位−43.94%，canonical历史不变。该结论不推广为零文字修订或任意负载零回撤。独立新音频有2s/8s双P99通过点。

最强Standard Safe Async同样实现这些规则并取得相近结果；**不可组合/独占性能主张被否定**。安全字符串后缀拼接NO-GO。合法保留的是通过同F/P、完整因果链及冻结输入验证的**整体未认证**私有假设，不是拼进认证文本的后缀。旧V0/V1 NO-GO、Whisper长时质量与历史内存边界继续保留；没有启动V2或新KV fallback。

## 下载与验证

公开包只含有界证据；模型、音频、环境、大JSONL/WAL留在8TB实验盘。`PUBLIC_BOUNDED_EVIDENCE.tar.gz`保留全部科学结果、冻结配置和原始哈希索引，仅不再分发一个第三方库源代码诊断摘录（原hash仍在索引，诊断见TOKENIZER_WARNING_TRIAGE）。解压到独立`evidence/`目录后，表中`independent/...`、`R0/...`等路径以该目录为根。

`runtime/`为最终实际测量的源码；`frozen_source/`保留分阶段源包；`source_history/`保留实际代码Git对象bundle。旧未运行工具bundle显式标注UNRUN，不冒充实际F2版本。实验源码commit不是本仓库归档commit。

```text
python -B verify_portable.py
```

这仅核对发布字节并运行73项独立可移植CPU测试，不访问SSH、不占GPU、不代表神经效应复现。依赖Python、NumPy、pytest；真实GPU复核另需合法取得相同模型、数据及环境，见VERIFICATION_COMMANDS。完整本地回归395项、另6项对抗测试和真实GPU/WAL/时钟复算是不同证据层。

本轮归档到用户指定的**公开**`zhouz4884-coder/RevTrace`，只追加`experiments/phase_d_20261021/`，不覆盖旧Phase N、工作树或论文。没有上传音频/权重/凭据，没有把公开链接称为匿名链接。大日志的存在、哈希一致或测试通过不能单独推出论文创新性或录用概率。

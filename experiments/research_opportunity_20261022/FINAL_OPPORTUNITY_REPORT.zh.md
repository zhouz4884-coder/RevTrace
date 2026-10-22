# Research Opportunity Audit 结项

## 最终判断

**A：NO-GO，不实现DAG Grafting。B：技术可行且有新增合法复用/关键路径收益，GO进入有限集成提案；不自动进入完整系统或大规模实验，独立算法新颖性尚未确立。**

本轮没有改论文、标题、摘要或基线的有效性条件，没有启动V2或新KV fallback。既有Phase N/D结论全部保留。GPU仅用于门槛通过后的有限原型：22个成功故障单元，另保留1个失败pilot；现已释放。

## A回答了什么

90个冻结真实运行、3,993次连续性检查中，已有Exact-P已覆盖3,715次。148次P不匹配（12个唯一源/前沿/P对）在rollback5及重新编码后均没有新增输入等价根，现存完成后代最大深度1。21个后代batch区间共17.164秒，但现机制之后同区间重算为0，不能把已付工作冒充可节省工作。

Whisper的实际显式prompt路径没有采用假设中的previous-segment截断；实际prompt最长60tokens。30对不同逻辑历史中0对实际decoder前缀相同。2个target与5个future不同输入得到相同Z是**实际双调用的事后收敛**，不是提前可认证的输入等价。没有CPU重解释旧Z来假装新parent生成。详见A_DECISION和原始CSV/负例。

## B回答了什么

现有Queue无法被新Coordinator凭名称重连，WAL也没有未提交Job/Result来源。最小可行方案需要独立Supervisor持有Worker/Queue及immutable dispatch registry；新owner另建IPC连接，只能在恢复的合法父状态/音频/χ与来源均匹配时重新授权。

34项CPU负控通过；22个GPU单元的来源、独立Render、原WAL、真实消费和执行时钟复核通过，180个旧A输入文件哈希及116个冻结runtime源文件复核通过。权重完整哈希在收尾再次匹配上轮冻结值；原Worker在GPU前逐项验证JSON/Tokenizer/Parser/Processor资产，不能把收尾权重校验伪称启动前完整权重校验。

| 场景 | Warm Strict RTO中位 | Conditional Adoption RTO中位 |
|---|---:|---:|
| 运行中 | 1.946s | 1.014s |
| 完成未提交 | 1.238s | 0.272s |
| 非空父、完成未提交 | 1.430s | 0.284s |
| 已持久、未发布 | 0.299s | 0.286s，无收养必要 |

每格2重复，仅限单Authority目标和本地消费端。Cold约17s至Warm约1–2s的主要差异是模型驻留，不能计为收养收益；WAL已提交点Cold也直接重放发布，未强迫模型重载来抬高基线。原CLI约31s首次消费不是恢复语义的必然下界，需要限定实现顺序。

正常成本以真实payload Linux CPU fixture估算：receipt深复制/摘要在同Pipe relay上增量中位约0.246ms，单pending样本约5.7KB JSON。不是完整线上性能或内存上界。GPU能耗逐样本保留，但短窗口覆盖和9个live积分字段异步偏差限制了精确能效结论，最终独立重算/覆盖率在CSV中，不再给节能headline。

## 对研究价值的独立判断

B比A值得继续：它有真实未安装工作可利用，不是只发现字面状态不同；净收益在公平warm基线下依然存在，并且非空父状态确认没有破坏原安全边界。

但B尚不能被当作“已有强DSN新算法”。Supervisor/活任务/结果去重并不新，相关正式工作已有覆盖。当前证明的是**应用特化的安全收养条件和恢复机会**。最有价值的下一步不是扩样刷倍数，而是允许最强普通任务组合实现同样条件，并确认剩余的语义/调度增量是否仍有独立价值。若等价，就将B作为恢复增强，不靠改名制造新贡献。

## 交付入口

- SOURCE_LIFECYCLE_AUDIT：Coordinator/Executor/Worker/WAL/epoch/job/certificate源码边界。
- A_DECISION、B_DECISION：各自GO/NO-GO、真实机会、收益、前提与下一步门槛。
- CPU_FAULT_MATRIX.json及CSV：全部负控及实际WAL/FIFO fixture，明确非GPU。
- B_COMPARISON.csv/JSON、原始B_INDEPENDENT_CELLS.csv：全部22个单元、时钟/显存/重复计算/能耗覆盖。
- RELATED_WORK_DIFFERENCES及VERIFICATION：正式发表来源与检索失败/排除项。
- EVIDENCE_INDEX、MANIFEST、源码历史bundle与有界证据：源身份、全部原始结果、失败及SHA。

完整模型/音频/环境仍在8TB；公开研究包不是匿名投稿包。原工作树和800个论文文件不变。停止是因为两条机会已有清晰裁定；不是声称topic极限、论文保证录用或已完成生产系统。

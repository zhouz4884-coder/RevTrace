# RevTrace 2026-10-27：全部尝试记录，同步检查点

这是进行中的研究归档，不是结项或论文新优势声明。旧结果不覆盖；未运行设计与 CPU 证据不充作 GPU 结果。当前完整目标见 PROTOCOL.md 和 GOAL_AMENDMENT_R7_DISPATCH_20261027.md。

## 已完成的真实服务实验

| 冻结源码 | 实际执行 | 结果与边界 |
|---|---|---|
| fdb1b1e30b06ee781046621376f458431f3ecb9f (v2) | c4 同步，六策略各1次，共6个 GPU 单元 | 六臂均通过D2/C8，Z/P/text/Stop一致；只有5次实际等待，下一次声明输入未改变，没有算法收益证据。等待计时混入资源排队的问题已保留、随后修复。 |
| 8923af39efbf36c9bf5ab4685f7a0d7d244482c9 (v3) | c16 错峰，六策略各1次，共6个 GPU 单元 | 六臂全run双P99均未通过；135次Canonical历史相同。Authority付费占用约24.4s，原音频释放跨度约21.2s，认证依赖链/资源需求主导。State-aware没有证明优于普通背压。 |

每个完整 GPU 单元的原始 events、Worker 输入/输出、实际 Consumer、配置、WAL 和功耗都在 `raw_packages/` 的逐阶段压缩包中；`RAW_INDEX.json` 给出解压后逐文件 SHA256。不是只上传汇总。原8TB路径亦保留。

## 修复与失败版本全部保留

| 版本 | 完整源码commit | CPU/实现状态 | 新GPU |
|---|---|---|---|
| v1 | c34e09ef8b60b4483cd791570998c0c816d8504f | 父目录pytest配置误引旧源码，13个collection error，失败原文保留 | 无 |
| v2 | fdb1b1e30b06ee781046621376f458431f3ecb9f | 独立pytest配置；Windows/Linux各223通过；84次真实tokenizer同job重渲染一致 | 上述6格 |
| v3 | 8923af39efbf36c9bf5ab4685f7a0d7d244482c9 | Windows/Linux各239通过；逻辑等待与物理排队拆开、实际Consumer反馈；84次重渲染+精确renderer描述符通过 | 上述6格 |
| v4 | 8a875f66af0168c1f34438f156b877d9fe2a5a41 | Windows259通过/16依赖skip；固定Linux LangGraph环境275通过/0skip | 无 |
| v5 | b466a7b79a9899cfdc144423e0de5d90e6d940af | 共享条件剩余ETA、四臂恢复控制器；新测试集成import错误，collection失败1项 | 无 |
| v6 | 326623099623f6fe7585e262b1b19cbb31e18b87 | import已修；309通过/3失败/16skip，3项是旧毫秒CPU fixture使用了生产尺度冷启动安装估计 | 无 |
| v7 | e1511deb6766ce68084128436907b8e2b8e3d417 | 保留激活等待的安全断言并修正fixture尺度；Windows312通过/16skip；Linux328通过、5subtests、0skip | 本检查点尚未启动 |

每版都有 `SOURCE_vN.json`、Git bundle、完整源码tar、CPU环境/配置/原始日志/JUnit/gate。不可把v7测试通过写成v7 GPU性能成立。冻结过程中发现的仅bytecode缓存和格式阻断也记录在 `PUBLICATION_NOTES.json`，没有删除用户源码或重置旧dirty checkout。

v3新诊断：旧剩余时间 `max(Q90(T)-elapsed, floor)` 会在长尾中退化为近零预测。v7改用历史条件剩余分布并计入真实receipt→install时间；稀疏尾部使用明确标注的保守回退。该回退在部分旧选中机会中反而过度保守，不能宣称全局预测改善。所有对照共享新成本模型，warm bank只来自已完成的v3 immediate开发臂。下一次GPU对照尚未产生结果。

## 恢复、原生应用与形式化

- 实测冷启动依赖profiling已完成；84个真实旧job/Z经过完整原生tokenizer/parser重渲染一致。父进程重依赖导入后再启动Worker的串行开销已定位。四臂真实故障控制器已实现并CPU测试，但本检查点尚无新RTO结果，不能用该优化声称解决R7上下文质量问题。
- 原生LangGraph两个结构任务家族、独立SQLite、至少三轮请求/再次写回、真实kernel和独立checker已经实现；Linux真实native CPU回归通过。实际模型provider、FP32同输入自验证和有界GPU pilot已实现，仍未运行。不把旧CPU ZIP与LP1 M拼成新原生神经闭环。
- `formal/`：真实TLC 21个冻结切面符合预期（10正面、11指定反例），TLAPS证明10个命题的20个义务。包括失败开发版本、工具日志、完整source bundle和独立语义复核。它不是Python/CUDA/OS端到端证明，也不证明识别质量或无条件期限。

## 新增R7/R8审计：不是把旧失败直接当当前缺陷

R7的margin FAST_COMMIT属于历史统计风险合同，当前exact路径独立选择FP32 Authority，二者不能混用。R8已经做过VACC、Snapshot+Delta、连续重放及singleton修复；R9/R9.E随后又提供了canonical分段和局部重放结果。因此先核查哪些问题仍然可达，不再重新命名已有机制。

原128条构造session及1645个utterance已能从原始音频/固定算法复算，11个旧outlier也能重新定位；但历史执行源码/环境身份不能仅凭当前目录CODE_COMMIT追认。当前旧目录是混合的后续源码快照，执行身份保留UNKNOWN。Snapshot+Delta利用另跑Canonical参考产生的anchor时，不能把anchor成本当免费；历史估计能耗也不等于同run实测能耗。

新增目标是努力实现有质量和实际成本空间的可信上下文恢复，或在独立来源上证明输入冻结控制超过简单强基线。两者都仍在审计/开发中，不预先宣布成功。

## 阅读入口与范围

- `analysis/GLOBAL_EVIDENCE_MAP.*`：此前阶段全局索引（新增R7/R8/R9细查见本轮补充，不把根README当最新状态）。
- `analysis/HISTORICAL_OBJECT_RESOLUTION_FINAL.json`：30个完整执行commit已解析28个；两项仍UNKNOWN，archive HEAD不冒充执行身份。
- `analysis/C16_STAGGERED_V3_CAPACITY_AUDIT.json`：六臂真实关键路径、输入变化、ETA及全部负结果。
- `analysis/PILOT_C4_INDEPENDENT_TRACE_AUDIT.json`：首轮六臂独立审计。
- `development_scratch/`：临时CPU原型与诊断试验；与正式冻结版本分开，不赋予不存在的源commit。
- `environment_attempts/`：依赖安装失败、成功和下载校验记录；无权重或认证信息。
- `PUBLICATION_MANIFEST.json`：本检查点逐文件身份；原始GPU大包也保留解压后索引。模型、音频和可重建测试临时目录不上传，排除理由明示。

本轮尚未完成：修复后的公平GPU重跑、付费同输入机制对照、真正独立验证、真实RTO比较、原生多轮GPU证据、R7迁移/质量成本验证、最终贡献矩阵与稿件集中修订。没有提前停止现有目标，也没有自动投稿。

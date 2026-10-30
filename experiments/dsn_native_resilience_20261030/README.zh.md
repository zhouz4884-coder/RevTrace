# RevTrace：同源失效遏制与持续状态补强（执行中）

## 当前进度（2026-10-30 HK20:50过程快照）

最终神经源码 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，59文件完整manifest `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457`；Linux253 CPU控件零skip通过。正式short28已全完成，476条原任务/参考/实际Consumer检查通过，见`FORMAL_SHORT28_V1_RESULTS_v1/SUMMARY.json`。这不替代仍待完成的独立actual36语义检查，非法安装/错误拒绝不得提前写零。

连续原引擎875步与逐步restore的875次原步骤完整状态/C/IDs全等，见`LONG_REFERENCE_RESULTS_v2`；118MB全DETAILS留8TB，不进Git。冻结长8正在同一源码/环境执行。短流全28已有summary只读索引在`SHORT28_READONLY_METADATA_INDEX_v1`，它不是raw重计/全36终门。正常Full-call只有1/2 fresh过D2，另一格仅EOS错过；worker故障整轮D2失败/C8通过，Owner冷启全部双门失败，旧事实重放与新模型完成的认证消费分开。

论文主张的收束见`SYNTHESIS_NOVELTY_ROUND5.zh.md`：完整输入资格、原C/U选择权威和整个视图支持分别判断。故障和长流补齐同一协议的可执行压力证据；最终36及独立审计无实质反证后进入正文/全部页面QA/新release，而不继续挑时序点。

本轮接续 `6a2721af` 的完整DSN稿和冻结bdfa正常态结果，落实2026-10-30用户附件中的两个主要建议。正常态结果不重标为新实现；旧CK5恢复结果不移植给新原生路径。

## 本轮固定目标

1. 同一最终原生运行时能够局部拒绝预期迟到/重复消息，原完整调用/C/U/输入义务保持；物理worker退出后可继续服务；Owner故障时从同步可信事实恢复，原到达时钟不断。
2. 两条元数据预选的新speaker合成长流，真实跨30秒音频缓冲移动、context/token更新及多轮修订；控制面历史按活跃依赖回收，与不可避免的累计文字、固定输入及当前model state内存分列。
3. 有限规格和实际执行轨迹精化直接对应最终FullSpec转换：实际Canonical安装只来自输入被真实父状态确认的完整原C/U执行；恢复重放既有事实与新采用旧worker消息分开。

## 实现与边界

`source_dev` 是从实际bdfa完整源码独立clone的新开发仓，最终统一提交、完整manifest/bundle和新干净执行checkout之后才启动神经实验。原Stage/FullSpec与原C/U保留，新两臂共同使用相同局部隔离、durable-before-install、恢复和Consumer；区别只有是否派发/保留条件性完整调用。未冻结开发源码和CPU控制不是已经部署的神经结果。

故障域为Owner与模型workers。幸存Supervisor持有原ORIGIN、持续输入账本、双GPU功率采样与实际Consumer。Owner组死亡后实核无执行者/CUDA所有权，再换Owner namespace；worker-only死亡不重置session状态、已验证完整buffer、合法视图或输入时钟。真实不变量损坏冻结写入，不使用泛化`except: continue`。每incarnation独立Pipe与接收线程隔离半个逻辑帧造成的阻塞。

## 预定实测范围

先做同输入/同原任务的有界开发pilot，验证整个新流程实际能运行并保留端到端机会，再统一冻结正式源码和实验配置。

正式短流主矩阵：现有S0908作为开发故障来源，6条件（正常、真实消息重复/迟到、实际ASR消费后worker fail-stop、IPC半逻辑帧worker fail-stop、原C完成后durable前Owner组终止、同步后安装/消费前Owner组终止）×2策略×2fresh=24格；另原S0764 EOS及S0905合法保留病例各2策略×1fresh=4回归格。两次fresh调换主GPU与arm顺序。每个故障位置与原D2/C8/所有offered/EOS在正式计划中冻结，不按结果改来源。

持续状态：新S0770/S0903各24条8–12秒原clip，精确PCM拼接为228.51025秒与208.1003125秒合成长流，不加静音、不重采样、不在接缝EOS/重置。2流×2策略×2fresh=8服务格。它们是两个speaker的合成持续输入，不是48个独立长会话，也不称自然连续录音。选择早于新audio/文本/神经输出；本轮新runtime未在metadata前冻结，不能冒称该额外前提成立。

长参考先连续运行原作者engine，步间不restore；然后在同GPU对875个原完整start逐个验证serialized-cut restore/full_step路径，全cut/C/IDs比较。首次不一致运行固定同输入重复与连续原程序legal oracle，不能用两条共享restore的路径“互相证明”。所有参考/组件控制与真实服务结果分开。

## 端点与收束

硬正确性：无非法Canonical安装、无ACK输入丢失或重置时钟、无重复义务消费；预期消息局部拒绝不清当前busy/lease；已完成的合法buffer和视图不因worker进程死亡自动消失。实际newCanon与完整原参考、独立精化checker共同核对。

服务端点：原D2/C8及全部EOS、原信用、实际整文本后验支持/未知、质量与能耗；故障→实确认旧执行退出→replacement NN-ready→持久事实实际消费→首个新Canonical→输入债务清空分别计时。冷故障可未达原D2，不能据此改期限或只统计重启后的输入。

记录真实buffer移窗/context trim、修订连续簇、pending/缓冲/去重/witness/视图/outbox大小以及RSS/VRAM。协议条目按活跃依赖有界不等于全部RSS常量；输出和当前状态必须单列。阴性结果保留并定位为实现缺陷、状态表示假设或模型数值原因。两工作包和对应正文/工件同步完成后才收束本轮。

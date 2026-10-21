# RevTrace Phase N：最终 GO / NO-GO

执行日：2026-10-21。正式协议全部完成，16 项最终独立检查通过。本轮不修改论文正文、标题、摘要；不投稿、不声称录用概率或穷尽 topic。

## 确定性决策

| 项目 | 决策 | 理由 |
|---|---|---|
| A/B/C 修订的单 owner/单 private-flight 契约 | **GO，保留** | CPU 交错、完整回归、真实 GPU 新旧对照、窗口账本、实际 canonical text/ACK 与独立 WAL/decoder 重建一致 |
| 修复后 T1 双杠杆结果 | **GO，按新口径使用** | 12 正式+6控制，完整同 rho canonical 内容历史一致；新 clock 和合法 CPU 反事实支持混合归因 |
| FP32 全 token/stop/Phi checker 原语 | **GO，仅有界证据范围** | 各 batch 布局无错误接受、Oracle repeats/self-controls 稳定；长度/模型/输入 realization 边界保留 |
| C2 原生增量 token 直接替换 Coarse target | **NO-GO** | 固定态原始接口全拒，付费 fallback；所有记录的 live Coarse target enqueue 前无该完成候选 |
| 所测付费 C3 Root producer | **NO-GO，未推广** | 仅 0–1/98 及时参考匹配；有可复现处理链等价性缺口且额外 work 要付费；不是安装了新模块 |
| V2 Online Selector | **NO_GO_ONLINE_SELECTOR** | 所测完整候选接口未达到预注册 25% 就绪覆盖；完整端到端优势/≤5% 尾风险未被证明；不凭固定态均值启动 |
| 新 KV-reuse fallback | **不实现** | 不在已通过门槛后的授权路径内；现有 uncached verifier 无可直接复用的 prefix KV |
| T3 有界敏感性 | **GO，完成** | 9 scouts+45 fresh formal，0/6 anchors及1.5/3/sparse6；全历史/代价/负结果均复核 |
| 进入下一轮论文论证重写 | **GO，待用户决定文本** | 证据可支撑更明确的状态边界与时序贡献；不等于投稿已完成或接受可保证 |

这些是 against 冻结工程门槛的决策，不是“验证方法永远不可能”的结论。

## 最关键的正结果

1. **可执行的方法义务已经明确。** 仅 frontier rebase 不足以保证异步可用：还需拒绝过时新发布、有限 reconciliation、durable install 后实际版本化 canonical correction。修订不是重命名 primitive，均有独立 trace 与合法 oracle。
2. **两个杠杆得到修复后复测。** 当前 live c16 上，Coarse/Fine 配对 throughput 中位数 1.2405×（B）/1.2463×（D）；Decoupled Display P99 降低中位数 Fine44.65%/Coarse22.44%，但并非每次 throughput/energy 都改善。新主张不混用旧 available-input 1.403×。
3. **归因不再把等待叫同一个名字。** worker preprocess、GPU model-call、owner receive、WAL 分开；Fine 等待多数同时具有前序依赖和资源占用。合法 CPU 反事实区分原因的存在，不代替真实 GPU 因果份额。
4. **精确验证确实能工作。** C1/C3 在目标 FP32 条件下完整接受，直接否定“完整重生成是唯一来源”。同时成本和就绪说明 checker 可行不自动成为线上收益。该比较比简单说“组合不够”更具体。
5. **C3 发现了实际输入审计边界。** 同 raw audio/H0/rollback prefix 仍可能因 batch processing 得到不同 audio-pad 数。CPU 重复精确复现；没有把输入变化偷换成输出损害、硬件 SDC 或自然发生率。

## 哪些原有主张要收窄

- “Decoupling 只有 rebase 一个义务”须改为有 A/B/C 的完整发布/进展契约；旧 parent 本身不非法，字符/当前可见前沿也不保证单调。
- “18× 状态锁下降”“所有 pre-enqueue 是 parent 阻塞”没有因果识别支持。新数据是共同前沿的完整 stage 与重叠占用，不是 mutex benchmark。
- “一致性只能摊销，其他方式不能合法降本”“组合表达不了”不成立。完整 predicate composition 和 fresh target verification 都是合法对照。
- “0/3 一定击穿原生 MarginGate 保证”不成立。结果类注入、实际执行 context 注入和原理论假设必须分开；F2 adapter 未实际使用的 prompt 改动不算有效故障。
- “6s压力3.45×是正常部署增益”“服务器已普遍通过2s”“全维度支配”不成立。0 hold 的匹配吞吐基本持平；当前 T1/T3 不是2s容量通过点。
- V1 是 exact target-operation controls，不是已上线 selector，也不证明全部 256-token GPU 行为或所有模型/精度。
- 原生增量 Z 与 P/完整 tentative transcript 的单位不同；C2 结果不否定尚未实现的目标候选重编码。Fine 的事后 P-match-and-ready 线索必须保留为**未验证替代解释**，不能转成无认证写权限。
- publication 是 server emit，不等于网络投递/浏览器绘制。`display_revision` 属 owner incarnation；未证明跨连接乱序客户端协议或显示 exactly-once。
- 新工作未修复旧 Whisper 长时质量/内存边界，也没有新增 host/storage-loss、zombie worker 或自然长期流量证据。

## 对论文贡献的建议范围

把主线放在：**模型生成反馈进入未来状态的准入边界，以及在固定有效性义务下协调私有显示、authority 工作和可恢复历史的方法。** 新证据补齐了从合法安装到真实可见纠正的实现链，且区分 verification 本身、候选单位、真实输入与时序可用性。

不把 No-Go 的候选 producer 写成新创新模块，也不靠声称传统机制“不能组合”论证增量。相关 substrate 可实施谓词；论文要解释应用必须提供的投影/覆盖/父条件、粒度与 publication 规则，并用受控归因说明其作用。

剩余主要评审风险是“组织这些义务的贡献重要性”，而不是数据可以自动保证接收。当前结果支持更可检验的创新论证；不支持宣称任何评审异议已免疫。

## 交付与停止理由

已完成全部授权 GPU 队列；不继续尝试未过门槛的 V2，不实现新 KV fallback。停止是因为正式协议各问题已有明确结论且完整独立审计通过，不是把结果修饰成理想值，也不是声称到达 topic 极限。

主证据入口：`EVIDENCE_INDEX.json`、各阶段 Markdown、`tables/`、冻结源码/配置/原始索引与哈希。模型/音频和大 serving trace/power/WAL 留在8TB盘；仅有界材料同步指定 GitHub。匿名镜像未更新/核验；GitHub 公开归档不被称作匿名材料。最终远端 commit 与资源释放记录见独立 verification 文件。

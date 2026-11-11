# 已发表决策规则移植：LA2 可行性与冻结前合同 v1

状态：**可行，先做 CPU 离线决策质量实验；尚未运行、无新模型调用。** 本合同不阻塞新增两个来源的 Full-vs-Ready GPU 确认。实验对象是既有任务输出的发布决策，不替换原 C/U、不改 selected G、不新生成音频或参考。附件 a243 的建议作为待检验意见；“同显存即资源匹配”“±1.5pp 是统一测量误差”“EOS 可几行修复”均不作为先验事实。

## 1. 外部依据与准确移植范围

采用 Macháček、Dabre、Bojar (2023), *Turning Whisper into Real-Time Transcription System*，IJCNLP/AACL demo，页 17–24，DOI 10.18653/v1/2023.ijcnlp-demo.3。[官方论文](https://aclanthology.org/2023.ijcnlp-demo.3/) 第 2 节、图 1 和第 3 节区分：连续新增音频下的前缀一致性、已确认输出跳过、音频缓冲裁剪、后续推理 prompt。LA2 的核心是比较两次带新音频更新的未确认序列前缀。作者实现按词比较；它还依赖词时间戳来裁剪。

作者代码固定为 [ufal/whisper_streaming@6da90b44b7e50d79695e68166d2a2c7609c75abb](https://github.com/ufal/whisper_streaming/tree/6da90b44b7e50d79695e68166d2a2c7609c75abb)。已保存 README、whisper_online.py 和 MIT LICENSE 到 external_rules_evidence_v1，另附 SHA 记录。代码定位：
- HypothesisBuffer.insert/flush：371–417，先去除已确认重叠，再逐词取共同前缀。
- OnlineASRProcessor.process_iter：477–513，确认决定影响 prompt 和裁剪；故只改 UI 并非整个 WhisperStreaming 的严格复现。
- finish：603–611，EOS 单独输出未确认尾部。此动作不是又一次一致性更新，须单列计数。
- README 明确每次更新要有新音频；重复发布、同一前沿 ASR/full-C 两阶段不得贡献两个 agreement 样本。

RevTrace 原始记录没有可直接拿来为 corrector 全文每个字分配音频的词级时间戳。主移植因此命名 **LA2-CP 整视图保守适配器**：保留两次新增音频更新取公共前缀的算法，中文传输符号明确用 Unicode code point；它不是作者词级时间戳实现的逐输出等价复制。必须同时报告文本前缀结果和能映射至真实整视图的结果，不能隐藏未映射部分。

原任务已经在 ASR 内部使用作者 PaddedAlignAttWhisper（实际 NN de0936 的 native_bridge.py:110–129、176）。将内部 AlignAtt 换成 LA2 会改变 ASR 候选、learned C 反馈与 selected G，超出本轮保持原任务的约束。本轮是在 **AlignAtt→原 C/U→真实 Consumer 候选**之上添加 LA2 阅读策略，既不把 AlignAtt 说成不存在，也不称本轮为独立 LA2-ASR 对原系统的同任务替换。

不将固定等两次发布称为 wait-k。Ma 等 (2019) 的 [STACL](https://aclanthology.org/P19-1289/) 是按源/目标词推进的 prefix-to-prefix 训练与生成策略；本轮不改原模型与训练，故仅把 canonical-only 与固定滞后作为**通用控制**。本轮不加未核实的 hold-n 论文标签。

## 2. 冻结输入、更新单位和四条比较规则

首轮固定全部已完成 PILOT24：6 策略 × 原定 2 speaker × 2 repeat，服务计划 SHA 2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6；不按观察到的收益挑臂、来源或前沿。每条规则读取同一个 cell 的同一份已完成候选日程；跨策略日程不假装共享预算或交叉反事实。复用机会审计已冻结的 522 项输入哈希清单，正式 CPU 开始前再验证原始字节。

权威输入：consumer.jsonl 的**实际到达整视图**；publications.jsonl 的完整私有依赖路径；facts.wal 与 GENESIS 的原始 C/U；ingress.jsonl 的 accepted_input（不可变音频 SHA、source_id、frontier、original_offer）；实际 ASR/full receipt/dispatch 用已冻结 OPV1 绑定器校验。worker 消息出现并不等于 UI 已收到，publication journal 写时刻不替代 Consumer observed。

每 source 的“新增音频候选更新”预注册为：首次到达、其真实 visible_frontier 严格超过此前候选更新最大前沿、且对应 accepted_input 已在该到达时刻接受的非空实际 Consumer 整视图。一次跨过多个已接受前沿仍只是一条模型/视图假设；不得凭 ingress 补造中间假设。同/更小前沿的 ASR/full-C、重发、canonical 重投不增加 agreement 次数。它们仍须即时触发支持重验，不能因“不计次”忽略否证。

每 cell 运行相同的四个只读观察器：
1. actual-SUP：重放实际已发布视图，作为程序恒等/指标守恒检查。
2. canonical-only：仅实际已到达的原 C/U 全文；不提前知道尚未送达的事实。
3. fixed-lag-0.5s：实际整视图到达后固定 0.5 wall-second 才可显示，包括非终局 canonical；期间有任何私有支持否证即取消。延迟中可保留已送达的更早 canonical 事实；没有成熟候选时显示空 genesis。允许虚拟定时事件，不能早于已记录到达。最终真实 C/U 的独立 terminal release 适用于所有规则。
4. LA2-CP：两次上述新增音频更新对未确认序列取公共前缀；同源序列外无未来信息。输出文本前缀单独保留。音频计分只可选择**已经到达**、全文为确认前缀之完整前缀、且此时仍有合法完整路径支撑的整视图；选择最大真实 frontier（并以较早到达、完整身份 SHA 打破平局）。无可映射整视图则退至已到达 canonical，记录 unmapped 字符，绝不按字符比例换算 audio seconds。

canonical 变化时以完整 FeedbackCut 等值沿真实路径重定位；兼容路径保留，缺失边界/完整状态不相等即丢弃。所有规则同样应用 SUP 支持义务；旧 canonical SHA 或文本相同本身不证明支撑。LA 已确认文本与新 canonical 前缀冲突时记一次强制重置并以 canonical 为基准，不能对已否证字符继续计合法展示。

无词时间戳时还有一项明确适配：若后续假设修改了已确认文字，保留原确认前缀，但停止延长而不猜测字符重对齐；只有实际 canonical 或支持否证可强制重置。记录此类 prefix-conflict-stall。已确认文本的证明视图全部被 canonical 覆盖、而 canonical 并不包含其剩余文字时，也强制清除没有支撑的尾部。

EOS 明确两栏：普通 LA2 决策；以及在**最终真实 C/U 到达后**执行 terminal release。后者无需伪造第二个新音频样本，所有规则均可终局采用同一个实际最终 C/U。按前沿的终局延迟与 EOS 情况保留；不能先用未完成 ASR 尾部当终局 C/U。

## 3. 输出、判断和因果边界

主表每 cell × rule 全保留：实际候选/新增音频更新/重复数、LA 前缀字符/未映射字符、整视图释放数、支持否证与重置、最终实际文本 SHA、最小编辑 I/D/S、被改字符暴露秒（注明对齐）、可映射 frontier 的首次/持续覆盖、按配置全 offered 音频的 D=2s/C=8s 双期限信用及 EOS/非 EOS 分栏。原 selected G 的时刻沿用原始事实，假设的 V 则明确标为 offline-shadow-V；未映射字符只有内容指标。报告每 speaker 配对、repeat 与全零结果，不把前沿/窗口当独立 n，不在看结果后调 0.5s 或 LA2。

该实验可回答：在相同**已记录计算产物和候选日程**下，已发表一致性规则会怎样交换显示延迟、修订与合法支撑。它直接补充 R1b 的决策规则外部参照。它不能回答替换策略后部署吞吐、GPU/能耗、闭环 SLO 是否提升；不声称整个 WhisperStreaming 复现或击败其原系统。原 Consumer 的 ACK 回传 visible_job_ids，影响 Owner keepalive/GC；线上替换会改变保留与未来日程。本轮观察器在已完成记录上运行，不发 ACK/GC/Owner 命令，故仅对固定轨迹无干预；上线须另冻结 noninterference 或闭环对照。

技术门：完整源/参考/候选支撑/音频更新绑定通过，actual-SUP 指标及终局文本恒等，无未声明未来访问，全部 24 cell 保留。覆盖低、LA2 延迟差、Ready=0、无改进均是结果而非剔除理由。准备独立 CPU 控制覆盖：新增音频单位、同前沿双阶段、迟到旧前沿、无 timestamp 的部分前缀、真实整视图映射、完整状态否证、兼容重定位、未来候选拒绝、EOS 无二次计数、定时取消、原始数据不变、恒等 replay。CPU 启动须 Root 分配空闲窗口并冻结 ID/config/env/8TB 输出位置；当前仅作者源与协议准备，不运行。

冻结前独立审查补强：v1 源 a105e33 未执行；后续 v2 源明确将同前沿但完整状态不等视为 refuted，不能当 covered 继承 LA 第一份样本；被 canonical 覆盖的 prior_update 与文本 previous 同时清除。新增实际合成发布路径控制验证这两个问题。持续覆盖按每个 offered 前沿在 [offer,min(offer+2,horizon)) 内的实际分段视图积分，右删失尾部给上下界，不把最后视图外推；首次覆盖 D 与持续指标分开。

可行性判定：**GO 准备 LA2-CP 离线 CPU 原型；NO CLAIM 对线上资源/闭环性能。** 若完整视图映射稀疏，仍提供可解释的内容前缀与延迟结果，并将稀疏度明列，不改名为精确词时间戳 LA2。


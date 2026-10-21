# 新证据 → DSN 可主张范围

这是一份实验后的主张许可表，不是修改后的论文，也不是录用概率。

| 主张对象 | 本轮硬证据 | 可主张 | 必须收窄/禁止 |
|---|---|---|---|
| 异步 private 结果 | E0/legacy 前后对照；A/B/C CPU；T1/T3 实际事件与窗口账本 | 目标覆盖/generation 检查与有限 reconciliation 是当前单 in-flight 实现的明确义务 | 旧 parent 单独不是非法；不是任意并发/永久输入流的无条件活性定理 |
| durable canonical publication | 每转移后实际文本、version/transaction 的独立 publication 与 ACK；恢复 CPU 控制 | durable install 后必须真实发布纠正快照，即使 private 曾显示更远 | 不是只把 commit 当 display；不是无损 patch、字符单调、客户端网络投递/绘制或 UI exactly-once |
| 两个可调性能杠杆 | 修复后完整 2×2；同 rho 全提交内容/各自 WAL 重放 | 此实现中改变粒度降低服务需求，解耦主要改善显示等待 | rho 同时改变调用次数、切分和条件，不说 100% 仅次数；不得与旧 1.403× replay 混合 |
| pre-enqueue 因果 | 完整 worker/model/receive/WAL 时钟、重叠位图、12 个合法 CPU counterfactual runs | 前序依赖、容量占用、barrier pending 可同时存在且可在控制中区分 | 位图不是因果份额；不能写 18× 纯状态锁消除或拿 CPU delay 当 GPU 成本 |
| 真实内容选择 | 有实际上下文替换的历史 E1；本轮 full FP32 Oracle/重评分 | 候选自一致性不等于选择；可信目标验证可以提供新的选择信息 | 完整重生成不是唯一合法方法；不声称验证/事务/WAL 基元无法组合出谓词 |
| 精确验证器 | 三 batch 形态、完整 Z/Phi/stop、Oracle repeats/self-controls、短前缀负控与 cap4 正控 | 有界集合中认证全部接受序列与指定 FP32 realization 等价 | GPU 候选长 1–34；131-token 控制是 CPU。不是所有长度/模型/数值路径的普适证明 |
| Native candidate 接口 | V0 所有实际 target 的原生 Z/P、处理后输入与 receipt 时刻；V1 三组 | Native 最后一轮增量 Z 不自动是目标 authority 的同单位 continuation | C2 拒绝不否定 P→目标 Z 归一化；不同来源候选可在目标 context 下被新验证 |
| 付费 Root 准备 | 同 proposer FIFO 的三次 live probe；Root 完全不被消费；全历史匹配 | 当前准备政策只获得 0–1/98 的及时参考匹配机会，成本须付且未证明部署收益 | 不称为已实施 V2；不把顺序阶段耗时和称作两 GPU 吞吐下界 |
| 实际处理链 | 同 raw/parent/prefix 的 523/524 input IDs；两个 batch 布局各重复两次 CPU | 仅 source/end/prompt 字段不足以断言 realized inputs 字节相同 | 单例且重复同源，不是自然故障率、输出损害或纯 FP16 数值故障证据 |
| 识别完整性 | 合法 cap4 与 Oracle 一致；旧 Whisper 长时结果保留 | provenance/目标执行等价和识别完整性是不同部署义务 | 不说没有 EOS 就必是非法；不把 Qwen 本轮结果当旧 Whisper 735/1464 的修复 |
| V2 gate | 原生 raw-Z 就绪上界、完整付费成本、C3 actual prep、尚无完整 online tail | 对所测接口与工程门槛为 NO_GO_ONLINE_SELECTOR；不实现新 KV fallback | 不是所有候选编码/工作负载的验证不可能性；不能用离线均值声称线上 P99 通过 |

## 最值得突出的贡献组织

可将新增证据组织成一条方法链：**明确被准入的反馈对象 → 固定每次安装的有效性义务 → 调节 authority 粒度 → 用 A/B/C 保证异步 private 进展与真实 canonical 纠正 → 用完整调用图测候选的合法性、就绪与代价**。常规事务/日志是可用 substrate；应用必须明确这些对象和时序规则。它不是“多起几个机制名”，也不靠宣称组合不可能。

## 尚未被本轮否定的方向

Fine 中 P 相同且及时的事后机会多于原生 Z 相同且及时。新的候选重编码、投影等价类验证、增量声学预处理或缓存可能改变 tradeoff；当前未验证，不算成果，也不能据此启用 V2。若另立协议，应先解决合法候选单位与目标 realized-input 等价，再测完整成本/尾风险，不先做 KV reuse。

本轮不覆盖跨节点/宿主/存储丢失、存活 zombie worker、真实长时流量或有界内存保留。旧 21 次 process-kill、波动/自然扫描与一小时审计是独立历史证据，不与本轮 commit/CPU/重复计数合并成故障率。

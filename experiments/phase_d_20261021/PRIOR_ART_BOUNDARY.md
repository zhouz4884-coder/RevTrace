# 已正式发表的近邻与本轮主张边界

本轮只据正式出版页判断，不以检索到的arXiv版本当新颖性冲突结论；这不是穷尽性文献综述，也不产生任何“first”主张。

| 已发表工作 | 已知对象/贡献 | 对RevTrace的约束 |
|---|---|---|
| Selfridge et al., SIGDIAL2011, *Stability and Accuracy in Incremental Speech Recognition*, pp110–119 | 已研究部分识别稳定性及其与最终识别/参考正确性的区别 | 稳定≠正确、ASR部分输出会修订，不是本轮新发现。[正式来源](https://aclanthology.org/W11-2014/) |
| Arivazhagan et al., IWSLT2020, *Re-translation versus Streaming for Simultaneous Translation*, pp220–227 | 容许修订的直播字幕/重翻译与稳定性约束 | 不能把允许回撤或flicker/latency权衡说成首次提出。[正式来源](https://aclanthology.org/2020.iwslt-1.27/) |
| Sen et al., EACL2023, *Self-training Reduces Flicker in Retranslation-based Simultaneous Translation*, pp3734–3744 | 改进flicker–latency–quality权衡，使用既有normalized erasure度量 | 字符/词擦除本身不是新指标发明；不能据本轮declared-frontier指标声称超过原生ASR/翻译方法。[正式来源](https://aclanthology.org/2023.eacl-main.270/) |
| Macháček et al., IJCNLP-AACL2023, *Turning Whisper into Real-Time Transcription System*, pp17–24 | LocalAgreement streaming策略及实现 | LA2/3必须作为已有方法署名，不能把rolling-character错误适配当唯一竞争者。[正式来源](https://aclanthology.org/2023.ijcnlp-demo.3/) |
| Papi et al., ACL2024, *StreamAtt: Direct Streaming Speech-to-Text Translation with Attention-based Audio History Selection*, pp3692–3707 | 区分hypothesis selection与history selection，设计流式翻译历史保留 | “显示选择与历史选择不同”单独不构成足够新意。它不是本文已实跑同契约系统，不能假造其失败或开销。[正式来源](https://aclanthology.org/2024.acl-long.202/) |

本轮值得验证的增量应具体落在：**固定持久化的认证选择历史下，交付时序会增加当前可见状态撤回；在认证边界满足实际投影状态等价、完整后代链和冻结输入条件时，如何保留未认证的完整临时假设，同时让认证字节/版本/恢复始终绑定真实WAL事实。**

这个增量不能靠“传统组件表达不了”辩护：Standard Safe Async同样获得完整规则，若语义/性能等价，必须报告。对现有生成验证、事务、日志、ASR稳定化的贡献区分应基于对象、有效性条件、实际代价和反例，而不是新机制名字。

## 三种不可混同的等价

1. **Canonical选择认证**：匹配指定参考调用的完整Z/终止/P及条件。旧V0/V1结果证明所测候选单位/及时性/成本不足以启动V2，保持NO-GO。
2. **私有后代连续性**：同F下P相等且实际依赖链/χ与冻结输入可验证，仅允许未认证whole hypothesis继续作为临时view；不要求私有Z就是Authority选择，也不给其写权限。
3. **跨数值实现的操作等价**：相同raw audio/P未必产生同processor实际输入，batch-dependent realization另行验证。冻结同一个已执行batch的metadata重锚不等于对任意新batch重执行等价。

这些是本轮证据组织的可检验边界，不是关于整个领域从未区分过它们的断言。最终DSN主贡献GO/NO-GO由完整矩阵、独立审计与代价结果决定，而非引用数量或速度倍数。

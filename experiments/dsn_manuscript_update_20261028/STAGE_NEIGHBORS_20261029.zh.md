# 阶段交接机会的新增近邻核查

2026-10-29。以streaming ASR / error correction / speculative candidate reuse / pipeline等词搜索，优先ACL Anthology与arXiv主源。本轮是有界补查，不是穷尽性新颖性认证，也没有新增神经实验。

- **RelayS2S**，Long Mai、Junli Liang，Findings of EMNLP 2026，25379–25396。已进一步阅读官方PDF第2节：它在用户轮次结束触发快S2S/慢ASR→LLM两路，学习式verifier决定前缀是否提交给TTS，慢路以已说出的前缀为硬约束生成；前缀失误以续流中的口头修正处理。它排除“首次双路径/首次handoff”等宽主张。RevTrace阶段适配当前验证的是完整同输入ASR候选交给原纠错与状态更新，而非选择一个前缀去约束另一生成器；是否有在线收益仍待测。[官方出版记录](https://aclanthology.org/2026.findings-emnlp.1201/)，[官方PDF](https://aclanthology.org/2026.findings-emnlp.1201.pdf)。

- **Alignment Drift in Single-Model Speculative Decoding for ASR: Mechanism, Correction, and Cost**，Wang等，arXiv:2608.12703v1，2026-08-13。已读主源Introduction/Related Work：它研究draft的音频位置状态、verification注意力校正及收益覆盖额外成本的条件。本文不能声称首次发现音频位置状态重要；区别在跨调用完整反馈输入与原选择尾部的运行协调，非训练新的浅层draft或恢复greedy token一致性。[固定版本全文](https://arxiv.org/html/2608.12703v1)。

此前已精读的SSBD、PredGen、IU与增量计算仍是核心定位依据。新近邻不使具体应用组合无效；它们使“究竟保持哪项原合同、在何种依赖下复用哪一部分执行”更需要明确。后续若stage没有实际收益，只保留本备忘录，不在正文硬加一项机制。

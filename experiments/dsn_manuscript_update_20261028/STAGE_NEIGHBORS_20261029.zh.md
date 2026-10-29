# 阶段交接机会的新增近邻核查

2026-10-29。以streaming ASR / error correction / speculative candidate reuse / pipeline等词搜索，优先ACL Anthology与arXiv主源。本轮是有界补查，不是穷尽性新颖性认证，也没有新增神经实验。

- **RelayS2S**，Long Mai、Junli Liang，Findings of EMNLP 2026，25379–25396。官方摘要明确有快S2S前缀、慢ASR→LLM并行和learned-verifier handoff。它足以排除“首次双路径/首次handoff”这类宽主张。本文待测的是：保持原纠错选择和完整反馈更新，按完整输入cut复用实际ASR候选阶段；不能把另一个选择/生成合同下的延迟数值移作本实验基线。[官方出版记录和摘要](https://aclanthology.org/2026.findings-emnlp.1201/)。本条尚不是该文全方法精读。

- **Alignment Drift in Single-Model Speculative Decoding for ASR: Mechanism, Correction, and Cost**，Wang等，arXiv:2608.12703v1，2026-08-13。已读主源Introduction/Related Work：它研究draft的音频位置状态、verification注意力校正及收益覆盖额外成本的条件。本文不能声称首次发现音频位置状态重要；区别在跨调用完整反馈输入与原选择尾部的运行协调，非训练新的浅层draft或恢复greedy token一致性。[固定版本全文](https://arxiv.org/html/2608.12703v1)。

此前已精读的SSBD、PredGen、IU与增量计算仍是核心定位依据。新近邻不使具体应用组合无效；它们使“究竟保持哪项原合同、在何种依赖下复用哪一部分执行”更需要明确。后续若stage没有实际收益，只保留本备忘录，不在正文硬加一项机制。

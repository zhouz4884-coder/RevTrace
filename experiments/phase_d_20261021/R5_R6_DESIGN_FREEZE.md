# R5/R6 预先冻结

R5：与原12源不同的16独立说话人完整utterances。每条分三个连续段，覆盖整个音频，不循环、不凭识别结果换样。Whisper-small.en：首段FP32 greedy生成非空合法历史并重复；第二段固定音频，FP32正确历史Oracle×2、FP16正确历史×2、FP16另一说话人历史F2×2。forward hook记录**实际首decoder输入**；若替换未被消费，不能计有效F2。第三段使用相同原H0，分别追加第二段native/fault生成结果，固定未来音频，隔离新差异的反馈传播。

保留same-input重复、完整token/termination、mel音频/实际decoder摘要与所有原始结果。完整3段拼接的WER使用完整utterance参考；分段自身引入的质量边界和prompt接口与Qwen差异独立说明。这是人工固定态GPU干预，不是自然发生率、serving加速或D2跨家族无损迁移。

R6：原chinese-05与额外Chinese/English各目标的最后authority上下文，固定raw wave、parent、rollback；singleton和heterogeneous4两布局×2GPU重复。每个实际batch再CPU processor独立重放两次，核对IDs/features/masks逐字节；分开padding、effective IDs、valid mask、生成Z/P/text是否改变。四个目标是开发池条件检查，不冒称四份独立自然故障。batch原生处理差异不等于GPU SDC。

所有模型使用8TB已有离线文件。阶段前验证模型/source/data身份、资源空闲；不修改KV策略、V2、Tokenizer、padding规则或历史以修饰对齐。源码hash在启动前冻结；失败会保留STOP，不能继续发新GPU矩阵。

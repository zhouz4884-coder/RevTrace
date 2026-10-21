# 已出现的库警告，不作静默适配器修改

独立CPU重建时Transformers打印Mistral regex警告。初次诊断假定存在tokenizer.json而失败；该checkpoint实际使用Qwen2Tokenizer、vocab.json+merges.txt。失败与真实文件列表均保留。

随后按**实际导入模块路径**而非glob选取目录，记录警告分支及源码SHA。checkpoint model_type为qwen3_asr，不在Mistral类型列表；通用local-model版本分支会打印此类警告，警告本身不是Qwen分词错误的实证。当前χ的文件/代码与实际结果独立重建匹配。未设置fix_mistral_regex=True，未替换tokenization regex，未改Z/P以求通过。

该诊断不证明任意分词器符合官方模型最优配置；D1保证以冻结χ和受信依赖为前提。对新regex/接口的模型正确性评测应另立契约，不混进本轮性能、完整性或跨家族结果。

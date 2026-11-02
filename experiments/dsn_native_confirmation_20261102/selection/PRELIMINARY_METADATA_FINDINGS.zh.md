# 元数据前置结论：12不是可以预先承诺的未用speaker数

这是正式census之前的只读入口判断，不是已经完成的来源独立性证明或最终选样。

原native开发使用S0764/S0765/S0767/S0768。独立四源实际使用S0908/S0916/S0913/S0905，完整WAV/PCM SHA及原始CRC见 `dsn_streamcorrect_independent_20261029/SOURCE_RECEIPT_v1.json`。后续32matched、resident、fault和本轮cost复用这些人，不增加新独立speaker。长流另外选过S0770/S0903，每人24原始片段组成synthetic long；整个speaker及每个part都必须排除。

旧8–9s metadata池在排除开发四人后只有14位eligible speaker。再排除独立四人和两个long speaker，旧公开archive池的暂定剩余为S0769/S0901/S0902/S0906/S0907/S0912/S0914/S0915（8位）。**这只是当前已确认排除集下的上界候选，尚需全历史core/旧PhaseD/Whisper/TC来源和SHA census；不能提前叫8位全部未用，更不能叫12位未用。**

较早core质量和TC Chinese复合输入使用过ModelScope来源，如S0726/S0740及其它S072x–S075x。它们有明确元数据/拼接成分路径，见 `results/final_closure/quality/chinese_manifest.json`、`results/tc_live_20260906/ground_truth/audit.json`。不能只排native四人；也不能把chinese-00之类重命名复合流当独立新speaker。

批准的只读目录/stat探针结果保存在REMOTE_METADATA_LOCATORS_v1/v2/v3.json：8TB有旧original项目 `/projects/revtrace`、全部现代 `/results/revtrace`、native/TC数据lineage和ModelScope AISHELL缓存。ModelScope缓存当前可见仅名为 `speech_asr_aishell1_testsets` 的包；其旧加载接口使用`split=train`，这**不等价于已验证的官方train split**。目前没有已验证可直接替换的官方train/dev catalog；不为凑12混split。

同split严格人数若为8–10，建议全部保留，服务矩阵动态为4N；若更少，先报告事实再另行判断新split的价值。选择只看固定catalog/speaker/成员/大小，实际完整8–9s/CRC/PCM头和WAV/PCM SHA必须在新音频数据gate逐条通过。原audio不裁、不同话语不拼、不能因CER、延迟、确认率或相容性不好换源。

目录探针是前置定位，不是正式metadata实验；没有加载模型、音频或新reference。`source_dev`的13个语义控制和local/authoritative census均尚未正式运行，等待root冻结源与完整run record。

# 选择与采集契约只读复核

**结论：PASS，实际N=8；未发现阻断后续固定32格确认的选择/采集缺陷。** 这是冻结元数据、原catalog与数据回执的一致性审核，不冒充第二套独立census实现、模型实验或对WAV重新执行的审核。未修改冻结源/CURRENT/正文，未调用模型，也未在reference期间重新读取WAV。

## 实际人数及来源

本轮provided AISHELL test namespace的catalog共20位speaker；历史排除其中10位，尚未用的10位里只有8位有原8–9s完整utterance。S0766/S0904没有满足该固定band的成员，因此**严格可行数是8，不是12**，没有扩大时长、混split或以同speaker新clip填人数。

| 冻结顺序 | speaker | 实际取得source | 完整时长(s) |
|---|---|---|---:|
|1|S0912|BAC009S0912W0434|9.0000000|
|2|S0901|BAC009S0901W0183|8.1380625|
|3|S0914|BAC009S0914W0456|8.9030625|
|4|S0769|BAC009S0769W0190|8.4200625|
|5|S0907|BAC009S0907W0440|8.5759375|
|6|S0902|BAC009S0902W0343|8.5659375|
|7|S0906|BAC009S0906W0197|8.3309375|
|8|S0915|BAC009S0915W0286|8.9980625|

每位1条完整原utterance；source和speaker分别8个。后续2策略×2fresh=32格不增加独立speaker数。

## 核查结果

- 两个census均PASS：Windows原metadata38360文件、8TB原metadata45923文件；均排除43位、0错误/0未解AISHELL alias，输入SHA前后相同。43为保守记录排除集，不是43份独立神经试验；catalog/eligible/fallback列表不当实际模型使用。
- 只读核原catalog、两ledger、固定seed2026110241，独立按metadata重算unused/band pool与抽取次序，8个speaker/primary ID完全复现。全部预锁same-speaker fallback的path/method/长度/CRC/offset/extra与原catalog逐项相同。
- 完整namespace固定为 `AISHELL1/StreamCorrect/aishell1_testset@16f6fd1e17418f1c4111a18fdd39543813206d96`；每条source的 `split_directory` 为 `StreamCorrect/aishell1_testset`，member path仍是裸目录下的原ID.wav，三者没有混写。
- 8条实际帧数128000–144000，PCM16/mono/16kHz/NONE，duration与frames/16000一致；包含9.0s边界。均technical_fallback_index=0，未换speaker/member，也未裁、拼、重采样。
- 实际WAV/PCM SHA不在两历史ledger中，8个WAV及8个PCM SHA各自唯一。该检查基于冻结回执和原data gate；本次没有重复读波形。metadata/data均model_calls=0，reference非空且在锁定选择后才附入；没有按其内容、CER、兼容率或延迟选源。
- acquisition代码对同member网络/CRC重试，只有CRC正确后header/真实band不合才允许下一预锁same-speaker候选；历史hash碰撞或候选耗尽均STOP，不默缩N/换人。

## 身份与边界

选择实际source：`c95735f0dfefd10c60820830616f579374b91c50`；采集实际source：`1a4e129b02e03dba491a1bdcd80de1e585d20f0c`。元数据回执SHA：`3a32b4981c6ac2e9a06cc93ae178d18958b34bdfab5102744b6e6e43ad6fbb59`；终结SOURCE_RECEIPT SHA：`e8a76b9e5c8f59e7c7cb68d73a1ac427597ba21cac1a31b6dae7cbd24dacc07d`；DATA_MANIFEST SHA：`1dc4a41e22c721551edbd600c53ded028dfae91354cfa7af33917d580a757db7`。

完整只读复核观察与每条WAV/PCM SHA见 `SELECTION_REVIEW_OBSERVATION_v2.json`。原metadata目录在8TB的 `.../dsn_native_confirmation_20261102/metadata_selection_v2`，终结data目录为 `.../audio_acquisition_v2`。

可以声称“与已记录RevTrace历史实验speaker/utterance/audio分离的8位新speaker确认”。不能写12新speaker、32独立声学样本、模型预训练未见，或把metadata census当对所有未记录历史活动的无条件证明。亦不承诺跨speaker参考句子文字从未重复。以上边界不阻断本轮真实8人、32格的固定设计。

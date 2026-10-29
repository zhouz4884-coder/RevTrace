# 独立4 speaker：先锁方法和元数据，再获取原音频

最终方法已在新元数据选择前冻结为 `bdfa3b1307d267a5a4caf6484e1ad465c39a592e` 的完整调用保留组合，`FINAL_NATIVE_METHOD_FREEZE_v1.json` SHA为 `fb6a1f57aba24b4300d84b9c30cfc8828bcb86c0fd011db92d4023ef1519364d`。本轮没有再训练、换模型、调精度、看纠错/性能结果再选来源。

依据原公开archive固定revision的central-directory，仅使用成员路径、speaker和未压缩WAV大小，以`(bytes−44)/32000`估计时长。排除旧S0764/S0765/S0767/S0768，优先8–9s band，只有不足4个eligible speaker才按预声明顺序扩大到8–10s、8–15s。首次band已足够，eligible为209条；没有扩大窗口。

使用固定seed `2026102931`，从排序speaker中均匀无放回抽4人、保留抽取顺序，再从各speaker排序候选中均匀抽1条。完整eligible pool、4个ID、ZIP offset/compressed-size/CRC和每人的技术header失败后固定fallback顺序，在任何WAV或transcript读取前保存到 `METADATA_SELECTION_v1_FROZEN.json`，SHA `4bf6249f275cbe5c43099c528316648e1c6aee3485be8968da08e1d50a3b7ccd`。选择源码 `18c7a0f079f211146ab3375cfd5208d6cbef8a76`、完整6文件manifest、环境、root当前指针/无参数preflight和规则均保留。

| 固定顺序 | source / speaker | 实际frames | 实际时长 | WAV SHA256前缀 |
|---:|---|---:|---:|---|
| 1 | BAC009S0908W0369 / S0908 | 132145 | 8.2590625s | 1626b08c1f9b |
| 2 | BAC009S0916W0463 / S0916 | 130637 | 8.1648125s | b1c0aa0f4959 |
| 3 | BAC009S0913W0313 / S0913 | 135184 | 8.4490000s | 9435ebfc329c |
| 4 | BAC009S0905W0246 / S0905 | 132752 | 8.2970000s | de48c54bf5ad |

四条全部通过原ZIP成员CRC/长度、PCM16单通道16kHz、实际frames与完整WAV SHA校验。全部technical fallback index为0，没有更换最初选定的任何一条，没有重采样。总时长33.169875s，每条均有17个原0.5s/EOS offered frontier，原完整参考预计68步。两次fresh重复是时序重复，**声学来源仍为4条/4人**。

原B主机直连公开HF在第1条成功后出现`ConnectionResetError(errno104)`，同一第2成员和另一公开query形态重复诊断均失败；同一精确Range经本机网络返回206。技术恢复使用**同一official public URL、同一冻结byte interval，经本机RAM直接SFTP到B**，没有向本机磁盘写音频，也没有改变来源。恢复源码 `1129b7af5001566a223594ccc35cfcbe1c0fa5db` 独立于选择源码；原失败记录与第1条已成功的WAV保留，后者逐byte核验后复用。14项CPU控制实际在B环境通过，未加载模型或分配GPU。

原transcript reference在选择锁定后才读取，仅附入最终CER reference。最终 `SOURCE_RECEIPT_v1.json` SHA `2040995aa06a5c7958479fe42397d65e299c8a4505de18b35f44099edd9e3b9e`；内含完整source对象、header、CRC、音频SHA、元数据锁SHA、选择时间、来源顺序及旧speaker排除集，已交给独立reference generator机械构建后续计划。

- 音频与最终receipt：B盘 `datasets/revtrace/streamcorrect_independent_20261029/`。
- 实际raw与技术失败保留：B盘 `results/revtrace/dsn_streamcorrect_independent_20261029/acquisition_v1`、`acquisition_v2`。
- 最终数据gate SHA：`a924c78ab7803462dae76852cf39956643fdf4c1fc8e27c092e93f78f6be2ac2`，`PASS_FOUR_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE`。
- 独立只读再核4条SHA/CRC/header/readonly通过，两个acquisition进程均退出，IO已释放。取回17个有界JSON共30,353B，逐远端SHA一致；所有WAV/Range原始字节仍只在B盘。

本报告证明的是数据选择顺序与实际可用性，**尚无新4来源的神经参考或服务结果**。后续保持所有来源、全部offered/EOS、质量/内容/能耗端点，按root独占GPU队列执行。

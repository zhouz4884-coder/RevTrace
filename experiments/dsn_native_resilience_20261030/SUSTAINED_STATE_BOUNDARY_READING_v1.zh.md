# 持续输入与真实状态边界：只读定位及候选实验计划

2026-10-30。仅阅读现有本地源码、附件与ZIP元数据；未读新音频、未按模型输出选择来源、未下载、未启动远端或神经实验、未修改CURRENT/共享runtime。以下是供root选择并冻结的计划，不是完成结果。

## 1. 真正需要跨过的原生边界

实际基准方法为 `bdfa3b1307d267a5a4caf6484e1ad465c39a592e`。固定原作者版本 `bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3` 的本地 `author_reference/simul_whisper/simul_whisper.py` 给出：

- `insert_audio()`（约291–307行）：每个500ms块进入segments；总音频超过 `audio_max_len=30.0` 后移除最早块。每移除0.5s，`last_attend_frame`补偿减25帧；`tokens[1]`加入context，随后删除对应token组。最早确定性移窗在30.5s，而不是30.0s。
- `_current_tokens()`（约250–264行）：非空context作为带prefix的token块放到当前tokens前面。短流中的空context不能验证这条路径。
- `infer()`在解码前调用 `trim_context()`；后者根据context长度及总decoder输入长度 `max_text_len-20` 回收旧文本。实际max_text_len由原Whisper模型决定（large-v2为448），默认阈值不是30秒；不能仅凭长流超过30s就声称实际触发了context trim。
- `_clean_cache()`与token decoder reset必须继续构成闭合cut；已声明cut包含audio segments、tokens、context text/prefix/token IDs、alignment cursor、language、initial tokens/length、sot_index、decoder type、完整contract、frontier和累计transcript。

`restore_cut()`根据 `buffer_start=frontier-sum(segment.samples)` 从immutable source重建实际滑窗，不持有原始音频tensor。本轮应逐边界检验该offset、每segment字节hash和顺序，不只检验文本。

本地author_reference缺 `token_buffer.py` 与完整 `config.py`，因此还不能断言TokenBuffer没有额外缓存或中文trim行为。root在tiny source-read窗口应取回已钉author树里的这两个小文件，核固定commit后再决定是否需要context恢复修复。不要凭猜测减少状态字段。原corrector仍按自身程序读取context/token prefix；即使其长流质量不好，也不能擅改原C/U后称任务不变。

## 2. 最重要的独立控制：连续原作者engine

当前 `original_full_reference.py` 每步仍经过 `CandidateBridge.full_step → NativeBridge.step → restore_cut`。若长context恢复遗漏隐藏状态，reference和serving可能共享同一错误。建议本轮先运行真正连续的原作者engine：初始化与固定warmup之后，每500ms只 `insert_audio → 原infer(C/U) → export_cut`，不在步间restore。

将这条连续轨迹与适配器restore/full_step轨迹比较全部输入/输出cut、原C、IDs和完整累计transcript。至少保留30.0/30.5s、下一次移窗、首次context非空、实际context trim的逐边界对照；原始全轨迹仍完整保存。若不一致，先做同输入、独立重复、连续原程序legal oracle，分开恢复代码缺陷、浮点机制与原作者程序行为。不要让两条共享restore路径自证充分。

这项控制的意义是检验“完整声明状态足以恢复后继输入”；它不宣称任意GPU重跑普遍逐位相同。

## 3. 有界输入候选：两条metadata-first合成长流

现有官方固定ZIP index为 `dsn_streamcorrect_adaptation_20261028/public_asset_metadata_v3/ARCHIVE_ENTRIES_0.json`，SHA `efd03c4e9ef086548d353ead2efacb826afcc6440e1c5b866faf79d8e176ccc4`；包含7176 AISHELL测试WAV、20speaker。

排除旧8speaker：S0764/S0765/S0767/S0768及S0908/S0916/S0913/S0905。剩余12speaker。在8–12s尺寸元数据段中，至少12条候选者为S0770(79)、S0901(15)、S0903(27)、S0906(23)、S0907(20)、S0914(34)、S0915(41)；至少24条者为S0770/S0903/S0914/S0915。这里仅做pool库存，尚未抽取新ID。

推荐root冻结一种主条件：固定seed从满足24条条件的unused speaker中均匀抽两人，每人按固定随机顺序无放回取24条，预计192–288s/流。选择、顺序、CRC/offset/尺寸在任何新WAV或模型输出之前锁定。相同speaker片段直接PCM拼接，不重采样、不增加静音、不在片段接缝刷新模型或伪造EOS，只有合成流最终EOS。所有原clip及接缝sample offset均存manifest，明确标记 **synthetic concatenated utterances**，不称自然连续录音。

两臂×两fresh×两流为8格；GPU角色和arm顺序可延续前轮反转。不要再扩长度矩阵：在同一个完整run内预定30/60/90/120/180s及最终边界采样控制面状态，主SLO分母仍为全部实际offered，不能把中间prefix伪称独立部署。两位speaker是两份声学来源，fresh重复不是额外声学样本。

较小方案为每人12片段（预计96–144s），确定经过多次buffer移动与context追加，但不能保证触发448-token附近的trim。无论采用哪种，实际context trim只按真实日志报告；若未发生，就是该边界未覆盖，不能降低原max_context阈值后冒充原任务。

长流计划还必须提升campaign安全上限：现 `maximum_service_seconds=180` 会使超过180s的输入连最终EOS都等不到。应在NN前冻结与音频长度相关的足够排空上限，例如 `max(180,8*audio_seconds+120)`；它只限制实验挂起，原D2/C8和arrival clocks不变，超时不能给未认证写入放行。

## 4. 精确数据工具复用与修改边界

可以复用 `dsn_streamcorrect_independent_20261029/source_v2/acquire_selected.py` 的ZIP local-header解析、deflate、CRC、PCM16 mono16k header与SHA核验，以及 `ops/stage_same_ranges_v2_ram.py` 的“原official HTTPS Range→本机RAM→8TB SFTP”路线。后者只在root释放IO窗口运行，不能在timed NN期间下载。

不能直接重用旧选择/采集main：它们硬编码4speaker、每人1候选和len==4。需新source将recipe改为两speaker各24个固定成员，网络失败只恢复相同Range。建议技术header失败直接停，不按模型、纠错率或兼容性换片段。尺寸band只用于元数据选择，真实header帧数照实保留，不为满足估计时长而裁剪音频。

在8TB盘生成新PCM16 WAV，保存final WAV SHA、PCM SHA、所有part WAV/PCM SHA、接缝sample offsets、实际总frames和官方文本拼接规则。原17MB reference JSON缓存仅在source选择锁定后读取，不需要再下载。音频、range、环境和长日志都留8TB；Git仅入bounded recipe、source、完整hash与汇总。

## 5. 测什么，不能混成什么

每次原始完整调用和实际安装记录：buffer起点/样本数/segment count；移窗删样本数；alignment cursor在insert前、insert后、infer后值；token组数量/长度；context text与token IDs变化；trim前后数量与触发原因；所有清理后缓存空断言；完整start/end与原C/IDs。观测wrapper只委托原函数，不能改变选择逻辑；两臂获得相同记录开销。

分开报告：自然identity预测改变簇的长度、实际完整start失配簇、取消/丢弃、合法工作接续，以及原offered时钟上的D2/C8/首个新可信输出/能耗。若自然语音没有连续失配，不应按输出换片段；必要时用预先冻结的独立“控制预测故障簇”压力条件，明确与自然发生率分层，原Canonical C/U不可改。

历史/内存至少采样：jobs、completed_full、reconciler.steps、ready、projections、nodes、_canonical_witnesses各epoch与各frontier、_seen_jobs、_issued_proofs、promotions/discarded/abandoned诊断容器、Consumer队列与rows、Power.rows、进程RSS和CUDA allocated/reserved。当前不仅两个被点名的容器增长。

普通GC应依据仍在执行/等父确认/待发布对象可达性及物理incarnation/epoch水位，不能按旧birth版本粗删未来可能收敛的合法输入；缺失witness也不是“已反证失配”。Consumer publication携带自足完整steps，但其in-memory rows、遥测数组与累计输出文本仍须单独处理。可以主张协调元数据得到有界回收，不宜仅因几个dict平稳就主张所有工作内存常量：累计transcript/应用输出本身会增长，日志与输出存放不是保留机制的新GC创新。

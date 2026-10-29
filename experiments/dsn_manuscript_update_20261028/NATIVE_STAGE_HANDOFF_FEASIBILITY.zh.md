# 原生候选阶段交接：源码推导的机会，不是已实现机制

2026-10-29。父 agent 通过 GitHub connector 直接读取固定作者源 `vu-duy-tung/StreamCorrect@bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3` 的 `simul_whisper/simul_whisper.py`，文件 Git blob `02a2202ae6f559c70014eca789796cbc948dd340`，重点为 818–1138 行的 `infer()` 与 579 行起的 SpeechLM corrector。与接入 agent 的本地源码检查相符。以下仅为待实测的设计推导；当前 v6 不变、原生神经结果尚未取得。

## 不只是把已有 Private 输出直接交给 Canonical

现有 v6 的 Private 用 first-beam continuation 走原始 retokenize/append/reset，得到完整可见状态；Authority 仍重复整个 ASR+纠错调用。若实际相同输入的 ASR 已经在另一卡完成，且正好占据下一次可信反馈的关键路径，值得考察**由受保护 ASR 阶段提前产生完整候选，由原始纠错器保留全部选择权**。未受保护的 Private 文本不能因此获得写入权，f0 的独立 FP32 Authority 也不能被此应用适配偷换。

本文已有重根关系可用于判定阶段输入何时成为可信根下允许消费的输入；若原作者已有完整阶段缓存/交接，应按外部先例评价。若作者构建的朴素完整 key 实现获得相同组合能力，同效只是替代实现正控，应采用更简单者，不能据此自动否定组合/应用贡献。

## 作者函数实际提供了一个怎样的切面

原 `infer()` 先处理 audio buffer、mel、encoder、context trim、完整 beam search 和 alignment cursor。随后将以下真实对象送入 `_run_SpeechLM_error_corrector()`：

- `input_audio=input_segments`，并非只用新增500ms；
- 完整有序 `current_tokens` beam 矩阵及 `token_len_before_decoding`；
- 原模型与原处理器。

corrector 从矩阵构造全部非空候选文本，按原训练格式制作音频+文本输入，greedy generate 最多8token；原 infer 将所选追加文本重新编码，再更新 `self.tokens` 并 `_clean_cache()`。其后没有另一轮 ASR 神经解码。**这给出了一个可研究的完整候选切面；现有日志的候选文本/逐步末 token 不足以还原它。**

必须保留的细节不止候选矩阵：ASR 阶段已经改动 context/token 分组和 `last_attend_frame`；原尾部在 corrector 返回 `None` 时仍可能使用 `fire_detected/is_last` 的 fallback。故仅发 `{top1_text, full_input_hash}` 不足以声称原调用等价。

一个候选 packet 至少需绑定完整输入 cut、音频与目标边界、`is_last`、模型/adapter/配置/运行身份，包含完整有序 beam、原 token 长度、选择所需音频及真实阶段后的反馈状态，并覆盖 None/fallback 路径。中间 ASR 的 KV/attention/beam cache 仍可能非空；不能直接套用 v6 只允许 cleaned-cache 的 `export_cut()`。应先证明在该切面之后哪些字段还会被消费、哪些仅被清理，再设计独立的阶段类型。不得把中间状态伪装成现成合法的闭合 cut。

## 如何决定是否值得做

1. 先完成既定两自然见证及满足门控后的12格。若没有非空完整状态兼容交错，不用换来源挽救交接。
2. 若有窗口，再冻结短 profiling wrapper：在真实 corrector 入口捕获完整 beam、完整输入/阶段状态，以设备同步分别记录 ASR 与 corrector 耗时。现有作者 `g` 没有这两个时长；不能用两卡总调用相减推算。
3. 检查受保护阶段和原完整调用在相同实际输入下的候选矩阵/顺序、corrector 实际输入、所选 token/text、完整闭合输出 cut、empty/None/terminal 路径。修复如涉及重新实现原尾部，要明确标成受控适配并有完整等价对照，不能仍称整函数原样执行。
4. 性能机会首先可能是单会话反馈关键路径，不是整体吞吐必胜。两卡各完整副本的理想吞吐 `2/(A+C)` 不小于固定两阶段流水线的 `min(1/A,1/C)`；减少重复 ASR 本身不能推翻这个容量反例。必须扣除传输、匹配、排队、失配重算和相同资源下更强顺序策略。
5. 有明确端到端窗口后才实施服务对照；若无窗口或接口保真成本过大，收束于已完成的合法进展主线，不把阶段交接当成论文成立前提。

这个机会的意义在于可能把“旧工作仍合法”的关系用于真实候选生成与选择权之间的组合，而不是给通用 memoization 再命名。当前没有启动该 profiling、实现交接或宣称收益。

源码：[固定作者 infer 与选择尾部](https://github.com/vu-duy-tung/StreamCorrect/blob/bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3/simul_whisper/simul_whisper.py#L818)。

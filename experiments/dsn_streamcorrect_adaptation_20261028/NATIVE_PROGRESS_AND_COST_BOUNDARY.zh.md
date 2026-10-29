# 原生 g 字段能证明什么，后续候选交接还缺什么

本记录来自固定作者 commit `bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3` 的实际源码读取，不是模型执行结果。
`simul_whisper/simul_whisper.py` SHA256 为 `9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7`。
本轮 v6 不因此修改，原有 2 个 witness + 12 格保持冻结。

`infer()` 返回的 generation 字典从899行开始定义，含 starting_tokens、token_len_before_decoding、frames_len/threshold、no_speech/prob、frame_delay、progress 与 first_token_latency。progress 在每次解码迭代保留 beam 最新 token、sum_logprobs、completed、attended frames 和 logits wrapper；starting_tokens 是共享起始前缀。它没有返回最终完整 top-k token matrix 及 beam parent reorder 索引，因此不能靠这些逐步末 token 反推完整候选包。

作者在889行和1058–1107行分别设置解码和纠错的局部 time.time 时间变量，但没有将阶段时长写进返回的 g。first_token_latency 含作者自身的估算过程，也不是 ASR 阶段A与纠错阶段C的成本分解。v6 的实际总 model_seconds、Authority/Private 差值都不能直接当作同设备、同输入、同路径的 C 成本。

v6 保留完整 selected_correction 字典（原始 prompt、原生全部候选文本、选定 appended text/token IDs）、实际返回 token IDs 以及完整前后 native cut，足以审核本轮全状态兼容和选定反馈。它不保存所有逐步大 logits，也不声称保存了可直接交接给 corrector 的完整 ASR 候选包。

若本轮自然 witness 与真实服务窗口显示后续机会，再冻结一个有界 profiling 源：在原始 `_run_SpeechLM_error_corrector` 的调用边界只读截取其完整 current_tokens/beam顺序、token_len_before_decoding、实际 audio 输入和完整 native state，并原样调用原始函数。计时使用同设备同步的阶段边界，单独记录捕获/序列化开销，保留完整候选与选定输出供同输入及重复控制。不能为了测 A/C 而只留时间、丢掉交接所必需的候选语义，也不能把仅打印的作者局部时间或旧总时长倒推成该证据。

该后续门控必须同时回答：完整输入相同是否产生同一完整候选包；保留/交接开销是否低于节省的 A；强两副本顺序路径的实际D2/C8、质量、能耗或内存成本是否仍给出足够端到端机会。重复实验的一致性只是有限实验证据，不能当作浮点模型确定性保证。

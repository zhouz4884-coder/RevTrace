# 原生context长度：软trim判据、真实序列长度与闭合cut计数

2026-10-30。仅本地只读源码和已收集95/96边诊断数据的纯CPU定义重计；没有新NN、远端读取、阈值/源码/CURRENT修改。原作者BBB的 `simul_whisper.py` SHA为 `9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7`，与固定输入相同。小counter为 [NATIVE_CONTEXT_COUNT_COUNTER_v1.json](NATIVE_CONTEXT_COUNT_COUNTER_v1.json)，实际计数脚本及所有被读文件SHA在其中登记。

## 精确定义

令 `T=Σ tokens[i].shape[1]`，`C=len(context.as_token_ids())-len(context.prefix_token_ids)`，`P=len(context.prefix_token_ids)`，`M=model.dims.n_text_ctx`。

1. **Observer的total是原作者trim的软计数。** `source_v2/state_telemetry.py:11–17` 计算 `total_decoder_input_tokens=T+C`。这与原作者 `trim_context()` 的**初始** `total_len` 定义相同（原作者197–206行）：条件为 `C>max_context_tokens` 或 `T+C>M-20`。本固定模型M=448，常见软阈为428。字段名里的“decoder_input”不能据字面当作精确实际序列长度。
2. **真正 `_current_tokens` 多一个有条件的context prefix。** 原作者250–264行只在context.text非空时，把完整 `context.as_tensor_beam()` 放在tokens前面。因此真正第一轮待解码序列长度是 `L=T`（context空）或 `L=T+C+P`（context非空）。本例P通常为1，即sot_prev。Observer没有把这一个prefix算入soft total。
3. **SOT/initial与beam不应重复计算。** 原作者187–195行的initial token序列已经是tokens[0]，其4个位置包含SOT/语言/task/no-timestamps等；initial_token_length=4、sot_index=0是元数据，不是在T之外再加4或加sot_index。252–254行把第一组复制到beam维，1132行也重复新增组至beam4；它改变batch行数，不把序列长乘4。`shape[1]`包括真实序列位置；不能因为ID≥DEC_PAD就删掉，因为初始special IDs也在此区间。当前本地已读cut没有negative ID位置。
4. **“corrector最多8 token”不等于每个ASR token组最多8。** 原SpeechLM在687行限制的是其自身生成器token；1096行又通过Whisper tokenizer把选中文字重新编码，1132行才加进self.tokens。已读cut有13位置的组，这是两个tokenizer的长度差，不应默认称beam padding或计数错误。

## `bound_still_exceeded`究竟能说明什么

Observer在原trim函数返回后重新编码context并复算软条件，得到 `bound_still_exceeded`。它的准确含义是：**原函数返回后，重新计算的软trim谓词仍为真**。它不是“decoder已经在448之外访问位置嵌入”的观测，也不是模型硬位置界被本方法改变。

两个代码原因需要区分：

- 原trim只删context，不删当前30秒内的tokens。如果T本身已大于M−20，context已空或 `trim_words()`返回0，原作者211–212行会break，软条件可以继续为真。这是原程序允许的退出路径，不是Observer主动放宽阈值。
- 原函数206–210行维护的内部c/total_len是减去 `trim_words()`返回的移除token数；Observer则调用as_token_ids重新编码新的context。`TokenBuffer.trim_words()`按原tokenizer的word分组改写text后返回旧分组token数，重新编码长度不必无条件等于内部递减计数。因此有context时，post-Observer谓词不必等价于原while变量的最终布尔值。不能只凭一个布尔值推断具体break原因。

原infer在880–897行trim后生成current_tokens并记录starting_tokens。**927行while另有 `current_tokens.shape[1] < max_text_len`**。L达到或超过M时，这个初始while可以不进入；编码器和后续原corrector仍可能执行。L在428与447之间也会触发软条件却仍在解码硬guard允许区间。即使某个闭合cut推导L≥448，也不能不经下一步insert/trim和实际decoder调用路径，就宣称发生非法位置访问。后续迭代又使用最后一个token并依赖KV offset（930–938/957行），其实际位置问题也不等于简单看输入tensor的第二维。

## 本地95/96控制能核实的范围

所有输入均对terminal collection manifest的size/SHA重新核对；没有把重复run算成新的声学样本。下表是**每步结束后的闭合cut**计数，不是实际post-insert/post-trim decoder入模记录。

| 已收集路径 | 完整行 | 最大soft total T+C | 最大假设_current_tokens L | 非空context行 | 该闭合cut软条件为真 |
|---|---:|---:|---:|---:|---:|
| v1/default_r0 | 94 | 341 | 342 | 34 | 0 |
| v1/default_r1 | 94 | 341 | 342 | 34 | 0 |
| v1/same_input_r0 | 2 | 354 | 355 | 2 | 0 |
| v3/release_g_r0 | 95 | 354 | 355 | 35 | 0 |
| v3/release_g_expanded_r0 | 96 | 365 | 366 | 36 | 0 |

这些cut最大音频buffer均为480000样本（30秒），最大token组数60，最大组长13；所有假设L都低于448。它们保留了真实buffer移窗与context变动证据，但**不能用于复算整个S0770连续458步的342次post-trim软谓词**。当前本地控制只覆盖至48秒，最终长参考完整统计必须等执行agent收齐相应telemetry后再计算。

执行agent已报告的S0770实际buffer shift398次、context变化353次属于**不同的真实事件计数**，不应因为soft-trigger名称不精确而删掉或改成“没有状态变化”。342也应保留原字段，暂解释为“post-author-trim derived soft predicate true”，不写成“342次模型越界”。

## 完整长参考收齐后的最小补表

只用每次 `context_trim` telemetry的after快照，可以分别列：(a) T+C>428，(b) context是否非空及prefix差，(c) T本身>428且context已空，(d) 推导的post-trim初始L<448/≥448。若要断言实际decoder调用，应再核原starting_tokens/progress或调用记录，不能拿闭合cut替代。已有真实移窗398/context变更353与全部完整state/C/IDs比较继续保留。

本任务不修C/U、max_context或阈值。**原模型当前状态/累计输出/decoder长度的界，与协议活依赖条目数和历史GC界是不同对象**；上述定义不能拿来否定或证明control entries有界，也不能把普通应用输出增长写成协议历史泄漏。

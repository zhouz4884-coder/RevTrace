# 完整长参考的context计数定义重计 v2

本次只读已全SHA收集的 `LONG_REFERENCE_RESULTS_v2` 两条source、连续/恢复两pass的全部STATE_BOUNDARIES。没有新NN、远端读取、C/U/阈值/源码/CURRENT修改，不覆盖v1。实际神经来源为 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，原875步与恢复875边已真实全完整state/C/IDs通过；本计数不重复授予这个神经PASS。精确输入文件SHA和小结果见 [NATIVE_CONTEXT_COUNT_COUNTER_v2.json](NATIVE_CONTEXT_COUNT_COUNTER_v2.json)。

## 定义保持与v1相同

`T=Σ token_group.shape[1]`；`C=重新编码context文本token数（扣prefix）`；`P=context prefix数`。Observer字段total_decoder_input_tokens实际上是原author trim的软计数 `T+C`，软谓词为 `C>448 or T+C>428`。真正 `_current_tokens()` 在context.text非空时的初始序列长度为 `L=T+C+P`，空时为T。本数据prefix均1。initial/SOT已经在第0组，beam不乘序列长度。

这次使用**原trim函数返回后的after快照**，它紧接着供 `_current_tokens` 使用；精度高于v1只从步末closed cut推导的假设长度。所有快照均重新核实T等于各组seq长度之和、total=T+C、derived soft与记录context_trim_triggered一致，且每个context_trim的bound_still_exceeded与after soft一致。没有通过改名或改阈使异常数量消失。

## 全部实际观测

下表按每条source的**一个pass**报告。连续原engine和逐边恢复pass在所有这些统计中完全一致；重复pass不算额外声学样本。首次0.5秒buffer-only调用没有trim_context，因此458/417原step对应457/416次trim观测。

| source（合成流） | trim calls | L≤428 | 429≤L≤447 | L≥448 | context非空/空 | after soft true |
|---|---:|---:|---:|---:|---:|---:|
| S0770，228.51025s | 457 | 103 | 14 | 340 | 56 / 401 | 342 |
| S0903，208.1003125s | 416 | 199 | 181 | 36 | 298 / 118 | 55 |

真实buffer shift分别398/357，context内容实际变更353/252，与原观察汇总一致，全部保留。after-trim token-group数1–59；它是原模型输入状态的数据结构，不是协议GC活依赖条目数。S0770的T/L最大739，S0903最大492；context文本token最大分别65/176。

**342与55的具体分解已经清楚：全部这些after soft true时context为空，且T本身大于428。** context-only trim已没有context文本可减少，剩余超软阈来自当前音频window内的token组，不是仅因为Observer少算一个sot_prev。原trim只调用context.trim_words，并允许返回0时break；该原程序路径可以在重新计算软谓词仍真时返回。本日志未记录每次while内的t返回，故不将所有342/55逐项冒称已直接观测到t==0，只确认“context为空而T自身超软阈”这个充分解释边界。

前述prefix定义差异仍真实存在：context非空时L比soft total多1；它解释一部分L=429但soft=false的观测，不能解释全部342/55。corrector max_new_tokens8属于Llama tokenizer，而原代码重新用Whisper编码选中文字，不能据此断言每个Whisper token组不得超过8；不应将组长13等直接当成padding错误。

## 不应把L≥448写成已发生硬位置越界

固定author BBB `simul_whisper.py` 927行的初始while条件是 `not completed and current_tokens.shape[1] < max_text_len`，completed起始False。若post-trim L≥448，**此while初始条件可以直接为false，不进入ASR decoder循环**；此前encoder已经执行，后续原SpeechLM corrector与反馈update仍可运行。这是源程序分支解释，不是记录到的非法positional embedding访问。

本任务没有加decoder hook或收全starting_tokens/progress Tensor来计实际forward，故只称“post-trim推导L及对应guard条件”，不把376个跨source的L≥448推导项变成376次越界或376次实测forward。若需要讨论模型是否持续产生新ASR token，应另核原程序分支或已有详细进展记录，而不能从一个布尔字段推出。

完整参考875/恢复875全部语义一致，证明声明状态在这两个原程序轨迹上的恢复保真；它不自动证明持续语音准确率或所有模型状态都满足理想软容量。人类CER、原C/U保真与实际新token产生量继续分开。这里也不据结果调整max_context、beam、C/U、音频选择或质量规则。

## 可直接供正文/补充使用的谨慎表述

> The sustained oracle exercises the original sliding audio buffer and context updates. The continuous and restored paths agree on all recorded transitions. A derived post-trim soft predicate remains true in 342 and 55 calls respectively; in these observations the context is empty and the current-window tokens alone exceed the author's soft target. This is not evidence of out-of-range decoder access: the original decoding loop has a separate initial-length guard. We preserve this behavior and report it as an original-program boundary, separately from bounded protocol-history entries.

正文可以只保留原状态转换覆盖和完整保真结论，以上细节置补充或artifact。不得将模型当前tokens/累计输出的大小界与协议活依赖条目回收界互相替代。

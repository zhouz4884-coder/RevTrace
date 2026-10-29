# 原生执行兼容修复与离线审计更正

本记录只说明真实执行准备与审计链，不是应用性能结论。模型、音频、参数、四个 metadata-first 来源、500ms/no-VAD controlled adaptation、两格自然见证后十二格正式三臂范围及原始D2/C8口径不变。没有新训练或按输出换来源。

## Triton API与时钟

v6真实ASR初始化/预热已经执行前向，但作者旧median生成器给`kernel.src`赋值，与实际Triton3.5.1接口冲突而停止。失败不是自然反馈假设失败，也不能记成“零神经调用”。原始失败格与controller日志保留。

API修复对应[官方Whisper的兼容方式](https://github.com/openai/whisper/blob/main/whisper/triton_ops.py)：调用`_unsafe_update_src`更新尚未首次launch的全新JITFunction。自有适配器只变换固定作者函数的三处host赋值；原嵌套kernel的文件/行号、源字节、比较网络和lru_cache保留。原作者`triton_ops.py` SHA为`164c8317baac5a415615206e489e12bc7bdeb6c43ba4fca1bb20c626f8cdc957`，宽度7生成源SHA为`9412b2ad3b2b4546d79f348423341178238301f181d7098c2429ea819fabf43a`。

同时将传给作者`infer(start_time=...)`的遥测锚改为`time.time()`，原有模型和Consumer计时继续使用`perf_counter`。CPU fake-author验证两种时钟域分离。这不改变原D/C端点，也不声称复现作者FTL。

v7控制错误地假定median输入非负；实际捕获`[4,23,4,1500]`FP32、552000项全部finite、其中389836项为负，原因为median之前已有标准化。此控制断言失败保留。v8只更正控制域：同一真实首张量SHA保持一致，另捕获下一输入区间的入口张量及范围；有限有符号、整数ties、真实noncontiguous、长度边界和显式短输入identity均覆盖。双3090共100行/300次原Torch oracle比较中，282次执行GPU kernel、18次属于原短输入identity旁路。NaN、正负零和Inf另按原比较网络的逐bit参考核对；六项均匹配原网络，正负零/NaN与Torch sort的既有差异保留，不使用`nan_equal`掩盖。

数值证据针对已保存的两个真实首张量及所列FP32控制范围；记录到后续token长度5/6/7入口finite不代表对所有未来输入的数值保证。约0.13–0.16ms的median计时与0.85–1.69ms原Torch GPU sort公式比较仅是组件控制，不是服务加速结果。此修复保留原GPU算法，没有把组件替换成慢CPU回退。

## 不重跑神经模型的空显示审计更正

v8两个witness服务均实际完成；原controller在B的离线审核中停止。冻结Consumer本来就将空文本的可见前沿设为0，旧auditor却无条件要求private显示前沿等于native endF。实际126个private显示行中只有一行触发：空文本/endF16000/显示F0，完全符合原Consumer；没有其他文本或谱系不一致。

独立源码`a0652a81a205483ba2091dfd345b85be72ee8b19`更正这一离线预期，保留所有谱系与原模型/输出检查。对两格同输入重复重计一致，伪造空文本进展、修改文本、换成其他来源Canonical父节点三项控制均拒绝。原门控因此可从两格已完成实际数据计算：17个非空raw-changed交错、36个unchanged交错，原四来源全部保留。这是原raw标签门控；是否只是空白/编码表面差异、是否有语义收益仍由后分析区分。

后续controller明确区分“实际神经执行源码v8”与“更正后的离线auditor/controller源码”，只启动原冻结的十二格、原配置/顺序、原fresh-process策略。两格原始神经执行、旧controller失败和全部输出不改写、不重放、不重标。正式质量、原插值D2/C8、强两副本sequential对照和整段Canonical状态一致性仍须等待完整正式范围。

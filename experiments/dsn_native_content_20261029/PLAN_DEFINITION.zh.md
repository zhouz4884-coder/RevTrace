# Native old14：内容端点的最小后验补强

目标是区分原音频处理前沿信用和实际新增显示文本。原v8 Consumer在累计text非空时允许F继续推进；当前轮可以没有新增文本。因此原17.0s不是17.0s新增转录文字，也不是字符吞吐量。

本次只读全部原14格（2 witness+12 formal），不选模型输出、不重跑模型、不改变原D2/C8/首观测信用/任何原gate。输入仅每格CONFIG.json、ORIGIN.json、consumer.jsonl，共42文件，预期数MB；硬上限16MB输入、32MB有界输出。已有primary重计提供三类文件SHA和逐格原信用，启动前冻结。它是看过原结果后的secondary，不伪装成预注册主指标。

每次实际Consumer row，分别比较raw文本和**仅删除Unicode空白**文本；不做大小写、标点、NFKC或语义归一。由同source上一实际row的LCP定义unchanged、strict_append、erase_only、replacement，记录引入/擦除codepoint数。原信用按first-visible covering row的该事件类别做互斥分组，其和仍必须等于原信用。分组意为“信用首次cover恰逢何种文本事件”，不将这段音频秒数归给新字符、不推测字符对应哪段音频。

引入的LCP suffix按(actual row version,offset)赋Unicode codepoint occurrence身份；仍为prefix的身份保留，擦除部分在该真实row闭合，随后相同字符串重现另赋身份。内部编辑导致LCP后整个suffix换身份，这是操作性定义，不是最少编辑或token对齐。每个occurrence记录实际首次观测、撤销、存活时间和关闭事件；最终仍可见者右删失于最后一个同source实际Consumer观测，不补齐到假想UI关闭时刻。字符秒与保留寿命只是描述，不把更慢运行导致的更久曝光当成吞吐收益。

processed/certified前沿字段按原Consumer记录，visible_F保留原含义；本次新增text事件和occurrence层，不臆造一个未记录的“文字音频F”。必要修订与更改是否语义正确仍由其它证据约束，本指标不当groundtruth。

最小交付是14行原信用与文本事件表、每次实际文本事件、LCP occurrence spans、全部offered首cover事件类别和SHA记录。8个小CPU控制只检查累计非空但无新字、prefix身份、LCP替换、相同字重现、空白变化、无变化、右删失和Unicode codepoint定义；不是新服务证据。不扩展成新的模型/正确性审计。

待root确认stage计时范围结束后，执行一次秒级标准库CPU分析并取回有界结果；效应零或原信用大部分落在unchanged行也算完整结果。不得为得到“新增内容胜出”再改归一或挑格。

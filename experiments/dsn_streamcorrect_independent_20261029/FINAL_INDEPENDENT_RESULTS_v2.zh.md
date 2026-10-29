# 四个独立speaker的原反馈任务与服务确认

**既定16格全部完成，272个完整Canonical步骤的start/end状态（包括stage_execution）、原纠错选择C和返回IDs均严格保持原full参考。** 完整调用保留使本组原D2/C8音频信用从37.0增至66.33975s，全部8个来源内时序配对均为正，4个speaker的两次重复差额和均为正，通过预先冻结的方向确认规则。8/8完整调用保留运行通过原whole-run D2/C8测试，对照0/8。

这组有**4条声学来源/4个speaker、每臂每源2次fresh-process重复**，不是8个独立声学样本。最终方法bdfa先冻结，再按size/speaker/固定seed选定4个新来源，未因输出、相容率、质量或性能换源。全部16格、partial EOS、未达标点和内容不匹配均保留；没有为这组调deadline、模型、精度或会话相位。

## 主要端点与完整约束

| 端点 | 保守原反馈链 | 完整调用保留 |
|---|---:|---:|
| 原offered音频分母（每臂8次运行） | 66.33975s | 66.33975s |
| 原D2/C8音频信用 | 37.00000s | 66.33975s |
| credited samples | 592000 | 1061436 |
| whole-run原D99/C99通过 | 0/8 | 8/8 |
| D99范围 | 2.997830–4.682101s | 0.836976–1.662508s |
| C99范围 | 3.254070–4.950728s | 1.090062–1.929134s |
| 各运行C50的中位数 | 2.115049s | 1.202509s |
| D2 misses /136 offered | 62（54非EOS+8EOS） | 0 |
| C8 misses /136 offered | 0 | 0 |
| missing D/C observations | 0/0 | 0/0 |
| 服务窗口两卡能耗 | 35801.253J | 31815.126J |

原信用差为469436 samples，即29.33975s。预注册规则是总差>0，且至少3/4 speaker两次重复之和>0；实际4/4，通过。没有把8个配对用于8个独立声学样本的显著性检验。C50的两个运行中位数相差0.912540s，下降43.145%；各配对C50均下降0.411390–1.652984s（22.14–60.02%）。服务两卡能耗合计下降11.134%，各配对下降3.64–15.33%。这里的C50是先按每格all-offered求中位，再对8个运行取中位，不能称为合并全部frontier的另一种P50。

两臂同源输入、同原ASR/C/U、两份完整FP32模型、相同ASR早显/Consumer、真实learned-C预热、同2s lookahead和相同两卡资源；repeat0/1对换主卡，来源内第二次反转臂顺序。保守链的未来完整调用须等真实父反馈；完整调用保留允许预测输入上提前运行，只有实际完整父输入相同时才安装。二者是本工作组装的受控执行对照，不能把任一者不加说明地称为作者已发表的完整部署benchmark。

## 所有8个配对

下表均为“保守→完整调用保留”，信用单位为音频秒。全文支持是同一首次实际视图前沿G的**完整文字**与后验原Canonical[G]相等，仍以原D2/C8信用为前提。

| 来源 | repeat/主卡 | 原信用 | 全文支持信用 | C50(s) | 服务能耗(J) |
|---|---|---:|---:|---:|---:|
| S0908/W0369 | 0/0 | 5.000→8.2590625 | 3.000→5.2590625 | 1.857884→1.446495 | 4323.295→4165.723 |
| S0908/W0369 | 1/1 | 5.000→8.2590625 | 3.000→5.2590625 | 1.904046→1.447285 | 4359.329→4164.489 |
| S0916/W0463 | 0/0 | 4.000→8.1648125 | 3.500→7.500 | 2.332209→1.320895 | 4667.771→3989.936 |
| S0916/W0463 | 1/1 | 4.500→8.1648125 | 4.000→7.500 | 2.318585→1.303805 | 4711.242→3988.970 |
| S0913/W0313 | 0/0 | 5.500→8.449 | 4.000→6.000 | 1.911513→0.844117 | 4321.745→3781.520 |
| S0913/W0313 | 1/1 | 5.500→8.449 | 4.000→6.000 | 1.804437→0.848485 | 4251.855→3745.007 |
| S0905/W0246 | 0/0 | 4.000→8.297 | 4.000→7.000 | 2.669993→1.093104 | 4580.436→3967.275 |
| S0905/W0246 | 1/1 | 3.500→8.297 | 3.500→7.000 | 2.754196→1.101212 | 4585.580→4012.206 |

每个pair的原信用、严格全文支持信用、C50和服务能耗均改善，没有删除负点或用次要端点替代原端点。完整P99及misses如下。

| 来源/repeat | D99(s)，保守→保留 | C99(s)，保守→保留 | D2 misses，保守→保留 | C8 misses |
|---|---:|---:|---:|---:|
| S0908/0 | 3.444114→1.662508 | 3.708585→1.929134 | 7→0 | 0→0 |
| S0908/1 | 3.559759→1.651323 | 3.820192→1.910987 | 7→0 | 0→0 |
| S0916/0 | 4.644835→1.579212 | 4.917212→1.871252 | 9→0 | 0→0 |
| S0916/1 | 4.682101→1.551031 | 4.950728→1.861144 | 8→0 | 0→0 |
| S0913/0 | 3.186886→0.840442 | 3.445788→1.102708 | 6→0 | 0→0 |
| S0913/1 | 2.997830→0.836976 | 3.254070→1.090062 | 6→0 | 0→0 |
| S0905/0 | 4.182855→1.243748 | 4.446018→1.517213 | 9→0 | 0→0 |
| S0905/1 | 4.329299→1.319541 | 4.586341→1.580808 | 10→0 | 0→0 |

## EOS没有被缩小分母或丢弃

每格16个完整0.5s区间加1个partial EOS，17个frontier全部计入原线性P99。保守臂所有8个EOS均D2超时；保留臂全部EOS同时满足D2/C8。首视图文字与后验Canonical EOS文字不相等的观察两臂都为6/8，仍不能把“及时见到一个完整视图”写成“文字已经准确”。

| 来源/repeat | EOS权重(s) | EOS D(s)，保守→保留 | EOS C(s)，保守→保留 |
|---|---:|---:|---:|
| S0908/0 | 0.2590625 | 3.531664→1.686475 | 3.782791→1.952569 |
| S0908/1 | 0.2590625 | 3.645329→1.670470 | 3.893382→1.922508 |
| S0916/0 | 0.1648125 | 4.732645→1.618258 | 4.995154→1.888997 |
| S0916/1 | 0.1648125 | 4.770158→1.589566 | 5.027451→1.877820 |
| S0913/0 | 0.4490000 | 3.220258→0.574202 | 3.477945→0.825087 |
| S0913/1 | 0.4490000 | 3.027818→0.569188 | 3.284670→0.848485 |
| S0905/0 | 0.2970000 | 4.238838→1.272442 | 4.502684→1.546272 |
| S0905/1 | 0.2970000 | 4.384350→1.361127 | 4.642393→1.626318 |

## 文字支持、字符事件与质量分别说明什么

| 严格内容/事件指标（每臂8次运行） | 保守 | 完整调用保留 |
|---|---:|---:|
| 原信用且same-actual-G全文匹配 | 29.000000s | 51.518125s |
| 原信用但same-actual-G全文不匹配 | 8.000000s | 14.821625s |
| 原信用且same-G参考unknown | 0 | 0 |
| exact offered-F aligned全文支持信用 | 25.000000s | 47.518125s |
| first-cover row为strict_append的原信用 | 27.000000s | 49.339750s |
| first-cover row文字未变的原信用 | 10.000000s | 17.000000s |
| 原信用first-cover整行为空 | 0 | 0 |
| 引入/擦除/末次可见codepoint occurrences | 180 / 14 / 166 | 180 / 14 / 166 |

raw与仅去Unicode空白两种全文判据结果相同，unknown分别报告且均为0。严格支持信用净增22.518125s，所有8对均为正；完整音频信用净增29.33975s并非全都等同于准确文字。same-G只提供后验原模型全文一致性，不是在线认证、人工groundtruth或词/音频对齐。exact-F支持仍独立保留，不能把G>F的视图截成F后重新比较。

LCP字符occurrence计数是实际UI的引入/撤回操作量，不是独立字符样本或误字数。两臂汇总计数相同，而其出现时间不同。文字未变的first-cover行仍可能获得processed-F原信用，因此不会将66.33975s写成新增文字量。

四条独立参考共81个去空白字符，最终原C输出合计5个编辑，CER=6.17284%；两臂、两次重复均保持。分来源为S0908 2/16、S0916 1/24、S0913 1/19、S0905 1/22。质量按每个声学来源只计一次；162字符/10编辑只是每臂两次重复的账面汇总，不是扩大了声学样本。该CER协议为固定的Unicode空白归一，不能冒充原论文评分协议或质量改善。

## 实际保留、合法丢弃与消费边界

独立原始事件重建核实92次promotion均满足`model_start < 真实父Canon安装 < model_end`，92次子/父原model路径均存在实际时间重叠，原birth、job、完整输入绑定均保留。此处model路径包含其CPU/preprocess，不声称每一微秒GPU kernel都同时执行。20个被保留调用的自有identity预测end后来被原C改变：保留当前调用取决于其**输入**相同，并不要求输出预测也正确。

24个ASR前缀在其自身完整start被真实同F Canon否定后跳过C，均无C/U结果或反馈cut。还有2个完整full结果因输入不匹配被discard，其完成C成本保留在服务能耗里；没有completed-full buffer reuse自然见证（为0），不把CPU控制当成自然服务收益。完整调用保留共130个完成的实际ASR加24个弃用ASR前缀，对照128个实际ASR；服务能耗下降不等于执行工作数减少。

两次音频前沿回撤均出现在S0908：r0/r1同一声学模式的两次时序观察，Consumer可见6.0s→5.5s，认证5.0s→5.5s。父j15在5.5s原C选定尾部“领捷”→“领接”；这里只称原模型选定修订，不宣称它更接近人工真值。依赖j16冻结的5.5s完整start为旧预测`87b7da…`，实际Canon为`13badc…`，逐字段仅tokens/transcript不同，是真实direct-start失配。两个j16完整结果均未出现于canonical_install，也未进入Canon历史；随后6.0s正确调用使用真实5.5s输入并严格保持原参考。两次回撤是必要撤回，没有把它们删掉以追求更平滑的图。

另有唯一一次自然相容视图保持：S0905/r1的Canon4.0s→4.5s时，完整可见前沿仍5.0s，全文与private job j11不变。j11旧birth为4.0s，但冻结完整start4.5s逐字段等于新Canon；model仍在运行，物理worker/owner/epoch未改。Consumer只认证4.5s，没有越权认证5.0s临时视图。这将原生在途计算与实际消费边界连起来；这3个事件不是另一套R×S消融，也不估计自然发生率。核心交互结论仍来自核心实验。

上述自然事件由独立冻结CPU checker `dd2cb7e7816fcfd7d6be5194f8f883c98dba1f78` 遍历全部16格重建，见[NATURAL_EVENT_DIAGNOSIS_v1.zh.md](NATURAL_EVENT_DIAGNOSIS_v1.zh.md)，Gate SHA `d3401ec0c82721ec95e487889bace5b9ece099d7cf3755343580f6ef43c1ea1c`。

## 计费范围与可审计定位

服务能耗是两张卡从实际service origin至Consumer drain。加载/原learned-C预热能耗另报：保守100951.276J、保留99966.388J，不能把startup波动写成调度收益。所有配置都真正执行同一固定old-source0 neural-ready，并丢弃结果/重置服务genesis。

最终方法与神经运行源码为bdfa，reference generator为66abab7、独立分析为b473；它们与GitHub归档HEAD不同，完整执行commit均可解析。冻结服务plan为`FINAL_SERVICE_v2_FROZEN.json`（SHA `cab424783f30ff9b53db8deef5eba482d3b101f15336b65de8b1c7d9ced3679a`）；原reference DETAILS SHA `58a33465f5af8dc0f39983253abdcf9bccb9ac79e03690e342792281a36c57a6`。437个神经输出有界文件29,998,654B与远端逐SHA一致，原raw/模型/音频仍在指定B盘。

实际本地独立重计source `b473d9dc47c21d5cc7f88d7871f37497398895fb`，源12文件、23CPU controls和root current无参数preflight通过；主指标/机制与全文内容两项均完成，未调用模型/远端。完整8对数值、所有frontier及derived事实分别在 `FINAL_PRIMARY_RESULTS_v2/`、`FINAL_CONTENT_RESULTS_v2/` 与 `FINAL_PAPER_FACTS_v2.json`。

- Primary gate SHA：`5e33e611a69275e1bd9e91c0675864569fa45aa5bba29fb02a4d285a2390f876`。
- Content gate SHA：`e9773c82701814dd9e8beaddbdbda2fbb7b2ae21ed9e98b4f3cb0d491c0227f3`。

这组支持在已冻结的真实反馈控制流程中，完整调用保留在既定单反馈链、两卡、500ms输入节奏上的服务价值。它没有扩展成大量独立声学样本、长会话/多会话容量结论、原作者benchmark复现、所有早期文字正确、自然发生率或新的全局保证。旧开发负点、ready-only阶段负结果、eager E路线STOP和核心服务边界继续保留。

## 可供主文选用的英文结果段

After freezing the complete-call implementation, we selected one utterance from each of four new speakers using only archive metadata and a fixed seed. Two fresh runs per policy and source, with GPU roles and paired order counterbalanced, yielded eight within-source timing pairs. All 272 Canonical updates preserved the original full input and output states, correction choices, and token IDs. Deadline credit increased from 37.00 to 66.34 audio-seconds; all eight retained-call runs passed the original whole-run D2/C8 test, whereas none of the conservative runs did. The median across run-level C50 values fell from 2.115 to 1.203 s, and service energy across both GPUs fell by 11.1%. Credit additionally supported by complete text at the actual view frontier increased from 29.00 to 51.52 s. This is posterior model agreement, not ground-truth accuracy or online certification. The acoustic population remains four speakers, with two timing repeats each.

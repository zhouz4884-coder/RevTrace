# 第三轮近邻定位：合法重根的应用贡献及原生候选交接边界

核验日期：2026-10-29。阅读 ID：`REVTRACE-NOVELTY-ROUND3-20261029`。这是有界原始文献阅读与设计判断，不是新实验、原生复现或新增性能结果。本轮没有启动模型、GPU、远程实验或修改论文正文。已有实验的实际源码和合同仍按各自冻结记录识别，本说明不重标旧运行。

## 结论和对论文定位的影响

**可以继续主张有价值的应用与组合贡献，但必须把“完整反馈状态下的合法重根及其服务后果”作为对象。** 检索发现三个比泛推测解码更贴近的先例：SSBD 已联合考虑旧输出复用和显示策略；PredGen 已在不断变化的 ASR 输入上验证、复用候选及预生成语音；增量对话 IU 模型更早已经区分 committed 与 active 前沿，并传播依赖撤销。这些工作要求收紧表述，不直接否定特定反馈服务中的新约束、新冲突和实际收益。

不应再使用“首次分开计算/显示”“首次独立稳定/临时前沿”“首次按依赖保留计算”等广义表述。当前可辨认的组合是：**一个保持原选择的受保护 Canonical 服务独立推进；旧 Private 的合法性由同音频边界的完整跨调用状态和真实冻结依赖路径见证；这一关系同时约束计算保留与实际 Consumer 的完整假设保留；没有用途的工作另以实际取消/排空协议退出。** 这是待证的具体服务能力，不要求每个原语原创，也不把已有方法合理组合视为天然缺乏贡献。

本轮确认的新近邻六项列于下表，均阅读了机制部分。所有“本文应增加的区分”都是本评审的解释；文献未规定某属性，不等于作者无法扩展。没有穷尽性或“未找到即不存在”的结论。

## 六项原始近邻及实质比较

| 近邻与已核身份 | 本轮实际阅读、已知机制 | 对 RevTrace 的约束与仍可研究的关系 |
|---|---|---|
| **SSBD**，Linxiao Zeng、Haoyun Deng、Kangyuan Shu、Shizhen Wang，*Self-Speculative Biased Decoding for Faster Re-Translation*，arXiv:2509.21740 **v2，2026-01-04**；首次版本2025-09-26，标题曾为 Faster Live Translation。未核实发表 venue。[身份](https://arxiv.org/abs/2509.21740v2)，[全文](https://arxiv.org/html/2509.21740v2) | §3.2–3.4、Table 3–4、App A.1–A.3/Algorithm 1：在更新后的输入上，一次 forward 验证旧输出 draft，分歧后续写；display-only mask-k 隐藏后缀但保留其内部复用。默认 β=0.2 偏向旧 token；β=0 是已测的无偏版本。App A.1明确：跨步 KV 复用限于共享 prompt/source-prefix，assistant 后状态通常不能直接复用。 | 它已解决“截断显示会牺牲内部复用”这一真实跨层冲突，不能把一切 R×S 协调说成新问题。区别在于它对**变化后的输入重新验证 draft**；RevTrace C1 要求同 F 处完整 P 一致并证明实际依赖合法，再保留完整既有分支；C2不以隐去任意 k 个后缀为条件。β=0也必须被承认为强近邻，不能只拿有偏版本作弱对照。其 paper-level 无偏算法不自动保证本部署浮点路径逐位相同。 |
| **PredGen**，Shufan Li、Aditya Grover，*PredGen: Accelerated Inference of Large Language Models through Input-Time Speculation for Real-Time Speech Interaction*，COLM 2025。[会议接收页](https://colmweb.org/2025/AcceptedPapers)，[全文v2](https://arxiv.org/html/2506.15556v2)，[作者仓库](https://github.com/jacklishufan/PredGen) | §3/Algorithm 1、§3.1–3.3、App B.2：每个新 partial prompt 验证旧候选前缀，再生成文本及首句 TTS；最终验证后可直接使用预合成语音。Greedy、Top-K、reflection 三种 verifier 不可混为同一精确语义。App B.2使用 TTS合成语音→Whisper-Live 的真实 ASR输出，包含输入自纠正；主体仍以模拟输入节奏评价。 | 不能把“ASR修订期间先做工作、以后确认后复用”称为首次。这里是对**下游回答和TTS**的候选验证；当前复用并不等于保持一个外部受保护的纠错反馈历史，也未规定已显示完整 ahead 在独立 Canonical 安装时的保留性质。强比较思路应取 greedy/完整输入验证，而非仅较宽松 Top-K/reflection；不要求为本论文另建语音对话系统。 |
| **IU 增量对话模型**，David Schlangen、Gabriel Skantze，*A General, Abstract Model of Incremental Dialogue Processing*，Dialogue & Discourse **2(1):83–111，2011**，DOI 10.5087/dad.2011.105；2009有同名短版。[元数据](https://aclanthology.org/2011.dnd-2.11/)，[完整29页](https://aclanthology.org/2011.dnd-2.11.pdf) | §3.3.2–3.4.2、§5.2.1–5.2.2、Fig12–13：grounded-in/supports 关系记录模块依赖；purge撤销真实支持闭包；commit承诺不再撤销。模块可异步并发。Fig12明确以 newest committed **NC** 和 active right edge **RE** 独立表达提交与临时前沿；Fig13连接输入/输出状态。 | 这是比泛数据流更直接的应用祖先。必须致谢提交/临时进展、Consumer撤销、因果依赖和异步模块等概念。其commit是模块行为承诺，并非神经结果正确认证。新增内容应落在**完整神经跨调用状态**、同F重根见证、在途冻结输入及原受保护选择不变；不能只把NC/RE换名成Canonical/Private就声称新架构。 |
| **Adapton**，Matthew A. Hammer、Khoo Yit Phang、Michael Hicks、Jeffrey S. Foster，*Adapton: Composable, Demand-Driven Incremental Computation*，PLDI 2014，156–166，DOI 10.1145/2594291.2594324。[作者全文](https://matthewhammer.org/adapton/adapton-pldi2014.pdf)，[作者所属机构artifact](https://www.cs.umd.edu/projects/PL/adapton/) | §2–3.2，尤其Figures4、6的FORCEPROP/CHECK-GET/CHECK-FORCE：动态依赖图、检查已记录读取值、按需修复/复用；将inner计算与outer observer分开。Sharing、swapping、switching可保留跨上下文工作；输入改变并不要求立刻重算所有潜在后继。 | “依赖未变可以保留”“没有观察需求就不重算”是成熟基础。C1是这一思想在声明的反馈状态接口上的充分条件，不是新通用增量计算。可研究的新增冲突是：同一个服务中**独立认证选择、合法临时计算、当前可见假设、仍占物理资源的已无用工作**并不具有同一生命周期。Adapton的按需重算不能被直接当成GPU取消的测量结果。 |
| **Nominal Adapton**，Matthew A. Hammer、Jana Dunfield、Kyle Headley、Nicholas Labich、Jeffrey S. Foster、Michael Hicks、David Van Horn，*Incremental Computation with Names*，OOPSLA 2015，748–766，DOI 10.1145/2814270.2814305。[全文](https://arxiv.org/html/1503.07792v2) | §4及§5.2：名字/namespace定位可复用计算，实际参数比较与依赖clean检查控制复用；参数不同会清结果并传递dirty；formal core证明from-scratch consistency。名字只识别候选节点，不能替代依赖有效性。 | “跨版本身份不等于必须废弃，名称相同也不等于合法”已有强理论先例。RevTrace不宜把完整P/F检查声称为一般状态等价理论，亦不能借用其from-scratch定理保证未建模的浮点/cache。已有C1按边归纳只证明声明合同内实际依赖合法性，保持这一较窄范围是优点。 |
| **Differential Dataflow**，Frank McSherry、Derek G. Murray、Rebecca Isaacs、Michael Isard，CIDR **2013**。[机构记录](https://www.microsoft.com/en-us/research/publication/differential-dataflow/)，[会议全文](https://www.cidrdb.org/cidr2013/Papers/CIDR13_Paper111.pdf) | §3.1–3.4、§4：以偏序版本和保留的indexed differences表示变化，允许从多个合适前驱复用，而非只取“最新版本”；撤销可用负difference表示；算子依赖维护使局部变化反映到全局状态。 | 版本前进不等于所有旧状态无用、多前驱增量复用和撤销传播都有系统先例。其可分解collection/operator语义不自动使黑盒神经输出可增量修补；本文保留的是完整结果和合法依赖路径，不应伪称神经输出delta分解或新的通用数据流理论。 |

### 重要校正：SSBD不能只归入“普通token推测解码”

它的输入确实来自流式ASR转录（ACL60/60分支），而不只是固定离线文本；它还专门协调内部draft和外部显示。将它粗略写成“offline decoding，故无关”会漏掉最接近的跨层贡献。另一方面，所读算法在每个更新输入上重新验证旧输出；没有由旧token表面一致直接继承完整旧神经状态。这个差别与当前P/F/冻结链条件直接相关，优于“任务名称不同”这样的表面区分。[对应全文§3、§4.1、App A](https://arxiv.org/html/2509.21740v2)

## 当前C1–C3究竟增加什么

| 层次 | 已有思想，应直接承认 | 具体应用约束与需保留的论证 |
|---|---|---|
| C1 | 动态依赖、同输入memoization、状态版本、变化传播与合法缓存已有。 | 实际模型调用输出成为下一次调用的完整输入；必须包括adapter声明的全部状态、准确F/音频和不可变合同。展示同文本不同P、同P不同F、断链/错冻结输入等反例；正例按完整边归纳。结论是**充分的依赖合法性**，不是最小性、独立浮点重复必同或Private获得Canonical权限。 |
| C2 | IU的NC/RE、SSBD显示隐藏、暂定/稳定输出和显示修订已有。 | 在认证根安装边界，若**当前完整假设**位于新F之后且仍兼容，则保留该完整假设，认证lane同时推进；不做文本后缀对齐。需要实际Consumer证据，显示后仍可能有合法文本修订。R/S联合是某类非退化服务进展的实现，并非安全性的普遍必要条件。 |
| C3 | 因果失效、需求驱动、safe-point执行和资源回收已有；Retire尤其近。 | “仍合法”与“已无剩余用途”分开判定。CancelRequest不是释放；以RowComplete/RowCancelled终态及同步BatchDrained证明实际lease恢复，并保留accepted-input和原期限义务。若简单coverage/watchdog同效，C3可作为服务实现支撑，不须包装成新取消算法。 |

现有数据适合证明这一冲突的真实后果，不能替代上述语义证明：主确认24个独立speaker的Qwen错峰中，仅R有17次前沿回撤、联合0次；新36格在c16点仅R共45次、联合0次，但信用交互三次中有一次为负，且该点四臂D2均失败。c8工作点四臂都通过。**因此新颖性应由“什么关系允许了哪种进展及何时有效”支撑，不能由联合普遍支配/SLO独占优势支撑。** 数值来自当前[贡献计划](../../docs/research/independent_synthesis_20261028/CONTRIBUTION_PLAN.zh.md)和[第三轮结果判断](ROUND3_DECISION.zh.md)，不是本轮重新运行所得。

## 原生ASR候选交接：可以保留为门控机会，尚非第四项贡献

当前[候选交接备忘录](../dsn_streamcorrect_adaptation_20261028/CANDIDATE_HANDOFF_REVIEW.zh.md)的正确切面是“原始ASR完整解码之后、原始learned corrector之前”。**在完全相同的冻结输入上复用已完成函数结果，本质上已有memoization/增量计算先例；将其用于ASR top-k packet本身不能承担算法新颖性。** 有价值的应用问题是：native反馈纠错服务能否在等待受保护选择时预计算，将稍后仍匹配的完整候选交给原corrector，既保住原函数输入/结果，也减少一次真实关键路径ASR成本。它不同于SSBD在改变后的输入上验证旧token，也不同于把任意FP16 Private改作f0独立FP32 Authority。

目前只保留这一假设，不启动变体。是否值得实现，先由既定v5原生witness及正式14格回答：

1. **机会真实存在。** 原生完整状态下出现合法ahead/候选可交接窗口；重复ASR在实际关键路径上占主要成本。只测整调用时间时，不能用两张卡的总时长差冒充corrector阶段时间。
2. **切面可保真。** 完整beam token矩阵、顺序、长度/offset、corrector音频、alignment cursor、buffer/context、fallback/rewind和更新尾部所需状态全部绑定；最终top1/text相同不足以证明top-k相同。应用合同若绑定具体精度/shape/卡路径，交接也须符合；有限次重复仅提供该范围证据。
3. **保护不降级。** 原corrector输入清理、prompt、候选顺序、解码/停止和状态更新逻辑不变；仍保持独立受保护选择的权力边界。依赖合法不直接等于输出已认证。
4. **有强端到端上界。** 扣除完整packet传输、排队、检查及不匹配重做后仍有明确服务窗口机会；和相同两卡上的**两个完整顺序副本**比较。固定ASR/corrector流水线并不天然胜出：理想吞吐上限分别为`min(1/A,1/C)`与`2/(A+C)`，阶段失衡时流水线较差。不能把这条理想上界当部署结果。

若v5没有这些机会，收束原生应用线即可。若有，不应因“memoization已有”就提前否决；应判断**完整候选保真、独立选择推进和实际服务窗口**这一组合约束是否需要新协调，并以同资源强对照验证。无需重新打开通用KV复用、近似输入等价或更强sticky Consumer支线。

## 最强而有界的比较义务

- 原生作者完整顺序实现、同资源的完整副本并行，是应用性能底线；当前适配必须清楚标注native原行为、兼容修复与受控适配。
- 当前同底座保守version fence/快照Consumer与完整Standard正控仍最直接检验关系。给Standard相同完整证据后同效，是组合可实现的正结果。
- 对交接如立项，增加一个**按完整冻结输入精确key复用的强朴素方案**，避免仅打败“所有版本变更都重算”的弱基线。它是作者构建的memoization式适配，不冒充运行了Adapton/SSBD原系统。
- SSBD β=0、PredGen greedy提供“先验证再复用”的强概念对照；只有native确有对应验证接口、且实际执行保持同一完整合同，才考虑有界实现。不要为了相关工作表格而新增翻译/TTS大分支，也不要把改写算法叫原生复现。
- 引文中承认IU和自调整计算的祖先关系，再明确神经反馈状态、实际Consumer与物理执行寿命的不同证明义务。保留Retire比较，但parent_cancel不是完整Retire。

## 检索方法、来源和可审计限制

使用`nature-academic-search`的multi-source-search/reference-mgmt流程。已读取manifest、always-load core及对应workflow；当前工具目录无academic-search MCP，因此用web发现并在ACL、作者全文、arXiv、会议官网和机构页面验证。Crossref对三个已核DOI的作者、venue、页码和年份返回成功，保存于[NOVELTY_NEIGHBORS_ROUND3_METADATA.json](NOVELTY_NEIGHBORS_ROUND3_METADATA.json)。OpenReview网页/API本次遇到验证/403；PredGen的venue由COLM官方接收页核实，全文使用arXiv v2。没有绕过访问控制。

发现查询覆盖：`speech recognition speculative correction streaming asynchronous`、`streaming ASR speculative reuse`、`optimistic speech recognition incremental`、`incremental speech recognition reuse hypotheses`、`SSBD speculative Zeng 2025`、`PredGen Li Grover`、`self-adjusting computation reuse trace change propagation correctness`、`Adapton incremental computation names reuse demand driven`、`Differential Dataflow CIDR 2013`。更泛的Whisper/ASR token推测解码命中保留为发现线索，没有冒充本轮另读的新增近邻。本轮新增精读限制为上述六项；既有九项ASR与Retire等综述仅作上下文。

六项BibTeX保存为[NOVELTY_NEIGHBORS_ROUND3.bib](NOVELTY_NEIGHBORS_ROUND3.bib)。SSBD用所读v2的2026修订年并注明2025首次提交；PredGen用已核COLM2025身份；Differential Dataflow使用机构/会议记录的2013，未给它编造DOI。其PDF首页年份印成2012，与会议官方2013记录冲突，已按官方会议身份处理。Adapton第二作者按原PDF byline/Crossref记为`Phang, Khoo Yit`；不从二级索引重排姓名。

本结论建立在当前工作区材料和本次原始文献阅读上；没有从旧memory中的数值推断当前实验状态。读文献支持定位和设计义务，不能证实原生14格或候选交接已成功。

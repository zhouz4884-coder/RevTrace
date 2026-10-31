# RevTrace：DSN 科学主线与竞争力独立判断

审查 ID：`DSN_STORY_COMPETITION_REVIEW_20261031`。范围是科学问题、组合贡献、证据选择和 11 页叙事；不是代码安全审计、Nature 模拟审稿、会议录用概率预测或新增实验。只读当前工作稿与本轮有界证据；未访问远端、启动 NN、修改论文/源码/CURRENT/Git。本文的“当前”固定在本地 paired 24/32 checkpoint；resident 与 completed-buffer 正负控仍待运行或独立核验，不预填成功。

## 1. 独立裁决

**现有研究已经支持一个连贯、具有实质内容的 DSN 科学贡献；本轮范围也有机会使它成为一篇更有竞争力的完整论文。贡献成立不依赖于再发明一个资源控制器。** 最有说服力的中心是：反馈更新同时改变“一个调用能否使用”“谁有权选择它”“当前完整视图还能否保留”，这些判断不等价。把它们混成版本失效或单一计算复用判断，会产生可测量的服务后果；分别构造见证并组合后，可以保留原选择任务和受支持的已交付进度。

这已经超出“给原实现补几个防御性检查”：计算保留单开在预定 24-speaker 层中把撤回从 12 增至 17，联合保留为 0；实际完整两秒区间先准时出现、又在仍兼容时消失 2.176 秒。它揭示了 first delivery 指标遗漏的服务现象，并以因子控制说明计算复用与消费规则必须共同研究。最终 selected 历史不变，使该现象有清楚的反事实解释。

但“有贡献”与“已经证明广泛实用”不能合并。**唯一最弱的轴是：这套组合在最终实现、明确且可信的服务合同中，其实际必要性和收益覆盖有多宽。** 不是文献数量不够，也不是所有原语都必须新造。当前证据对机制存在性和条件正确性很强，对可用服务范围的支撑仍集中在小型、受控、有限请求与特定 relative-progress 窗口。剩余 paired/resident 正是在补这个轴。

不建议据此给出“录用率”或“必拒/必收”。我的投稿方向判断是：继续围绕现有单一问题完成本轮，收紧叙事后进入正常 DSN 打磨；不能把尚未完成的应用证据先写成解决了普遍持续服务。

## 2. 哪些内容是科学贡献，哪些内容承担支撑作用

| 内容 | 在论文中的科学作用 | 应有的主张力度 |
|---|---|---|
| 完整输入资格与 whole-view 支持分离 | 提出可操作的两个判断；解释为什么保住工作仍会丢掉已交付进度 | 主贡献，贯穿摘要、动机、机制和主实验 |
| native 的当前输入确认与该调用自己的下一预测分离 | 把反馈依赖落到真实原始 ASR/C/U；说明预测错误不等于当前调用非法 | 主贡献的具体实例，不能由 own-end disagreement 冒充 input-confirmation rate |
| eligibility、selection authority、durable fact、actual consumption 分层 | 使保留在并发、跨进程与恢复时仍有明确定义；解释可复用为何不自动可安装 | 组合闭合，不单独声称发明事务/RPC/WAL |
| R×S 因子结果与准时交付后消失的实际区间 | 给出问题的实际后果、必要的反事实和独立于质量的服务现象 | 主实验证据；保留负重复和高负载失败 |
| selected-trace refinement | 说明协议额外步骤不会改变受保护 selected 转移关系 | 安全连接论证；不包装成深的新 refinement 理论或整个显示行为的等价定理 |
| 3976 转移、90 compatible applications、跨 death 的 4 个已有视图 | 验证同一语义跨 state change、执行/消费生命周期的适用性 | dependability 证据；不是低恢复时延或自然发生率 |
| 新 completed-buffer 正负控 | 若通过，覆盖已完整接收、producer 已死、父输入后确认这一关键交错 | 定向机制见证；不是故障时 D2/C8 改善证据 |

两个充分条件的证明本身较直接。若把论文标题和贡献写成“新定理证明相同输入可复用”，会主动削弱它。可争取的创新在于：选准服务对象、明确非等价判断、落实真实反馈状态，再证明并测出它们组合后的行为。已核验先例建立了依赖复用、draft 复验、显示稳定和事务身份的基础；本篇应准确归属，并以具体反馈/whole-view/原 C/U 合同解释组合增量。

完整正控制拥有同样能力、产生相近结果，是组合可重现的证据。它是自建 complete-contract instantiation；不能被说成外部先例已经实现全套，也无需为了制造胜负将它削弱。表中应清楚标作 `Full-contract control (ours)` 或等价明确名称，正文用一句解释预期相近；其保留资格和权限与主联合臂相同，就不再承担“缺少该组合”的反事实任务。

## 3. 这个最弱轴为何真实存在

核心确认的优势不是压倒性的延迟改善：联合臂在 headline 层多得 26.645/714.110 秒 credit（3.73 个百分点），相对 computation-only 为 16.610 秒；全部 headline runs 仍失败 whole-run D2。fresh repeat 的 interaction 为负，同步到达时 ahead-view 机会很少。这里最稳定的结论是兼容进度的持续可用性，不能把它扩写成通用加速器。

旧 native 8/8 是四个 metadata 预选、8–9 秒来源上早期 bdfa 的真实机会；它确实很有价值，但不能贴给最终 4f。当前共同条件 paired 的 24/32 快照为：

| 版本 / 策略 | 已完成 runs | D2/C8 完整通过 | Credit / offered（s） |
|---|---:|---:|---:|
| bdfa / Conservative | 6 | 0 | 25.000 / 49.593750 |
| bdfa / Full-call | 6 | 6 | 49.593750 / 49.593750 |
| 4f / Conservative | 6 | 0 | 22.500 / 49.593750 |
| 4f / Full-call | 6 | 4 | 49.075625 / 49.593750 |

这 24 格的 408 个 selected transitions 全部通过原 reference 检查；缺失 credit 为两个 S0908 EOS，各为 0.2590625 秒。当前结果同时支持“最终实现仍有很大的正常态机会”和“最终实现的 D2 边缘成本须如实呈现”。不能从这张未完成表宣布最终 8/8、性能等价或归因已完成。表中的 6 次也不是 6 个独立新说话人。

无 reset 长流则是真实负边界：全部 D2/C8 与质量失败，两来源 CER 为 638.48% 和 251.53%。D/C 首超限和宽松离线长度下界均早于 after-trim 448 条件，因而不能把全部失败归咎一个末端 guard。新独立 EOS resident 合同若成功，说明存在一个可用的请求式服务应用；它不会把原坏长流变成成功，也不意味着实现在线 VAD。

因此应把“泛化轴”具体写成：已有跨来源的机制证据，加上最终实现上的有限可用服务合同；能力边界则包括相对进度稀少、超载、无端点递归状态和冷恢复。这个表达既能承认限制，又不会让所有负结果淹没已经发现的协调问题。

## 4. 是否增加 resource-admission / interference 研究

**当前选择：完成既定 paired、resident、buffer 正负控；主稿只保留 eligibility 与 admission 的区分，不新增 adaptive admission 贡献。** 这个选择基于论证收益，不基于“必定耗时几周”或“必定是第二篇”的经验断言。

资源准入可能补强当前最弱轴，但需要满足更具体的链条：同一有效服务合同下确有 shared-resource 干扰；新增 conditional dispatch 是干扰的可干预原因；在不改资格、原选择、义务时钟、精度和持久化的前提下，一个简单准入规则能改善真实有用服务。现在的四请求 single-outstanding closed loop 没有 native 跨会话竞争，坏长流又同时有原模型质量失败，二者均不足以直接支撑“公平准入控制器”。核心 Qwen 的多会话研究是真实的，但不能自动代替 native admission 的证据。

| 新证据状况 | 资源研究的边际价值 | 本篇建议 |
|---|---|---|
| resident 两策略可用，Full-call 的收益可复现，未见明确干扰 | 当前主线已获得更可信应用合同；新增 controller 不能修补一个已观察缺口 | 不加；用一段 discussion 说明资格与新开工值得性不同 |
| resident 出现时延/能耗损失，尚未分离同步日志、IPC、warmup、模型状态与实际竞争 | 直接设计 admission 易把编排缺陷包装成策略贡献 | 先做同输入/重复/合法 oracle 与关键路径定位，沿既定工程门处理 |
| final 有真实收益，且固定同到达/同输入的 shared-resource 场景显示 conditional work 阻塞必需工作 | 有机会直接提高应用意义，并解释“合法可用不等于应继续扩张” | 若范围有限，可加一个固定预算/固定并发上限对照和一个小 panel；不要求立刻发明自适应算法 |
| 需要新多租户生命周期、开放到达、负载预测、动态预算、公平性目标才能得到正结果 | 新问题的目标、对照与失败边界会占据整段方法和评估 | 先形成独立研究合同；不把本篇变成 retention+recovery+scheduler 三个中心 |
| resident 无可用服务，或 final Full-call 相比 final Conservative 已失去强机会 | admission 未证明能修复主要问题；可能只在坏任务上降低浪费 | 不能靠再添机制制造成功。保留 NO-GO/受限结论，重新判断 native 部分主张 |

若真的进入第三行，最小有判别力的问题应当是：“在预先固定的有限争用负载下，限制**新**条件调用能否保护必需选定工作的期限，同时保留已经得到支持的 whole views？”对照至少包含 Conservative、现有 Full-call、同 Full-call 加固定资源上限；固定总资源、到达、source、max-ahead/义务及请求终点，报告实际 Consumer D/C、全 offered credit、每请求完成和物理 drain 的 work/energy。这个实验只支持指定负载上的干扰与干预，不自动支持公平性或生产容量。若加进正文，应替换一部分次要 K 细节，而不是再追加一整节控制理论。

## 5. 11 页应讲一条因果线

页预算按父任务指定的 11 页技术正文目标规划；本文不重新断言会议官方页限或 references 是否计入。最终规则由主任务按已核验 CFP 处理。

| 内容 | 页额度 | 读者读完应回答的问题 |
|---|---:|---|
| Abstract + Introduction + 实际短区间 | 1.10 | 什么服务问题被常用 first-delivery 指标漏掉？ |
| Feedback contract 与三个生命周期 | 1.00 | 为什么输入、选择、视图、物理退出不是同一判断？ |
| 两个见证及 native 完整调用映射 | 1.20 | 什么条件足以继续算、什么条件足以继续显示？ |
| 统一协议与 selected-trace argument | 0.95 | 原 selected 任务、durability、authority 如何保持？ |
| Evaluation design、比较对象与端点 | 0.65 | 独立样本和原 offered 分母是什么？ |
| 主 R×S 结果 | 1.10 | 联合协调是否改变实际可持续进度？ |
| 48 个 operating workloads 与负中点 | 0.95 | 何时有效、first delivery 与持续可用性如何不同？ |
| 最终 native paired + resident（条件成立时） | 1.15 | 原始 C/U 下是否存在可用服务机会，最终工程成本多大？ |
| Fault / buffer 正负控与实际恢复 | 0.95 | 已有资格能否跨具体故障交错保留，付出何种恢复代价？ |
| No-reset state stress 与输入确认分层 | 0.65 | 状态压力下什么仍正确、什么已不可用？ |
| Related work + 主要限制 | 0.95 | 组合增量与已知工具的边界在哪里？ |
| Conclusion + 必要披露 | 0.25 | 读者最后应记住哪一个结果？ |
| 合计 | 11.00 | |

这是空间优先级，不要求各段机械从新页开始。叙事顺序应为“观察到的损失 → 非等价判断 → 可执行组合 → 因子识别 → 原任务 native 机会 → 故障与压力边界”。不要按实验日期逐轮复述，也不要把这篇变成几十项 gate 的清单。

### 建议保留四图三表

1. **Fig. 1：已准时交付的完整区间消失。** 保留实际 1.444/1.544/3.720 秒与 2.176 秒洞、原 D2 读点；用矮幅跨栏图。Caption 明确该例来自 c16、不是成对反事实、不代表自然发生率。它承担“为何研究这个问题”，无需再放一张相似 toy timeline。
2. **Fig. 2：统一见证与身份图。** 由现 protocol 图改成一条完整输入调用链，标出 eligibility、原 C/U selection、whole-view application 三条检查边；旁列 physical lease/producer death，不让 WAL/fsync 细节盖住新组合。图中 typed identity projection 与 complete original result 必须不同。原大协议细节放 artifact。
3. **Fig. 3：保留现 service-region，但让 continuity 可一眼看见。** 保留全部四 workloads 和三个重复，包括负 c12；主 panels 为原 first credit、D99、timely compatible-loss deficit。不要只展示收益最大的 c16；不要将会话数当纯容量横轴。核心 24-speaker 精确数由 Table 1 承担，避免再复制一张 headline 柱图。
4. **Fig. 4：最终 native 应用机会与成本。** paired 完成后画 source/repeat 的真实 paired D99 与 credit，bdfa 和 4f 显式分开，并标 D2、EOS miss；不能把 32 次当 32 独立样本。若 resident 通过，再增加同模型 PID 下四独立 EOS 请求的 request-local D/C 与切换轨迹；若失败，panel 如实展示失败或改为简短边界，不能填预测值。

表格选择：

- **Table 1：headline R×S 五臂表。** 保留 credit、withdrawals、D99、board-energy；完整正控保留一行并清楚定性。文字同时给 +3.73 pp、0 audio-frontier withdrawals、569 erased characters 和 whole-run D2 失败，避免用零撤回偷换文字单调。
- **Table 2：native/fault 的紧凑 dependability 结果。** 用预定 six short fault conditions 的两策略结果，保留完成、非法安装/局部拒绝、old-fact replay 与 new-result latency、D2/C8；不能只给 recovery-ready。已完成 buffer 若通过，以独立 `controlled completed-buffer` 行/小块展示 2 positives + 2 negatives，标明 timing fixture，不能与自然样本池化。完整逐格表归 artifact。
- **Table 3：适用边界分层。** 正常短流 40/57、故障 58/90、两长流 96/924 与 166/830；分别给 durable/Consumer-used。紧邻文字解释 360 confirmed → 354 durable/used、352 original-Owner install、2 recovery-first uses。长流 D/C 与 CER 失败同块写清。若空间确实不足，四行小表改为一段精确正文，不能改回混合“18.94% 成功率”。

不建议增加泛泛的 prior-art 勾叉表：对 SSBD/PredGen/Adapton 没有运行完整系统，缺项叉号容易制造过强排他主张。用三段功能定位与具体合同差异，比凑“本系统全勾”更可信。

### 压缩和移出正文的内容

- K 物理释放保留一个机制段和一个服务后果句；其 24-run 全展开、所有阈值及全部能耗差移 artifact。它有真实证据，但不是这篇主中心。
- 旧 bdfa 的 8/8 留一句清楚历史身份；如果新 paired 完成，则正文 native 主表/主图以共同条件最终实现为准，旧能耗表不与新终点混拼。
- 725 hashes、725 输入审计流程、全部 freeze SHA、manifest、完整受控时序和 formal state 数放可追溯附录/证据包；正文给每类方法与身份，不用审计细节代替科学解释。
- selected-trace argument 保留约半页充分条件与归纳，不把 live-view property、floating-point rerun agreement 和 selected projection 合成一个“大定理”。
- 原自然率、stress coverage、deterministic property 用各自一处定义固定，后面靠精确主语表达；避免每句都重复一长串免责声明。

## 6. 可直接采用的主张结构与文字选择

摘要应优先出现“computation retention alone can worsen delivered-progress withdrawal”，再出现两个见证和主结果；不应以恢复工程开头。native 的最终结论待新结果填入。当前摘要里旧独立确认的 all-eight 句必须保持 bdfa 身份，最终版可用共同条件 paired 结论替换，不能语义上让读者以为最终 4f 达到旧 8/8。

三贡献可收拢为：

1. 一个针对原始递归反馈任务的契约，分别定义完整调用资格、原选择权和 whole-view 支持；给出两个可执行充分见证及选定史保持条件。
2. 将这些见证组合进实际异步执行/消费/持久化/受支持 fail-stop 生命周期，同时保持已有原语归属和原 C/U 行为。
3. 通过因子控制识别“复用工作仍丢交付进度”的服务缺口，并在明确来源、负载、最终实现和故障边界下测量收益与代价。

建议中心英文段落（不依赖待运行成功）：

> A trusted feedback revision changes several decisions at once: whether an executed call still has a valid input, whether its result may extend the selected state, and whether the Consumer may retain its current whole hypothesis. RevTrace checks these decisions separately and coordinates their outcomes. In the predeclared 24-speaker stratum, retaining computation alone increases observed frontier withdrawals from 12 to 17, while joint computation and whole-view retention yields zero. The selected feedback histories remain unchanged. This identifies sustained availability of supported delivered progress as a service property that first-delivery deadlines alone do not capture.

将“保护进度”写成 supported whole views 在 compatible application 下的条件性质，读者就能理解为什么 569 erased characters、1118 necessary incompatible withdrawals 和 joint 零 compatible withdrawal 可以并存。将 deadline credit 当支持性收益而非唯一贡献，可以承受负 interaction repeat，不需要所有指标和所有基线都输。

## 7. 剩余结果的条件决策树

| 结果分支 | 科学解释 | 下一步与正文决定 |
|---|---|---|
| paired 32/32 完成，语义均通过，final Full-call 维持清楚服务机会 | 组合的 native 价值在最终工程中仍成立；具体 EOS 代价有边界 | 发布完整 paired 结果；以 final 数据写 native 主结论。若只剩 S0908 EOS miss，就写实际 passes/credit 和原因未识别，不能硬调期限 |
| paired 有可重复额外延迟/credit 损失，完整 state/C/U 一致 | 性能或工程开销需要归因，尚不是语义假设失败 | 依预写门做同输入、重复、合法 oracle 和关键路径定位。只在仍有强 E2E 机会时新 freeze 局部修复并公平重测；不加新 scheduler 掩盖 |
| paired 改变原 state/C/U/IDs，或出现非法安装 | 当前 final native claim 被阻断 | 先分离代码、数值/模型与合同机制；冻结负结果。不能让 core 历史成功替 final 宣告通过 |
| resident 两 fresh pairs 语义/时钟/PID/完整义务全过，两策略可用且 Full-call 仍有实际收益 | 最弱轴得到直接补强：存在驻留模型、独立 EOS 请求的可用有限应用 | 把 resident 作为主 native 应用证据；保留单 outstanding、有限预注册、文件 EOS 定义，不升格开放到达吞吐 |
| resident 语义正确，但两臂都不可用或 Full-call 没有实质机会 | 常驻并未自动扩大服务价值 | resident NO-GO/阴性保留；核心贡献仍成立，native 只支持短链机会，竞争力的应用广度缺口仍在。停止在本合同内按来源/间隔搜索好看结果 |
| resident 失败源于可定位编排/计时错误 | harness 无效，尚不能对机制下结论 | 在新冻结身份下修正并按原队列重测；不改原 NN 核心来迎合新合同 |
| buffer 两正安装/消费、两负不安装，身份/exit/CUDA/channel/fence 全满足 | 关键跨 death 交错获得真实 NN 见证；authority 与已接收资格的分离闭合 | 作为机制与故障覆盖加入，继续报告实际服务延迟；不声称 buffer retention 带来 fault-time SLO |
| buffer 正控不安装，或负控安装 | 前者需分离 fixture 时序失败与保留机制失败；后者是必须处理的 safety failure | 先核实际前提，再走同输入/重复/原合法 oracle。失败未解时撤回 complete-buffer survival claim；已有 consumed-view survival 的 4 项不被偷换成该证据 |
| paired/resident 都好，但 buffer 只有已知视图存活、无完整 buffer 见证 | 主服务贡献仍可站立，稀有 fault claim 不够完整 | 用已证的 view survival 和合法选定史收窄论文，不为补全 checklist 无限加故障种类 |

最终选择应看证据组合，而不是要求每项都是正结果。若 paired + resident 产生明确可用合同，buffer 正负控闭合，则主线完整且应用意义明显增强；若 resident 阴性但 paired 仍有机会，论文仍有连贯贡献，应用范围必须更窄；若 final 已无端到端机会，则本轮不能把旧 bdfa 的强结果转贴成最终系统的成熟服务承诺。

## 8. 本审查的依据与边界

直接阅读：`AGENTS.md`；本轮 `README.zh.md`、`CLAIM_EVIDENCE_PLAN_20261031.zh.md`、`ACTUAL_PAIRING_AND_BOUNDARY_FINDINGS_v2.zh.md`、`TARGETED_PRIOR_ART_AND_CLAIM_REVIEW_20261031.zh.md`、paired/resident 与 buffer 设计；工作稿 `main.tex`、全部 sections 和图表清单。当前 paired 数字只读本地 `PAIRED_POLL_v2_1793434686191349800.json` 并核对四组计数和 408 个参考 steps；没有再读 NN raw 或访问机器。先例定位沿用已完成的定向原文核验报告，本审查不声称新增或穷尽检索。

历史 memory 仅用于延续“真实服务与恢复子指标分开”的研究边界；上述当前数值均由本轮本地材料复核，未用历史记忆替代当前结果。本文是独立判断和具体修改建议，尚未实施论文修改，不构成任何待运行实验 PASS。

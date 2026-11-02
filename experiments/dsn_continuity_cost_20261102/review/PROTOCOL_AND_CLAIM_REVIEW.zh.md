# 持续覆盖与完整协调成本：独立语义和主张审查

日期：2026-11-02。审查ID：`REVTRACE-DSN-CONTINUITY-COST-REVIEW-20261102`。

这是对实验设计的独立审查，不是新实验结果。已读当前release v9的引言、合同/保留/精化/评估/故障与边界段，上一轮`DSN_EVIDENCE_OPPORTUNITY_REPORT.zh.md`、`PROTOCOL_COST_AUDIT.md`的历史S段、S_DECISION及实际historical/当前Consumer实现。未运行模型、证明、trace reader；未修改论文、原数据或CURRENT。已与本轮历史分析和成本实现agent交换具体审查建议。

## 1. 总判断与值得检验的新问题

当前主线可以继续增强，无需因为普通index或Alternative joint同效就否定组合创新。但必须区分两种性质：

1. v9当前[S]：**眼前这个完整view在新root下仍合法，就保留它**。这是`03_continuation.tex:77`的per-application命题。
2. 本轮新假设：**眼前view失效或不存在时，是否仍有一个已合法登记、未被撤权的历史view可供使用，却因为只看latest而未显示？** 这是在已知可用证据集合中的选择完整性；它比保住current-view更强，并不等于发明索引算法。

研究价值取决于第二种性质是否产生**非零持续可见区间**、是否保持完整text/authority/原始输入义务，以及实现代价是否值得。先量化当前问题，结果再决定是否接入新在线策略；不以旧“首次D2信用为0”直接判死，也不先把14个时点改称14段受益窗口。

代码依据：`legal_progress_20261026/final_source_v2/runtime/src/revtrace/historical_display.py`的`_select/consume/kernel_private_support`枚举Consumer已登记tip，并联合native/core支持；当前core `physical_retirement_20261028/source_v3/runtime/src/revtrace/certified_display.py`只检查`tentative`。收到不兼容private publication时，后者先登记nodes再清当前view；因而历史选择也可能由**Private publication**触发，不只由Canonical安装触发。新结果必须按trigger kind分层。

## 2. 持续覆盖分析必须维持的语义

|检查对象|接受的处理|拒绝的处理|
|---|---|---|
|可用时点|原FIFO Consumer接收/处理顺序；保持原`observed_perf`与同时间原sequence|将GPU完成、Owner收到、未发布host结果提前当作Consumer候选；用快速CPU重放的新时间计算旧服务空窗|
|结果身份|原job、完整P/Z/text、session、contract/epoch/generation、原publication身份全部绑定|重新渲染到不同parent后当原结果；用相同text替代原节点身份；新owner给旧job重签|
|实际权限|每次root、mode、epoch或明确revocation变化后重新检查完整支持|从CERTIFIED-ONLY/RECOVERY回NORMAL就复活已撤权generation；把missing/ambiguous path当兼容|
|未知与失配|unknown单列；只有同frontier完整input实际失配才是refuted|因祖先失配就宣布所有未来输入非法；或把尚未反证当作可直接显示的完整资格|
|保留对象|完整whole hypothesis；Canonical lane仍只由原可信选择推进|拼接未认证suffix、历史preview推进认证frontier、拿全run最终text补齐中间视图|
|必要修订|支持被反证/显式fence时允许且记录withdrawal|为了曲线单调保留不合法view；把所有文字修改/必要回撤都叫avoidable loss|
|候选比较|同一已登记集合、同一完整支持谓词；scan与index用同tie规则|index额外使用未来root/离线正确性标签，或latest少付检查后仍宣称同保证成本|
|EOS与原时钟|每个原offered interval，包括partial EOS，使用原ready/ORIGIN；ACK/recovery不重置|只枚举完整2s网格；用ACK作新release；丢掉失败/unfinished/range不齐attempt|
|结束时点|最后一个实际同source观察后右删失，完整可观察段积分|任意延长到进程退出/下次任务/假想稳态，使尾部面积增大|

`HistoricalEnvelopeView._select`的既有排序是`(audio_end_sample,display_revision,job_id)`。主分析应复现这个规则，避免测试中途新引入tie改进。另报告同F多个合法不同text候选的数量；若研究stable tie，另列敏感性控制。最大frontier并不保证最少字符改动。

**不可跳过的复现门**：在同一原事件流上，latest/two-register必须重现原Consumer的visible frontier、whole text、mode/root及原身份。此门失败意味着reader/clock/合同尚未对齐，不能先展示scan的正面积。保留原attempt失败/缺失/unknown数量与原因，不把只有完整正例的三个attempt当全部样本。

## 3. 指标建议：先定义可观察对象，再给面积

令`E(t)`为时刻t Consumer已经登记且仍具有完整权限/支持的候选集合；Canonical snapshot也是合法服务候选。定义`F*(t)=max(F_C(t), max_{h∈E(t)}F_h)`，`F_p(t)`为策略p的**合法**实际覆盖。若整view确为从起点连续覆盖，可报告：

`B_p = ∫ max(0,F*(t)−F_p(t))/sample_rate dt`，单位audio-s×wall-s。

该指标是固定历史/时序下的**available-evidence coverage deficit**；不能命名为部署goodput、自然故障率或用户正确文字损失。若adapter frontier不表示连续区间覆盖，应按原offered interval逐个计算，而不直接拿两个frontier相减。

推荐同时报告以下五组，不让一个大面积替代全部服务性质：

1. **机会与持续区间**：全部Canonical/Private/mode触发数；候选数量；distinct candidate jobs、sources、合并后episodes；episodes长度/最长值、右删失数。14point cuts若来自同一段，应合并而非相加。
2. **受益类型**：A曾实际显示的同节点覆盖被恢复；B旧publication曾登记但此前未合法显示，现在首次可用；C当前view直接保留；D没有合法候选/必须撤回。A和B均可能有服务意义，但不能统称“恢复用户已看过的内容”。
3. **原期限分类**：原first D2 pass/fail、原C8 pass/fail、完整grid/partial EOS各列；已获首次信用不得再次增加。若partial-EOS显示出新的潜在first credit，应明确旧scope与新scope，而非宣布旧结果错误。
4. **完整内容代价**：恢复/切换的whole text与原节点一致；按实际view transition计inserted/erased code-point occurrences和同F文本变化；raw及固定normalizer后的same-F selected-text支持，unknown单列。原task CER/WER与这些量分开。
5. **成本与下界**：实测完整选择/申请/应用路径成本；保留原时轴零新增处理延迟的结果作为机制机会。不得直接从audio-s×wall-s面积减CPU毫秒，二者维度不同。若评估成本后收益，需要明确改变apply时刻/队列的延迟模型并报告敏感性，或先并列报告机会时长与操作成本。

**原事件流冻结的限制**：scan改变Consumer ACK，真实在线系统可能改变后续dispatch、batch与model inputs。所以离线积分即使严格正，也只证明“现有结果与权限下可以选择更多持续覆盖”，不证明在线端到端提升相同。在线确认若有意义，应保留相同原选择程序、原deadline/完整输出合同和完整Standard同能力，并实际记录Consumer应用/资源成本。

## 4. 成本实验应测哪些对象

主对象应是当前冻结NN4f的完整协议路径，不是把旧101μs组件数换标签。建议分层列以下真实操作类别，按触发/复杂度各给样本数、wall与thread/process CPU；并报告没有落入span的时间：

|层|应该包括|必须分开的时钟/前提|
|---|---|---|
|冻结输入/EL|完整输入序列化、identity/hash、实际注册、dependency comparison、UNKNOWN/CONFIRMED/REFUTED决策|dispatch前等待与纯检查CPU分开；不能把原C/U推理移到免费oracle|
|AU与receipt|原完整C/U结果及selected correction/IDs绑定、Owner/session/worker身份、complete/buffer/late/duplicate判定|已接受closed receipt与新fenced消息分开；不要按一次普通完成代表异常路径|
|安装与持久性|FactStore frame构造/校验、write/sync、parent/next绑定、installation|wall含阻塞；threadCPU不含磁盘等待；同一group fsync只收费一次；recovery replay不是新selection|
|SUP/实际Consumer|immutable publication copy、FIFO接收、registered ancestry、whole-view guard、实际apply/ACK、字符/metric观察|publish≠apply；Owner wall、Consumer CPU与排队分别记录；跨线程inclusive wall不能相加为关键路径|
|生命周期|物理terminal/drain确认、incarnation/fence、closed buffer保留、原输入债务/时钟|logical cancel/ACK不能替代physical release；native model work与protocol host work分列|
|控制历史|live/pinned closure、历史节点/diagnostic class大小、序列化和copy成本|short正常与long state stress分层；不能以最多64个unpinned项代表全部state/context/RSS恒定|

代表性至少覆盖normal、compatible view、necessary withdrawal、duplicate/late局部拒绝、accepted closed buffer、Owner recovery；缺某类就标not observed，不用大量normal操作替代。历史完整trace重放可提供对象覆盖和实现resource footprint，但不是新serving。

计时的`inclusive`只作为包围范围；互相嵌套的EL/identity/hash/commit不能相加。processCPU已包含所在线程CPU，二者也不能相加。记录日志写出、capture/extra validation和计时汇总的位置；若在service window中，就进入观测开销；若在window外，仍报告额外资源，不能无声消失。

## 5. 什么能称为哪种成本

|比较对象|可接受名称/主张|不可接受名称/主张|
|---|---|---|
|当前真实完整对象/trace，功能路径不变，只量各层span|current protocol resource footprint / 完整对象的协调路径成本|端到端“完整协议税”，因为没有可执行counterfactual baseline|
|同当前安全谓词/模型/资源/WAL/Consumer，关闭额外timer/capture vs开启|instrumentation overhead / 观测开销；真实配对可报告其end-to-end影响|协议安全成本；两臂都执行协议，差的是观测器|
|同安全语义，优化前后实现，原完整input/output/selectedtask均核对|implementation cost reduction / 实现代价与服务tradeoff|移除安全检查带来的合法加速；通用零开销|
|当前NN4f vs旧bdfa，已知还改变transport、fault handling、logging等|total reliability-extension cost，附功能差异矩阵|单独EL/AU/SUP税、纯WAL/安全税、单因素因果|
|CPU禁用guard但不向任何Consumer/Canonical发布|CPU归因负控或hypothetical lower path cost|合法服务baseline、可部署性能|
|与完整Alternative joint实现比较，得到相近结果/成本|独立实现确认相同义务可实现；组合设计可移植性|据此一票否定组合创新，或反向宣称RevTrace唯一能实现|

真实off/on观测配对仍需检验：原offered/EOS及ORIGIN→actual physical-model-drain窗口、完整原C/U选择历史、actualConsumer/withdrawal、physicalcall/batch/inference数量、paid abandoned work、两板能量。若capture改变schedule/batching/inputs，端点差异仍是**观测器的总系统影响**；不能只称固定host执行的纯CPU tax。两来源×两策略×off/on×两fresh若执行，独立声学样本是2，不是16；方法顺序/角色应在pair中平衡，raw与失败全部保留。

## 6. 结果到主张的预先映射

|得到的结果|本轮可接受结论|写稿动作|
|---|---|---|
|历史14点在原Consumer时轴下只有瞬时差/同一view反复计数、或没有权限|当前scan改进是point-cut结构回归，不是持续服务收益|保留artifact反例；主文不增加“历史恢复服务”贡献|
|历史N5有非零持续缺口，当前bank为0|现有latest策略在某合同缺少已登记进展选择完整性；当前bank未测到残余|可加Discussion/附录，不把旧合同正例改写为当前native验证|
|历史和当前bank都有非零、可重复合法缺口，内容/成本边界通过|支持将S从current preservation增强为registered historical selection；仍先称固定历史机会|冻结最小在线latest/scan/index确认；只在实际结果后决定主文提升|
|scan/index同效且均优于latest|组合义务更完整、普通多版本组件可实现；无需独占索引算法|以明确性质/接口与真实服务解释创新，不靠算法名|
|面积改善但字符反复修改、whole-text支持更差或代价大于窗口|frontier availability有tradeoff，不能宣称全面用户体验改善|保留双指标，可能只作可选择策略/边界|
|当前协议span成本可测，off/on影响小，端点/任务一致|当前完整实现的cost footprint及可控观测影响|补一张简洁成本图/表，替代旧101μs宣传；不提升为零开销|
|观测off/on导致deadline/energy显著变化|instrumentation是系统成本的一部分，论文运行配置需明确|报告实际差及service margin，不能将观测off最佳端点与on最全证据拼成同一run|
|持久性/receiver等单路径优化有稳定收益且同保证|有意义系统工程强化，可作为协调可部署的支撑|据最终source/diff描述；不另造与中心竞争的新贡献|

## 7. 对novelty与DSN叙事的独立意见

最有价值的潜在增量不是“多一种index”或“又多一个安全guard”，而是把**拒绝非法状态**与**充分利用已经合法可用的结果**组织成可执行、可测的双义务。在递归可信反馈中，current-view不合法并不意味着所有历史结果都不合法；计算完成、消息权限、整视图支持和物理生命周期又不同时结束。若本轮实测连上持续可用性与成本，就能把现有R×S从配置组合进一步写成更完整的服务契约。

但名字必须由结果决定。当前v9的先前compatible-view保留命题本身正确，不应为新机会把它说成错误；registered maxlegal只是更强的可选性质。只有旧14点而无当前服务结果时，不宜改题目/摘要去许诺最大全局进展或恢复覆盖。已有核心2×2与native full-call仍是主证据；本轮补的是性质完整性和实际代价，不必推倒重写。

此审查未使用外部近邻论文作首创/否定判断；没有将“普通组件可达到同效”当成组合创新无效的理由。文献定位应在确定最终对象与测量主张后核对一手原文，而非先选术语再寻找支持。

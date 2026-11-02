# v10之后的独立研究与编辑取舍

日期：2026-11-02。依据：用户附件`456255b6-f2da-485d-8991-1b52527d3703/已粘贴的文本.txt`全文、当前v10相关TeX、既有独立证据地图，以及本轮SGLang/Retire原文有关机制段。本文件是设计/写作审查；没有启动selection census、raw reader、模型或正式48run，也没有修改Paper_DSN。

## 1. 拍板：先做一个便宜的稳健性分析，再做一次真正增加独立来源的确认

附件最有价值的判断成立：当前缺口是**最强原生性能证据仍集中在四个旧说话人**，而不是缺少第四个机制。建议顺序如下：

1. 立即冻结已有final4f matched/resident的deadline sensitivity与每source配对分析；原D2/C8不变。这比继续抠文字有直接信息增量，且不增加神经调用。
2. 只有在metadata census证明可行后，冻结未用于开发、诊断、选择策略的新说话人确认；12×2policy×2fresh=48是合理预算，不是必须凑到的统计门槛。
3. 沿用final4f、原Correct/Update、两完整workers、原500ms与EOS、相同观察配置和原输入时钟。正式集不参与继续调参。新结果若支撑现有主张，用它替换旧四来源headline的主要证据位置；旧bank转为机制/重复一致性的支撑，不把两个bank混为新的独立样本。

主文仍只有一条消息：**可信反馈推进后，不同对象需要不同的保留/撤销判断，而合法提前计算必须兑现成实际服务。** 不重开max selector、KV/encoder新carrier、cancel原因竞赛、日志系统或通用Agent安全分支。

## 2. 来源选择：独立性比“12”更重要

### 2.1 必须先解决的真实容量问题

AISHELL-1原论文§4明确：train340、dev40、test20 speakers，三者不交叉。因此在扣除全部历史模型使用者后，**同test split是否还剩12个新speaker，不能假定**。[AISHELL-1原论文，PDF第3页§4](https://arxiv.org/pdf/1709.05522)

同split不足12时，合理决策是使用全部合格剩余新speaker完成较小确认，或另行冻结明确标记的跨split扩展并分层报告。不能静默放宽8–9s范围、换成同speaker的新clip，或临时跨split后仍称相同holdout分布。不存在“少于12就没有论文资格”的依据。

### 2.2 selection应遵守的区分

- 使用`corpus/split/speaker_id`命名空间，并交叉核对utterance ID、完整WAV/PCM SHA，防止文件改名或不同路径复用。
- 实际ASR/corrector/原reference/model操作使用，与metadata列举、下载、archive扫描、未执行candidate分开。只扫描过metadata不能自动称“已被模型使用”；反过来只查最终主表也会漏掉开发、故障、长流、stage/encoder、cost和reference使用。
- 每speaker只选一个完整8–9s原utterance；排序、seed及technical fallback规则在模型调用前冻结。以元数据/已知格式损坏排除，不以CER、速度、输入确认率、纠错是否相同或输出长度选样。
- 不拼接、不裁剪、不重复扩成满足时长；时长来自完整PCM frame count。保持当前短会话合同，duration只是既定研究范围，不把结果推广为任意时长。
- “未用于本项目的开发/评价”不等于“基础模型预训练未见”。后者本轮无法由manifest排重得到，正文只使用前一种明确表述。
- reference与正式运行同样计入该新source的真实模型使用。正式集合先冻结，再获取reference；不能依据reference表现替换来源。技术失败保留并诊断，不以期限/质量结果启动替补。

metadata census需要给root一张stage-aware排除表和完整剩余名单，才决定48run是否成立。已与selection agent交流上述要点；本审查未自行执行census。

## 3. 48run若可行：优先把性能比较做成真正配对

每source两policy×两fresh repeats。对同source，repeat0顺序AB或BA，repeat1必须相反；跨source第一顺序也要预声明平衡。GPU角色按repeat轮换且两policy共享。**先导出实际48行launch顺序并自动检查AB/BA，不只检查生成器里出现了reverse。** 上轮off/on的block reverse与parity抵消，不应重现于本轮主要性能比较。

沿用相同final4f观察/日志配置；没有必要再引入一次timer off/on轴。模型加载、原神经warmup、allocator、原selection与partial EOS处理一致，初始ready后开始原service clock，最终能量使用同一原origin→外部确认physical-model-drain窗口。两完整workers、单source会话的提前调用比较，不能换成同时开放12个source的容量实验。

只以身份、技术、语义、资源安全门决定是否暂时停止诊断；不以性能正负裁剪矩阵。所有原offered尾段、未完成/失败、quality和paid work保留。确认原任务需要真实原reference与完整state/C/IDs核对；不能把Conservative的输出免费称作独立original-engine reference。

### 统计单位和聚合

- 独立声学单位是新speaker数；48是运行数。每policy只有24次运行，不能写48次独立任务。
- 原D2/C8信用按全部offered音频权重汇总；另对每source先合两repeat，再给RevTrace−Conservative配对差。两种汇总主语不同，不能拿source等权CI装饰audio加权headline。
- Whole-run pass按每run原P99判定；`x/24`保留repeat的相关性。逐run P99中位数不等于将全部frontiers混池计算P99。
- 文字quality按唯一source reference计分，不把同一参考在两repeat/两policy重复为新reference内容。维持原whitespace-only CER与完整selected-task保真；首次whole-text同F支持另列。
- 12个speaker的paired differences比一个看似精密的transition-level p-value更有信息。可预声明source cluster bootstrap作为描述支持，但无需为了显著性加入额外统计。不能对一串deadline点择优挑一个显著结论。

## 4. Deadline sensitivity：回答阈值是否决定故事，而不是换标准

建议使用agent的冻结方案：`tau_d=0.5..6.0s`、步长0.25，`tau_c=8s`固定，同时导出event-exact CDF。主标准D2/C8、原6/8与7/8及全部EOS继续不变。函数为：

`Q_p(tau_d,8)=sum_i w_i·1[D_i<=tau_d and C_i<=8]/sum_i w_i`。

分母永远是全部offered，不以C8通过作为入选条件。缺失D/C为无穷，不能从曲线删掉；部分EOS按实际sample权重进入。matched与resident复用同四source，分bank展示；resident每request使用它自己的原origin，不把trial全局时钟套给后面请求。

每source先合两repeat，输出配对曲线/原值；总体曲线维持audio-weighted口径。四source min/max包络是描述范围，不能叫置信区间。图用经验阶梯而不是暗示新运行点的光滑拟合。若新的独立确认运行，沿用同一冻结grid和分析器，不再按新结果选择显示范围。

结果的可接受解释：若优势跨一段阈值保留，说明不是只有D2这一切点有用；若集中在D2附近，也应给出真实分布和每source结果，不能把放宽后的pass替换原headline。这一项可放现有native图的小面板/附图，不要求增加整张复杂机制图。

## 5. 把“确认→提前有用→已付但未用”接成一条论证

不要再增加一段独立“limitations”。在原生评估先给主服务结果，再用一个短机制段解释三个不同环节：

|环节|现有能用的证据|精确用途|
|---|---|---|
|输入确认使原调用仍可选|早期独立native bank：92个promoted calls中20个自身预测end被原C/U改变|输入确认不等于预测正确；原纠错/更新仍决定结果。不能改写为final4f新统计。|
|合法结果确实更早到达|当前final4f：whole first view在其自身G与后来selected text匹配的及时音频22.5→51.0s；resident24.0→50.259s|早到的是后来所选的同F完整内容；不是额外正确字符或人类准确性提升。|
|确认与实际使用有区别|原36trace诊断：normal40/57、fault58/90、long96/924与166/830；fault中只有52durable、50原Owner install、52consume|不同负载的机会结构；不能拿混合360/1901当生产确认率或用确认率唯一解释长流失败。|
|未使用工作仍付成本|真实完整/abandoned worker host intervals、actual physical drain与board energy；K24同输入输出后继批已有兑现链|以实际字段计费，不从job/token数推算GPU省时；host interval不是CUDA kernel时间。|

**最理想的新增整理**是从同一个新确认bank导出这条链：条件派发→输入确认→durable/actual Consumer使用→真正早于必要选定执行的服务贡献，并附未使用工作的已记录host/物理资源账。若现有日志不能直接识别关键路径，不把“提前开始”“被使用”“造成全部coverage收益”画成相等。

主文只需一句教训：**输入资格提供保留许可，实际就绪/消费时序决定它能否兑现服务，未使用的推测成本仍进入比较。** 不需要新增admission算法。旧long诊断可留artifact；新bank若没有同源paid-work完整字段，也不要把旧坏长流成本填进新表。

## 6. 近邻：具体已有机制与本稿不同问题

本轮用`nature-academic-search`的citation-verification路由；academic-search MCP不存在，直接读取一手出版PDF/arXiv，而非按旧笔记假定。既有BibTeX保留，无新引用数量任务。

### SGLang

实际读了NeurIPS2024正式PDF的§2异步stream、§3开头与§5（PDF第6–7页）、API实验相应短段。§5的对象是：首个API调用越过stop条件生成额外输出，解释器再把这些输出匹配到后续程序原语；它的确是跨调用推测，不能仅称KV缓存。[SGLang正式论文](https://proceedings.neurips.cc/paper_files/paper/2024/file/724be4472168f31ba1c9ac630f15dec8-Paper-Conference.pdf)

本稿可具体强调完整原recognizer–corrector调用在真实父反馈未定时已执行；其完整输入后来被确认，结果仍由原C/U决定，实际whole view另验支持。这是**复用对象与服务判断的区别**，不是“别人只会token、不能调用函数”，也不是断言SGLang无法作为实现底座。没有阅读/移植其全部当前GitHub实现，不由论文API缺项推导不可能。

### Retire

实际读了本稿引用v1的§3.1、§4–§6.1与相关图注。其runtime先给出`SUPERSEDE(scope,epoch,revised context,contract)`；server协调新旧epoch权限、safe-point/writer closure、完成KV前缀匹配及ownership generation检查，后继运行时异步回收旧资源。它同时处理拒绝与保留，远强于“父版本一变全取消”。[Retire v1原文](https://arxiv.org/html/2610.01160v1)

本稿的具体增量在**如何从原selected反馈推导各对象的不同动作**：旧显示路径失去支持，未来完整输入仍可能UNKNOWN；已拥有完整结果不因producer退出自动失效；输入确认不替代原选择。Retire可接收客户端推导的scope/contract决策，因此不能称它理论上不能实现这些动作。parent-cancel不是其完整复现。当前稿不需移植两套大系统来证实一个“经典组合必败”的错误命题。

## 7. 紧凑写稿选择

- 新source确认若完成并有信息增量，**替换**旧四source主表位置；不要再给main叠一个独立“更多模型/更多数据”贡献。
- native既有内容图保留“同内容更早”作用；deadline曲线可做紧凑面板或artifact，按结果是否改变读者判断选其一。
- 机制段以确认许可、实际就绪/消费、已付工作三件事闭环，不新增长流限制段。
- Related Work只补SGLang/Retire各一两句对象/决策边界，与方法案例对应；现稿大方向已经正确，不重复大矩阵或扩大免责声明。
- H、M、250k、旧微秒/V100继续artifact。正文只放直接增强当前主张的结果。新结果尚未产生，不能提前写“12speaker均通过”或增大摘要数字。

附带紧凑TeX建议见`COMPACT_TEX_PROPOSAL.tex`。所有新增数字插入位在正式结果前保持注释；root完成元数据可行性、冻结执行与独立验证后再决定采用。

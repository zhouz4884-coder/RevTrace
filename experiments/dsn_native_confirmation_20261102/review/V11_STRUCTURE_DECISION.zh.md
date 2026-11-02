# v11原生证据的结构取舍

日期2026-11-02。只读当前v11的native、operating、fault、cost、Discussion与main入口，并核对已完成四source敏感性CSV。未改Paper、已冻参考/driver或CURRENT；未读进行中的32run效果。新8source参考8/141连续及282恢复步骤已通过，正式服务效果仍不预填。

## 1. 核心判断

v11可以吸收新8speaker确认而不加新章节、机制或第5张图。最有价值的变化是**把主要原生服务结论从四个已使用来源推进到严格独立的新来源**，同时保留旧bank中最直观的机制与实际内容证据。它应替换/重排现有内容，不成为“又做了一个实验”的目录项。

当前native节已经涵盖设置、旧主表、保真、能耗/EOS、residency、敏感性、内容和输入/视图机制，顺序略像逐批汇报。建议改成：**独立确认的主服务结果→任务保真与成本→同内容更早/机制解释→resident部署形式→简短敏感性**。不增加一段long/admission防御。

## 2. 一张分层表承接旧4与新8，不池化

Root计划的old4/new8合并表可行：每cohort两policy，共4行，沿用`tab:native_full_confirm`。headline是否换新8，等待全部运行及原任务/实际Consumer/资源/统计gate闭合后再决定。

|位置|建议处理|保留的主语|
|---|---|---|
|native开头第一段/主表|在同一表内标明“Matched: 4 previously measured speakers”和“Independent: 8 new speakers”；每cohort各自比较两policy|旧4每policy8runs；新8计划每policy16runs，不能将32叫独立speaker数|
|Task fidelity段|合并来源冻结、固定2完整workers/FP32/原500ms/EOS、原C/U/complete-state/ID保持；新reference严格4f，旧静态marker映射细节进artifact|reference工作单列，不成为serving性能或额外声学样本|
|Energy and EOS段|缩为表后两句，按最终实际new8结果解释相同服务窗口的能耗/期限；旧S0908两个EOS失败仍由旧表/旧数据保留，不把它们写成新8失败|不要沿用旧6.52%为新cohort结果|
|The same content arrives earlier段与Fig4|若新8完成同G后验内容重计，可换matched面板；否则继续明确旧4matched/resident并作机制支持|22.5→51.0、180/14/166、106/136与104/136均属旧bank，不搬给新8|
|Input confirmation段|提前保留20/92的一句反直觉机制，与“输入确认不选定预测结果”对应；其余24停ASR/2wrong-input、旧保真计数移artifact或压缩|明确early independent bank；不是final4f新8输入命中率|
|Resident段|保留一小段说明模型只加载一次、PIDs跨4request持续、每request原clock；旧0/8→7/8可在一句中保留|它验证residency，不增加独立speaker数，也不与新8fresh trials合池|

不同cohort的offered总音频不同。合并表如保留energy totals，caption要明确各cohort独立分母、只做cohort内比较；更易读的可选写法是GPUJ/offered-audio-s，窗口仍是相同原origin→外部确认physical model drain。不要让新8较大的总kJ被误读成更差效率。

来源数、运行数、参考调用与选定转移在一处说明即可。没有必要在开头、表注、保真段和节尾四次重复完整计量纪律；原全offered/EOS/P99规则保留在设置，表注只给本表的cohort分母和聚合。

## 3. 四source敏感性正文一段足够，不增第5图

当前v11这一段已准确且有信息增量：C8固定，0.5–6s预声明display budget、保留EOS；1.5s下matched36.2%→84.0%、resident36.2%→78.7%；D2时两bank各四source配对差均正。

本次只读CSV校核：两个bank在该固定grid均无负的总体覆盖差；matched严格正点从0.5至5.5s，resident从0.5至5.75s；6s均为100%。这些支持现句“优势跨较紧期限，时间压力减小时收敛”，不用再加曲线大图或把较松期限的pass写成新headline。原D2/C8规则与6/8、7/8保持。

新8结果进入后，这一段可留在native节末，明确它重计旧matched/resident。若之后沿同冻结grid整理新8，只需替换为新的独立确认敏感性结论；不必同时保留三套预算曲线。完整阶梯曲线、每source曲线及repeat范围留artifact。当前四张图已经各自有清楚任务，添加第5张的收益小于它对篇幅和注意力的占用。

## 4. 确认、兑现与成本用一个机制段连接

建议紧接主表/内容图后用约70–90词解释：输入确认使旧调用仍可选，原Correct/Update仍可改变它的自身预测；有用收益取决于完整结果赶上实际Consumer的服务窗口；所有已发工作，包括未使用结果，仍在执行/能量账中。它自然接到已有protocol-path cost表，不另起资源调度贡献。

不要把不同bank的“确认率70.2%”“及时matching内容”“未使用work秒数”拟合成一条通用因果规律。新8若有同源完整字段，可以用新bank短链加强；否则用版本清楚的既有20/92与旧内容图说明机制，paid work说明与真实窗口费用对应即可。

可供root取用的紧凑文字骨架（结果槽不预填）：

```latex
Input confirmation permits retention while original Correct/Update still
determines the result. In the earlier independent bank, it changes 20 of
92 promoted calls' own predicted ends. The service benefit comes when
eligible complete results reach the actual Consumer sooner; issued work
that is not used remains included in the measured execution and energy.
```

后续新8若总体/分source结果没有增强外推，应按实际结果收窄性能范围，完整study保留artifact；不从32run内部选择更好speaker/repeat重建headline。主贡献仍由R×S机制与原任务保持支撑，不要求新cohort每个点都绿。

## 5. Discussion与c12的精简决定

**赞成移出Eligibility/resource-admission整段负控制。** 它提出另一个研究问题且主要讲未建立的penalty，容易分散“合法保留如何兑现服务”。在Service/capacity只留一句即可，同时保留SEDA的实质引用：

```latex
Input eligibility permits retention; queue-based resource admission
governs when to launch more work~\cite{welsh2001seda}.
```

**赞成把c12 strong-witness未建立的技术句移artifact。** 正文已有c12的0/12、D99和实际timely-loss counts，足以说明工作区间；不需要再插一个“还没找到更强案例”的防御句。保持窗口口径含EOS（全offered设置已说明），不要把c12的较小EOS loss当成Fig1完整非EOS区间强见证。

其余当前结论无需扩大：保留whole-view与dependency/human accuracy的定义、原必要修订和实际故障冷恢复数据；不把H/M/更多旧counts加回main。新8确认、简短deadline稳健性和当前真实协议路径费用，已经围绕同一服务主张形成足够紧凑的闭环。

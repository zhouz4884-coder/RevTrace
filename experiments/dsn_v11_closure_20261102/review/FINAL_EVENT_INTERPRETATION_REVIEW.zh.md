# 最终事件解释独立复核

2026-11-02。只读本地 `analysis/FINAL`、`review/EVENT_CLAIMS.json`、v12 `sections/05_native_retention.tex`，并对照此前人工只读报告 `S0901_S0902_EVENT_REVIEW.zh.md`。没有重测、模型、remote/raw-reader重跑、源码/原数据/CURRENT/TeX修改，也没有新增方法或回归矩阵。

**结论：最终V3账目与此前六格人工事件一致，EVENT_CLAIMS的核心数字和v12解释成立。建议正文补一个小范围限定：“six late non-EOS replacements in each repeat”，使0.53–0.74s明确排除EOS。没有影响主结果或要求重跑的阻断事实。**

## 1. 被审证据与完整性

- 正式CPU源 `5c0ab42caa2401f9a59ff8e929bcd4ec9e52155f`，原NN依赖仍4f，未重贴runtime身份。
- SUMMARY状态 `PASS_COMPLETE32_RECORDED_TRACE_ACCOUNTING`；9formal controls无failure/error/skip。覆盖32格、564原offered端点、610条issued-job timeline及190条D2 miss timeline（含两策略）。
- 420原输入文件共182,255,325bytes前后不变；本地INPUT_HASHES_BEFORE/AFTER的文件SHA也相同，为9731cc82…。
- EVENT_CLAIMS绑定的SUMMARY、JOB_TIMELINES、MISS_TIMELINES、SOURCE_DEFICIT_LEDGER四个SHA与当前文件逐项一致。
- 原c4闭环仍为32格/564选定步PASS。V1空text/visible0处理缺口、V2的control alias、V3独立fixture属于分析版本修复，原失败版本和runtime保留；不能将它们写成v11运行时被修复。

## 2. 六个失败格逐项对照

以下均是RevTrace/fullcall原结果，未及时质量是audio-seconds，未因P99口径或EOS缩分母。

| 原格 | D2 miss / EOS | 原miss前沿 | 未及时audio-s | EOS实际view UID / publication |
|---|---:|---|---:|---|
|S0901 r0|1 /1|130209|0.1380625|e0-j000000018 /48|
|S0901 r1|2 /1|128000、130209|0.6380625|e0-j000000018 /48|
|S0902 r0|1 /1|137055|0.0659375|e0-j000000024 /52|
|S0902 r1|2 /1|136000、137055|0.5659375|e0-j000000024 /52|
|S0915 r0|7 /1|96000、104000、112000、120000、128000、136000、143969|3.4980625|e0-j000000026 /51|
|S0915 r1|7 /1|同r0|3.4980625|e0-j000000026 /51|

所有20条fullcall miss均为 `RECORDED_SAME_PRIVATE_JOB_PATH`，view_job_id等于对应job UID；owner epoch均0，未生成新birth或重授权身份。相同短UID必须连同cell_id使用。

S0915合计6.996125s，全部RevTrace未及时质量8.404125s：

`6.996125 /8.404125 =0.8324632249044368 =83.24632249%`。

SOURCE_DEFICIT_LEDGER、SUMMARY与EVENT_CLAIMS一致。v12写“6.996 of8.404 uncredited audio-s”准确；这是**全部RevTrace未及时音频的占比**，不是全部offered音频的83.25%。两repeat各七次且含六个完整非EOS区间，故不能归结为一个EOS小尾段。

## 3. 原UID、原时钟与人工记录一致

MISS_TIMELINES保留原perf_counter绝对时钟，以下EOS实际D、C与人工报告的六位相对时刻一致：

| EOS格 | 原D /s | 原C /s | publication receive→D /s |
|---|---:|---:|---:|
|S0901 r0|2.497231526|2.752944534|0.177807928|
|S0901 r1|2.635833302|2.836231819|0.187518098|
|S0902 r0|2.314062872|2.576467142|0.031524049|
|S0902 r1|2.825579238|3.103334189|0.041011401|
|S0915 r0|3.085665079|3.418742717|0.018858709|
|S0915 r1|3.084205000|3.416274713|0.041607258|

注意CSV的first_D_row_index是0-based；它的47/51/50分别对应人工报告的consumer.jsonl第48/52/51物理行，不能把索引差一误判为事件不一致。

S0901两个EOS j18的 `started_on_canonical=False`、promotion_count=1、actual_parent_full_state_equal=True；原派发在对应父install日志之前约0.519/0.528s，输入确认后仍使用原UID。S0902正确EOS j24则started_on_canonical=True，完整actual parent相等，派发晚于对应父install日志约5.170/4.907ms。它们分别支撑“保留匹配的在途EOS调用”和“完整输入反证后失去lookahead”，不能互换解释。

## 4. 0.53–0.74s的准确范围

EVENT_CLAIMS的 `six_replacements_each_repeat`准确对应每repeat的j15/17/19/21/23/25：目标前沿96000至136000，即6.0、6.5、7.0、7.5、8.0、8.5s。十二个调用均durable-selected且完整输入等于实际父状态。

其原infer host区间最小0.530869625s、最大0.740866979s；对应父install**日志观测**到dispatch为2.162–5.275ms。六步输入增量均为8000samples/0.5s。

**EOS j26不在这个集合中。** 它的输入增量7969samples/0.4980625s，原infer分别0.813146312/0.825710608s，started_on_canonical=False。最后一个非EOS j25的自有预测匹配原选定end，因此EOS能重新条件执行；不能说所有七个miss都是被反证后的current-parent replacement。

原model区间是原函数/同步围出的host时间，包含其实际callback与原C/U，不是独立GPU kernel时间。现稿“original inference”可保留，但不能改写为纯GPU费用。

## 5. Local publication→D不是guard税，也不是新修复性能

该间隔跨越Supervisor主循环排队/前置同步日志、publication处理及实际Consumer验证/应用等，当前记录没有把它拆成独占guard CPU。S0901之前人工定位的pub46/47同可见状态snapshot和FIFO等待，与正式间隔一致。它不能被改名为单一检查开销或直接从服务总时间相减。

EVENT_CLAIMS中六个EOS在publication receive时的latency已大于2s，事实正确；其decision_scope也已限定为原观测路径，没有声称全局删除/重排日志的测得收益。

为避免“单个EOS miss不必使线性P99失败”的推理漏洞，本次只读对ENDPOINTS现有时钟作了额外算术核对：保持原first-view路径与全部上游时钟，取 `recorded publication receive−original offer`，按原unweighted linear P99公式得到下列值，均仍>2s：

| 格 | 固定原路径的receive-latency P99 /s |
|---|---:|
|S0901 r0|2.252235|
|S0901 r1|2.384693|
|S0902 r0|2.179126|
|S0902 r1|2.673493|
|S0915 r0|3.050156|
|S0915 r1|3.024897|

这是验证一个**局部负判断**的已有数字运算，非模型实验、formal重算或可实现的新服务结果。它支持“仅消去原路径receive之后的局部延迟，不能把六格任一whole-run门改绿”；它不证明改变系统后所有上游时钟/路径都会不变，也不证明任何合法优化都不可能成功。

## 6. v12原文逐句判断与建议

`Paper_DSN/revisions/20261102_dsn2027_release_v12/sections/05_native_retention.tex` 的新段落总体准确：

- 六个失败来自三source、S0915质量及七frontier×2：一致。
- repeated corrections反证后续完整输入：原proof链接和full-state比较支持，未只用文字相同/不同代理。
- S0915 r0 F6：dispatch7.590534→ASR7.976400→actual consume8.022780、deadline8.000000；正文7.591/7.976/8.023的舍入正确。这是实际交付把该边缘点推过D2的见证，不是整轮可修证明。
- S0901在匹配输入上保留前确认EOS；ASR仍late：一致。“early”指相对父确认提前执行，不能在别处改成“timely EOS”。
- S0902完整输入反证后失去lookahead：与current-parent正确调用的原时序一致。

**建议必须补清的一个范围词组（没有数值纠错）：**

> In each repeat, the six late non-EOS replacements dispatch about 2--5~ms after the recorded parent-install event and spend 0.53--0.74~s in the original inference call for each 0.5-s input.

如希望保留更精确范围，可写2.2--5.3ms。限定“six/non-EOS”排除j26的0.81–0.83s；“recorded parent-install event”与正式字段的日志观测语义一致。现稿0.53–0.74本身没有错，但紧接“through EOS”容易让读者误套到全部七点。

可选、非必须：将“matching early EOS call”写为“input-matching in-flight EOS call”，进一步消除“早于deadline”的歧义。不建议再添加新counterfactual、调度器或回归矩阵。

最终独立判断：**PASS，附上述最小范围限定建议。** 这批证据适合解释原固定系统的服务边界，不能变成纯guard税、错误实现已被修复或新的期限保证。

# Core与边界呈现独立审查 v1

2026-10-31。只读审查新稿`05_evaluation_core.tex`与`05_operating_boundaries.tex`及已有有界metadata；未编辑论文、未扫描原raw、未调用模型/SSH、未改指标。输入文件长度/SHA与本次文稿快照记录于`CORE_PRESENTATION_AUDIT_INPUTS_v1.json`。这不是新的实验结果或最终PDF视觉验收。

## 结论

**数值、分母和静态引用通过。** 首次抓取稿中的两项RevTrace D99范围不准确，Root正在同步修正；复读确认已变成下表正确值。四臂主发现及作者完整正控的身份未发现错误。另有三处短措辞建议，已经分别发给Root：明确边界表最后列只列R10/R11；能耗59.16–59.73为跨臂中位数范围；内容图的matched试验通过与resident请求通过不能统称whole-run passes。下文区分已核事实与这些编辑建议。

## 1. 全48个原运行与新边界表

直接读取`experiments/dsn_midpoint_continuity_20261029/COMBINED_DATA_v1/RUN_ENDPOINTS.json`（48条原值），不是从旧图坐标反推。按point、arm、repeat分组，重复顺序r0/r1/r2：

| Workload | 全部臂/重复joint D2/C8 pass | RevTrace R11 display-P99原值 / s | 应显示min–max / s | R10 secondary及时兼容loss windows | R11 windows |
|---|---:|---|---|---|---|
|8 sync|12/12|1.528392029,1.442405783,1.426366496|1.426–1.528|1,0,0|0,0,0|
|8 staggered|12/12|1.704412707,1.724690094,1.954826906|1.704–1.955|1,2,1|0,0,0|
|12 staggered|0/12|2.196642289,2.298685094,2.227744697|2.197–2.299|1,1,3|0,0,0|
|16 staggered|0/12|3.223255310,2.801328113,2.919546100|2.801–3.223|10,12,9|0,0,0|

每point=四臂×三fresh processes=12run。前两个point各12/12，后两个全部D2失败且C8通过。8/12/16session每臂offered121.205/185.300/250.180s，源混合随session数扩充，正文明确不是纯容量曲线。两次8session uncredited tail各0.215s，具体为R00 staggered r1与R11 staggered r2；P99通过与尾部未获credit同时成立。

首个文稿快照的8stg1.686–1.955与16stg2.784–3.224不是R11这三点的range。Root收到独立原值后已改为1.704–1.955和2.801–3.223；审查后续复读确认，未由本审查者直接修改。

## 2. c12强见证与secondary windows必须分开

冻结`FROZEN_MIDPOINT_STRONG_WITNESS.json`给出`STRONG_WITNESS_NOT_ESTABLISHED_STOP`，其中两组3/3 P99条件不满足，R10完整非EOS见证条件也不满足。它**不等于secondary loss windows为0**。

进一步读取已有`RESULTS_v1/RUNS.json`和`TIMELY_LOSS_WINDOWS.json`：

- R10的`strong_full_non_EOS_timely_compatible_windows`为0,0,0，但secondary windows为1,1,3。
- R11两者都为0,0,0。
- R00 r2另有**1个**完整2s非EOS兼容窗口（session9,F192000），所以不能把R10无完整见证概括成c12所有臂均无任何完整窗口。

新正文“smaller losses in the table”在表仅列R10/R11时可成立，但建议明确为“computation-only's smaller losses”，免冷读者误以为对所有四臂作全称断言。表题/正文不把未建立的strong witness写成secondary没有损失。

## 3. c16及代价段的数值

同一48原值重新配对：

| repeat | R11−R10及时coverage / s | R11−R00 / s | 交互I / s | R10兼容withdrawals | R10 secondary deficit / audio-s×wall-s | D2读点缺失 / audio-s |
|---|---:|---:|---:|---:|---:|---:|
|r0|+18.910|+20.280|+20.910|16|24.903354589|6.000|
|r1|+5.055|+22.885|+26.380|17|23.634917157|10.675|
|r2|−7.225|+20.180|−9.575|12|15.736030408|4.000|

RevTrace三次兼容withdrawals与上述secondary windows均为0，display-P99优于R10仅1次。相对R00减少physical model时间为1.585201372/0.916446366/0.656308694s，显示范围0.66–1.59s成立。能耗差−109.666/−5.250/+34.146J，episode wall差−0.007476/+0.273687/+0.253822s，均不能写稳定能耗或墙钟加速。

RevTrace raw same-frontier agreement相对原credit减少2s的运行是c16 r2、c12 r0/r1。另有R10 c12 r1也减少2s，所以新稿该句建议写“RevTrace's raw comparison”作为主语，而不是含混地让读者以为列尽所有臂的raw差异。原normalizer相等的合同沿用原分析，这里没有重扫文字。

## 4. 独立24speaker主分层和完整正控

独立读取`physical_retirement_20261028/H3_RESULTS_v2/{COMPACT_TABLES.json,aggregate/RUNS.json}`：110cells=60primary+20paired_jitter+30coarse。predeclared Qwen/rho1/staggered分层共15run（5臂×3cohort）；**15/15的display P99>2s**，因此主图caption包含完整正控的全部15run D2失败是准确的。

| 原arm|withdrawals合计|期限coverage / s|displayP99每run统计的median / s|erased code points|GPU J/audio-s每run统计的median |
|---|---:|---:|---:|---:|---:|
|R00|12|654.115|3.796606210|633|59.715039732|
|R01|1|628.435|3.890572895|524|59.160517271|
|R10|17|664.150|2.430698946|808|59.676245096|
|R11|0|680.760|2.328649213|569|59.374881807|
|STANDARD_FULL|0|667.530|2.534055115|569|59.725646499|

每臂offered714.110s。R11相对R00+26.645s、相对R10+16.610s均精确。按原RUNS重算cohort A/B/C的`Y11−Y10−Y01+Y00`分别18.530/6.205/17.555s，未以deadline窗口伪增样本量。新稿同时保留fresh cohort A的I=−2.245s（226.320/230.565s），未宣称全负载超加性。

R11在headline18/368兼容机会且18保留，R10为17/368且17清除。同步R11为3/368，期限coverage比R10低0.790s。所有计数与原COMPACT表一致。

`CANONICAL_HISTORY_GROUPS.json`共144group，全部`all_recorded_histories_equal=true`且无缺history；`STANDARD_POSITIVE_CONTROL.json`共22pair，全部`canonical_histories_equal=true`。其源role明确为author-built complete-composition positive control；新稿“Alternative joint implementation / our complete positive control / shared substrate”的身份表述准确，没有写成外部原生SOTA或独立重写神经栈。

Headline WER26/1908=1.36%在各臂相同。Whisper rho1=83.123689727%，coarse rho3=11.530398323%，反馈合同不同的范围保留。Headline的59.16–59.73是上述**五臂各自run中位数的跨臂范围**，建议文字写“arm-median board energy”，避免误读为15原run的min–max。

## 5. 引用、图表与未完成范围

从当前`main.tex`递归跟随字面`input`，共19个可达TeX文件、30个label；0缺input、0重复label、0未定义ref/eqref。Core新图`fig:main_evidence`与新边界表`tab:operating_workloads`及原`eq:credit`均有唯一定义。Finding编号由Root统一，本审查不改。

内容图caption的matched与resident通过数应分开描述：前者8trial/臂，后者2常驻trial中的8request/臂。`Original whole-run passes`统称panel(b)两类不够准确；已建议改为“Trial passes (matched) and request passes (resident) retain their original D2/C8 criteria.” 这不改变任何通过数。

本次不评定最终新图PDF的视觉布局、字体或最终整稿分页，不继承v4的视觉QA作本轮验收。全48point artifact的原数据保留、主文边界表与负面范围已核。最终联合图排版/源数据映射和整稿编译由Root/绘图agent继续收束。

## 6. Root修订后闭环

审查末次复读确认Root已落实全部措辞点：

- “computation-only's smaller losses”明确c12非完整区间结论的作用臂；没有抹去R00 r2另一个完整见证。
- “RevTrace's raw comparison”明确列举哪一臂的posterior support差异。
- 能耗句增加“across five arm medians”，没有把跨臂中位数范围写成run min–max。
- 新主图caption改为“Trial passes (matched) and request passes (resident) retain their original criteria”，两种通过数的分母分清。
- 两项D99范围已按R11真实三点修正。

另外直接复核`COMBINED_DATA_v1/OPPORTUNITY_RATES.json`的actual Consumer apply记录：c16 R10 compatible opportunities/cleared均16/17/12，无incompatible ahead或未知项；R11兼容clear为0。因而正文这些“兼容撤回”计数不只是用总audio rollback代理。未访问原raw。

新文稿审查快照及新增OPPORTUNITY_RATES哈希另存`CORE_PRESENTATION_AUDIT_INPUTS_v2.json`，原八个有界证据源前后字节未变。最终本子任务状态：**PASS_NUMERICAL_SCOPE_AND_STATIC_REFERENCE_AUDIT_AFTER_ROOT_WORDING_FIXES**。最终PDF编译/视觉QA仍由Root执行。

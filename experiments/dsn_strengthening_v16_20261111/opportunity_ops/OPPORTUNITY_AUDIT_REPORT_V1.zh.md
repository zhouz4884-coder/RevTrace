# 24格native pilot：机会、真实对照与边界

2026-11-11。完整24格机会审计PASS，22项聚焦CPU控制全过。源码依照serving前已冻结的v5定义编写；作者在实现冻结前没有读取serving outcome。实现冻结时间晚于pilot完成，不冒称实现本身在首个serving cell之前已冻结。正式CPU只在Root确认pilot退出/CUDA空闲后运行，12:30:41 UTC闭合；随后RESOURCE8开始，本文仅重组已冻结有界输出，没有再扫原raw、跑测试或模型。

**最强结果是：在飞完整原调用的保留确实被激活，而且完整结果memoization不足；但这批输入没有激活“祖先版本失效、完整输入仍未被反证”的独特分歧。** Fullcall与强dependency-versioned都保留56个普通直接相容handover，四次逐source/repeat期限信用完全相同。不能把这56件或旧92件改称56/92个与强版本方法的分歧。

## 1. 全24格、全部实际成本与结果

每臂4格＝两位既有speaker×两次fresh；每臂offered33.116250 audio-s，含原500ms/8000sample和partial EOS。它们不是4个独立speaker，也没有新增独立声学来源。

| 臂 | D2/C8信用s | 及时、后见同G全文支持s | whole-trial通过 | worker wall-s | 已观察infer wall-s | infer缺测jobs | 两板origin→实际drain J |
|---|---:|---:|---:|---:|---:|---:|---:|
| Conservative |12.000000|12.000000|0/4|48.780547|48.082922|0|26063.657|
| Dependency-versioned |32.340125|30.500000|2/4|51.878951|50.010869|2|22062.787|
| Fullcall |32.340125|30.500000|2/4|51.764636|49.901344|2|22376.920|
| Ready-only |12.500000|12.500000|0/4|82.145438|54.903466|49|30246.708|
| UIR |30.840125|29.000000|2/4|52.990277|52.318277|0|24027.254|
| Strict-birth辅助 |12.000000|12.000000|0/4|81.299560|52.422584|53|30780.751|

worker wall不是GPU active time；infer是原同步engine.infer及其中回调/同步的区间，不是独占神经/GPU算时。106次before-C异常没有完整infer timer，缺测不是0；全部worker timer有记录。上述J只覆盖原神经READY之后的service origin到确认物理drain，两板均计，startup/reference另列，不能叫完整冷启动能量。

所有24格外部功率都有边界/窗口内样本、schema及generation-bound worker launch/exit区间证据；未见foreign PID样本，因此表中24/24能量均可按该记录范围使用。它不是逐NVML样本starttick硬件证明，也不保证未采样瞬间没有干扰。

## 2. 不同问题的机会必须拆开

| 臂 | 实测model-active输入确认jobs | 其中整个parent receipt→install区间均active | ancestor-only独特分歧jobs | 实际recorded promotions | Owner-ready复用 | before-C退出 | late完整拒绝 | 相同完整input/target再派发 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Conservative |0|0|0|0|0|0|0|0|
| Dependency-versioned |56|56|0|56|0|2|0|0|
| Fullcall |56|56|0|56|0|2|0|0|
| Ready-only |9|9|0|0|0|49|9|56|
| UIR |54|54|0|54|0|0|2|0|
| Strict-birth辅助 |5|5|0|0|0|53|5|56|

Ready/strict列中的9/5是**原调用输入确认时确有模型仍active的机会**，后来被该政策fence；不是9/5个被它们实际保留下来的promotion。其余提前退出没有完整infer时钟，不能用9/5推断它们总共只有这么多在飞计算。Fullcall/Dependency各56件则既有真实原模型执行、完整输入匹配，又实际成为selected原结果。

这批唯一job身份必须带cell/source/owner/incarnation，不能跨cell只按e0-j序号合并。全表共530次实际派发＝408个installed＋106个before-C退出＋16个完整结果拒绝；pending0。实际promotion事件166，model-active确认机会180，两者不同，不能相加为独立工作。所有实际Consumer1200行都重建检查；speaker仍为2。

### Fullcall vs Ready-only：在飞保留有真实增量

Fullcall两位speaker跨repeat的真实model-active相容确认分别30、26，全部有native_model_evaluated=true、model_start≤install<model_end，且更强地覆盖整个已记录parent-receipt→install区间；不是排队、物理已结束但Owner未处理或Owner-ready伪装。

Ready-only的Owner-ready复用0是有效结果，不能证明它等价Conservative：它确实提前派发、产生支持视图，并在每次install fence未admit的调用，出现56次相同完整input/target再派发、49次policy before-C退出和9次late refusal，占用82.145s。Fullcall占用51.765s，期限信用多19.840125s。门达到两speaker最低presence，但这只是激活，不是power/显著性保证。

### Fullcall vs强dependency-versioned：独特分歧没有被激活

actual-prefix shadow逐个真实install比较完整start是否refuted/current/pending与较早frozen ancestor反证，首次fence持久记忆，未来实际合法安装另标；没有替换原调度。**Fullcall basis和Fullcall/Dependency union basis，两speaker各自均为0个ancestor-only分歧。** 因此不存在可在本pilot里量化的later-legally-installed分歧子集。

普通直接相容56件两者都留住，四个逐source/repeat信用分别完全相同：S0769两次均8.4200625s，S0901为7.5/8.0s；同G支持总量也同为30.5s。v5允许的结论是：**当前合同下较简单的版本表示足以实现观察到的合法提前执行收益。** 这不是所有版本规则都正确，也不是Fullcall所有check被证明冗余；不应自动扩大为160次未回答问题很少的重复。

## 3. Fullcall vs UIR：小而有条件的退休机会

UIR正确地发出0个skip hint，但观察并压住2个实际完整输入失配hint；两件仍完成原infer，返回后均被拒，0件被selected。Fullcall对应S0901两repeat各发生1次真实before-C退出，随后确有新job使用该物理worker；S0769则无退出机会。原ASR已执行，退出infer timer为NA，不称纯神经0。

| source跨两repeat | Fullcall before-C | UIR suppressed/错误完整返回并拒绝 | Fullcall−UIR信用s | Fullcall−UIR worker-s | Fullcall−UIR J |
|---|---:|---:|---:|---:|---:|
| S0769 |0|0 /0|0.0|−0.271294|−1554.293|
| S0901 |2|2 /2|+1.5|−0.954347|−96.041|

这与S0901有真实取消机会和少量服务增量一致，但另一speaker没有机会，退休扩展的“两speaker各≥1”最低门未达到。更不能把总1650.334J差全部归因于两次取消：最大能量差来自S0769/r0，那里没有取消，UIR7512.138J而Fullcall5877.455J；其r1方向还反转。这是应保留/诊断的有限重复能量变化，不是2%筛选或重跑直到变好。

UIR仍运行input/coverage分类并共享end-use EL/AU/SUP，所以即使它完全追平，也不能说完整输入检查或其CPU成本可删除。这里也没有把任意原C入口重检的潜在收益测出来。

## 4. 真实SUP机会存在，但五臂不能识别SUP独立收益

| 臂 | 非空compatible-ahead实际应用 | 完整tip保留 | avoidable loss | 必要不兼容撤回 |
|---|---:|---:|---:|---:|
| Conservative |0|0|0|0|
| Dependency-versioned |4|4|0|0|
| Fullcall |4|4|0|0|
| Ready-only |5|5|0|0|
| UIR |6|6|0|0|
| Strict-birth辅助 |4|4|0|0|

合计23件实际Consumer应用，均完整保留。Fullcall四件全部来自S0901，两repeat各2；S0769无此机会。这里不是只看frontier或文字相同：每个step绑定实际registered完整start/target及protected ASR或full receipt、kind和完整end，然后按实际publication/verified fact重建全链。area按实际PRIVATE部分恢复分段积分，下一canonical截断；本次loss0，面积0，不代表未测window被补0。

SUP在五主臂里固定，不能用这23件给EL contrast再加一个独立SUP收益。它们可作为是否值得另冻same-native-task support ablation的机会线索；独立SUP因果证据仍是已有严格R×S，而不是在本五臂中“分摊”audio秒。

## 5. Conservative的serialization问题：能从现有timer知道多少

以下只用已冻结OPV1付费job表的成对worker/infer duration做文档算术，无新raw或实验。Conservative68件全部有两个嵌套timer：worker48.780547s减原infer48.082922s＝**0.697625s，约占1.430%**，平均10.26ms/job。

它是charged worker interval内所有outside-infer工作的总和，可以作为**其中serialization部分**的上界，但包含必须的restore/insert/export等，不是已测得的可避免serialization税。模型内部callback成本仍在infer内，命令/结果传输、Owner/WAL/Consumer和调度等待又在worker interval之外。付费表未导出全部绝对model_begin/end，只能核这组成对duration。因此不能由1.43%断言online original-continuous baseline最多改善1.43%，也不能无新同输入控制宣布省掉整个wrapper的收益。

### Ctor_nofault /pre-post-bound数据可用性

本轮没有新的NNde专用Ctor_nofault/subphase/meminfo pre/post GPU实验结果。PILOT的原READY记录有coarse model_load/full_load_warmup时间、实际precision/env以及终结resource snapshots，但OPV1没有把这些变成constructor子阶段测量。formal/recovery审阅方确认其已完成记录只有8个历史4f故障cell的coarse加载/能量；loader_profiler_dev和LOADER_CONTROL_REVISION_v2仍是prospective/unintegrated。**新NNde的Ctor_nofault wrapper/pre-post-bound表应记N/A，不能搬历史4f数充当当前观测。**

## 6. 检查了什么，以及尚未执行的精化检查

已完成的是具体数据检查：原de NN scanner的checksum/完整fact链、完整parent/end/C/IDs新reference、原f367逐job终态partition、原500ms/EOS端点、actual-source-backed Consumer全链、Owner receipt/install序号与physical job身份。22个CPU案例针对真实协调器、sticky fence、actual later install、UIR共享拒绝和hint差异、缺timer、ready边界、部分恢复积分、伪造view source、重复receipt与能量缺schema等。

**独立手写模型到实际Python每一步的trace-refinement检查尚未在这次audit中执行。** 原driver的Root_actual_trace_audit_pending/ROOT_ACTUAL_TRACE_RECHECK_ENTRY保留，不删也不因新绑定PASS改成已完成。它不意味着当前facts/Consumer完全没检查，也不能把本审计升级为整个Python/CUDA/OS已精化证明或GPU执行attestation。

## 7. 来源、字节与闭合

- 原NN：de0936b2e30179d63aeef6e235cd1af685578c58，66文件/manifest ce99ca42...。
- 原driver：f367c4e1068a9391a0e99d8537c94995a3388e13，20文件/manifest c9c0fa0c...。
- 本审计实际source：`0d54630951dff6e1a423a1652704ee39eea0b8ce`，17文件，完整bundle已导入root ref `refs/revtrace/execution/v16-pilot-opportunity-audit-v1`。
- 审计manifest SHA：`fdaa04d4567a9a1d0b25f0d7bd93043da681ca67fc01ac9a91461d54a52cd33e`；bundle SHA：`b92d80a650c8205d7c0f2bbda39a7f68370f3b8d348ef135160b9a087b5ba13c`。
- config SHA：`420dd86121c1487dbc6a3ac3b26398f411b4d96d6cdb14e0aa00685cc24f19d5`；environment SHA：`4a9190ccb247897ad09dc58cc70ce8212c9e5bab75843840f907395383f2a32c`。
- 固定plan SHA：2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6；v5定义 SHA：32fcbdf1cac6f74326b9569a874d3d6d7b80b12757e4dd0e61b91d72ce0e4989。
- 522个冻结输入、164038043字节，执行前后大小/SHA一致，无缺失input；无模型包导入/新模型调用。

8TB raw位于 `.../results/revtrace/dsn_strengthening_v16_20261111/PILOT_OPPORTUNITY_AUDIT_V1`。取回202有界文件1452135字节，逐SHA一致，在 `opportunity_ops/RESULTS_V1`。SUMMARY SHA `d878661ab71ede43d265b6ba1a27c1edf5c815513a91f4343325e821f5bbcc4f`；GATE SHA `0e080cff68a738d90963370a6c1d010d894b8d57ce281274e46cf28cd5172b9f`；ALL24表 SHA `bc3e852ab83fb61a3ce484e01b0eb029e8821171e9090d2ad473ceb8577d511a`。

presence表SHA `223907e7f53e3c26e7a58dee52a4a4d404d9f1ff9e2e2144b7f387e0071f5628`，原actual paired contrasts SHA `1c52e1aab80a143bf6effc68ffd8a996beb442673e79876738126d28b260d214`。本文汇总算术另记 `BOUNDED_INTERPRETATION_TABLES_DERIVED_V1.json`（DERIVED_FROM_FROZEN_OPPORTUNITY_OUTPUT_NOT_NEW_RUN，SHA `0e172610d1814732f625762207c0b268e9ab84d7ce825ee1fae8a5d8ed83e2ab`），未改原结果。

CPU PID2886052/start615001513已消失，12:30:41 UTC确认无本审计执行与CUDA owner，最终NNde默认/自身0d source预检PASS；Root于12:32:58另启RESOURCE8后，本子任务没有再运行raw分析、测试或模型。后续大规模扩展须按v5区分“在飞保留已激活”“Vdag独特分歧未激活”“退休仅单speaker激活”，不把最低presence门称power，不把五臂差或重叠时间相加为每个check的唯一audio秒贡献。

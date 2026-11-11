# EOS诊断：24格复核、固定端点反事实与修复边界

2026-11-11。已完成独立冻结CPU实验 `REVTRACE_EXACT24_EOS_DIAGNOSTIC_20261111_V1`，4项controls通过、0 skip；24格原f0 P99、miss counts和加权credit全部重现。无新模型/GPU调用、无音频读取，没有改当前NN/controller、G、D2/C8、source或offered分母。

**结论：EOS是残余问题之一；“全部残余失败100%是EOS、只修EOS即可2/4→4/4”不成立。** Fullcall的S0901 r0同时有1个非EOS D2 miss；只改EOS D到1.999999秒或理想0秒，原whole-run quantile通过数都只变成 **3/4**。

## 1. 实际24格EOS与非EOS失约

下表D/C是该EOS前沿相对原offer的实际首次显示/认证延迟；所有24格C8 miss都是0。完整408个前沿、原/反事实D99及输入SHA在 `EOS_DIAGNOSTIC_v1.json` / `EOS_CPU_RESULTS_v1/SUMMARY.json`；逐格完整表另见 `EOS_DIAGNOSTIC_TABLE_v1.md`。

| arm | source | r | EOS D2 misses | nonEOS D2 misses | EOS D / C (s) |
|---|---|---:|---:|---:|---:|
| Conservative | S0769 |0|1|9|4.468186 / 4.763346|
| Conservative | S0769 |1|1|10|4.809839 / 5.076855|
| Conservative | S0901 |0|1|10|6.294407 / 6.671419|
| Conservative | S0901 |1|1|11|6.386118 / 6.712730|
| Dependency | S0769 |0|0|0|0.880736 / 1.129848|
| Dependency | S0769 |1|0|0|0.813713 / 1.069541|
| Dependency | S0901 |0|1|1|2.471738 / 2.746899|
| Dependency | S0901 |1|1|0|2.405556 / 2.571727|
| Fullcall | S0769 |0|0|0|0.778995 / 1.056663|
| Fullcall | S0769 |1|0|0|0.822141 / 0.983634|
| Fullcall | S0901 |0|1|1|2.602553 / 2.738675|
| Fullcall | S0901 |1|1|0|2.407536 / 2.588414|
| Ready-only | S0769 |0|1|9|4.976616 / 5.208714|
| Ready-only | S0769 |1|1|10|4.987521 / 5.203122|
| Ready-only | S0901 |0|1|10|6.061554 / 6.600860|
| Ready-only | S0901 |1|1|10|6.495926 / 7.107178|
| Strict-birth | S0769 |0|1|10|5.013922 / 5.247798|
| Strict-birth | S0769 |1|1|9|4.824607 / 5.074424|
| Strict-birth | S0901 |0|1|10|6.153167 / 6.784331|
| Strict-birth | S0901 |1|1|11|6.789823 / 7.058323|
| UIR | S0769 |0|0|0|0.927676 / 1.249709|
| UIR | S0769 |1|0|0|0.916266 / 1.055546|
| UIR | S0901 |0|1|3|2.868247 / 3.111354|
| UIR | S0901 |1|1|1|2.702267 / 2.904616|

“18/24格有EOS miss”确实成立，但不是“全部残余miss都只在EOS”。Fullcall S0901 r0的非EOS前沿为 **F=128000（8.0s）**，D=2.063384300s、C=2.568379885s，不能归入EOS=130209。

## 2. 只移动EOS D的两个算术反事实

严格保持其它所有原始D/C、前沿、deadline与weights不变：A只把晚EOS D压到1.999999；B把EOS D理想化为0。它们不执行另一schedule，也未证明真实whole-view发布能独立只改变这一个数组值，**不是已部署修复**。

| arm | 原credit / 原pass | EOS-only两情景credit | EOS-only两情景pass |
|---|---:|---:|---:|
| Conservative |12.000000 / 0/4|13.116250|0/4|
| Dependency |32.340125 / 2/4|32.616250|3/4|
| Fullcall |32.340125 / 2/4|32.616250|3/4|
| Ready-only |12.500000 / 0/4|13.616250|0/4|
| Strict-birth |12.000000 / 0/4|13.116250|0/4|
| UIR |30.840125 / 2/4|31.116250|2/4|

每臂原offered为33.11625audio-s。Fullcall97.656362%→98.490167%，增加0.276125audio-s/0.833805pp，仍剩非EOS0.5audio-s未获双期限信用。S0901 r0的D99原为2.516286；情景A为2.053243，情景B仍2.015906，均未过2秒。r1可因EOS改善而通过，但不能把r1的“只剩EOS”推广至r0或所有策略。

2/4只描述这四次真实运行的原quantile结果。两次同speaker重复出现同通过/失败标签，既不是总体“50%失败概率”估计，也不证明该speaker确定性失败或未来修复必过。

## 3. 精确权重，不是±1.5pp测量不确定性

非EOS一步为0.5audio-s；两个EOS余量分别0.4200625与0.1380625audio-s。相对每臂四次总分母33.11625，单个0.5前沿的变化为1.509833pp，两个EOS权重分别1.268448pp和0.416903pp。它们是**不同权重的端点增量**，不是对称±误差条、重复间标准差或“更小差异不可解释”的阈值。D99和真实timestamp也不按这个pp量化。相同credit不能推出时钟/行为等价；小于1.5pp的EOS变化完全可以精确解释。

## 4. 早期0→16k/24k：不是权重预载冷启动

原service origin在两worker neural-ready与固定C/U warmup完成之后设定，预载权重时间不在D/C主clock内。author原`infer:840–844`还先做min segment length检查；1秒音频之前可返回buffer-only而无neural coverage。NN配置audio_min_len=1.0，原task可产生空文字，Consumer显示前沿不会用空文字伪造可见覆盖。

Fullcall S0901 r0最初三个D为1.510280/1.010280/0.510280，来自同一个实际job3的首次view，故相差0.5；r1也如此。S0769首次view来自job2，前两D为0.918489/0.418489，并非共同“三个冷前沿”。S0901 r0 first C甚至先于first D，说明“已处理/认证”与“非空可见view”又是不同对象。

已有bounded OP还记录S0901 r0第一个8k原call infer约0.000277s，16k约0.225880s，24k约0.667081s。可确认这是原buffer/解码/显示激活与pipeline fill的一部分，不能称模型加载冷启动；是否另有shape/JIT/allocator首次成本未由该数据独立识别。**不删前三个offer或改主D99分母**；可以另列明确辅助阶段图。

## 5. EOS源路径与已观测时间，不臆造+0.55秒C

固定author SHA `9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7`。`infer`把保留segments拼接后重新算mel/encoder（846–866），EOS虽只新增0.138秒，不代表只计算0.138秒。is_last改变帧阈值、rewind/末端截断及最终flush（905、1009、1024、1114）；corrector guard1056没有EOS特例，仍遵守原C/U。

NN3的`stage_worker.full_step`传真实`is_last`，`CandidateBridge`在实际原corrector边界发typed ASR projection，StageCoordinator admission也没有禁EOS早显的条件。四次Fullcall EOS的first D均已绑定到其真实selected EOS job的private投影；**不存在“EOS没有early-ASR路径，所以补开关即可”的证据。**

| Fullcall EOS（S0901） | r0 | r1 |
|---|---:|---:|
| 原EOS offer→selected job dispatch |1.901463|1.689106|
| 该job完整infer墙钟（ASR+C/U+callback） |0.762532|0.737247|
| dispatch→真实首次private显示 |0.701089|0.718431|
| 首次private显示→首次认证消费 |0.136122|0.180877|

大部分display预算在EOS job派发前已用掉；该间隔可含前序依赖/可派性、scheduler、ingress通知，不能全部命名为单一queue。EOS D已经来自C前的ASR投影；邻前沿D之差不是独立corrector时长。bounded记录不能精确拆ASR、C、worker queue、WAL fsync、Owner与Consumer传输；display→certified也只是剩余路径的观察间隔，不能当完整C耗时。

## 6. 修复判断与小probe事前边界

**没有足够证据认定是几行的低成本EOS修复。** 不能提前读取未接受的最后音频、padding、丢EOS、放宽D2、跳过原C或改变原G来制造4/4。只优化EOS最终delivery也不能自动治好r0的8.0s非EOSmiss。

独立预登记的小诊断在`EOS_STAGE_PROBE_PREDECLARED_v1.json`：既有失败source S0901加及时source S0769，作为公开已见development；各两次原连续完整stream，加同exact EOS start的原/只加时钟instrumented对照。保持原500ms/partial EOS/C/U与完整state/C/IDs gate，记录实际ASR/decoder/EOT、projection发送/接收、C入口/出口、restore/worker、WAL/install/Consumer边界。CUDA细分计时若加同步，仅属于诊断模式，不能混成原serving效果。

该probe未实现、未冻结执行源、未启动；须在当前n4 Focused8主任务之后，由root另冻结源/config/env/inputs/ID和paid work，不插入或重写当前NN/controller。目标先区分“前序ASR/派发关键路径”和“可避免的host发布/flush延迟”，原/原重复与原连续脚本是合法oracle。只有发现真实可修且仍有端到端机会，才提出窄实现与另一个新版本的同输入重跑；无结果承诺。

## 7. 本次证据身份与附件其它事实

* 分析source：`a5e069817bf2eb7f0b1efa604b78c21e43361a28`；manifest SHA `dca0f66491095f9d834106b82235f38748d971974303194141ea7242b6f1a221`；root完整commit/ref可解析。
* 冻结config SHA `3de609cfdfc6a12a8c9371c40415d6276eb836590c00305eac56d8f2cf6459ec`；每格config/origin/Consumer/SUMMARY/OP work精确SHA，以及reference config均在其中。只读这121条明示路径；结束后复核SHA，没有广扫原始银行。
* ID/config/env、8TB raw/summary/gate均在启动前记录；source/run gates通过，CURRENT仍NNde09/d2af。CPU PID2921088已退出；4controls、24原endpoint复现PASS，0新模型/GPU。
* 原结果在8TB `.../results/revtrace/dsn_strengthening_v16_20261111/eos_v1`；bounded逐SHA取回`EOS_CPU_RESULTS_v1/`。SUMMARY SHA `4c24518fb0abd99c15da570c2be7c83f20e9a214a8db29c91924feea032cd37a`。
* 实际`REFERENCE_FULL4_V2` source为S0769W0190、S0901W0183、S0902W0343、S0906W0197；warmup为S0764W0209，**不含S0908**。
* Ready-only的ready命中0是有效观察，不使该臂无效：原24格另有56次重派及合法在飞机会，不能把它误称R×S中的“只保视图臂”。safe UIR仍有end-use AU/SUP，因此附件“去使用前检查”表述不准确。现有2/4不成为收紧D2到1.5秒或重选有利workload的依据。

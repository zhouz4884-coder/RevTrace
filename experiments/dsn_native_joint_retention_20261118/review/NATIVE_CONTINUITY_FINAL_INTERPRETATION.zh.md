# 原生R×S最终连续性解释：80格有界镜像独立核对

本记录直接读取两个已完成campaign SUMMARY，以及80格各自的CANONICAL_SUPPORT_EVENTS和OBSERVED_LOSS_WINDOWS，共162份输入文件；逐文件SHA见同名JSON。没有导入冻结运行时/聚合器，没有GPU调用，没有修改论文或Root最终报告。派生重算V1的GPU-drain/CPU-SERVICE_END先后断言错误不作为神经trial失败：20+60个原神经格均为完成技术门，SLO失败继续留在表中。

## 1. 五臂服务、成本与实际job库存

每臂8个既有speaker×2fresh重复，全部offered为137.864125audio-s。R0=Ready-only、R1=Fullcall；S仅改变实际Consumer的兼容视图保留。Conservative/S1是独立无投机锚点。

| 条件 | 信用s | 覆盖% | whole-run通过 | worker-s | 两板J | admitted ready复用 | unique promoted jobs |
|---|---:|---:|---:|---:|---:|---:|---:|
|r0s0|58.000|42.070|0/16|326.546|118631.806|0|0|
|r0s1|58.500|42.433|0/16|326.232|117825.874|1|0|
|r1s0|130.960|94.992|10/16|222.646|92814.125|0|196|
|r1s1|129.960|94.267|10/16|222.523|89847.958|0|196|
|conservative_s1|55.500|40.257|0/16|197.573|96985.333|0|0|

worker是实际job的host elapsed占用，非GPU-active时间。能量保持service-origin→外部确认physical-model-drain窗口；CPU SERVICE_END可以更晚，不能要求GPU drain必须在它之后。Unique promoted jobs按cell内唯一身份累计，不能自动称为同样多的model-active交接。

Ready-only/S1实际命中1次完整结果库存，位于S0907；Ready-only/S0为0，其余source在Ready/S1也为0。结果证明新运行时的Ready路径确实被实际执行过；零命中格仍是有效策略结果，不以命中为正去选择性重跑。

## 2. 连续性主结果

| 条件 | 兼容ahead机会→保留 | 可避免/必要/unknown撤回 | 移除audio-s | 全体Gap | 同root可避免Gap | 同root必要Gap |
|---|---:|---:|---:|---:|---:|---:|
|r0s0|13→0|13/6/0|9.500|1.506477|0.506138|1.000339|
|r0s1|17→17|0/6/0|3.000|0.854814|0.000000|0.854814|
|r1s0|10→0|10/2/0|6.000|0.595934|0.378727|0.217207|
|r1s1|9→9|0/2/0|1.000|0.323444|0.000000|0.323444|
|conservative_s1|0→0|0/0/0|0.000|0.000000|0.000000|0.000000|

Gap单位均为audio-s×wall-s。机会是实际更新边界计数，不是去重view身份或自然发生率。两个S模式各自的闭环时序不同，例如Full/S0有10次兼容机会而Full/S1为9次，不能把它们逐事件强行配对。

最直接的原生机制结果是：Full/S0有10次完整支持下的实际清除，Full/S1为0；同时Full/S1仍有2次必要撤回，全部来自S0902的两个重复。这支持“选择性保留仍合法视图”，不支持“R开启后ahead只会被追上、永不会被反驳”或“Joint无任何gap”。Ready/S0也有13次可避免撤回，Ready/S1为0，因此S效果不是R=1独有。

首次信用上的S简单效应为R0处+0.500audio-s、R1处−1.000audio-s；四臂交互I=−1.500audio-s。连续性改善与首次信用小幅反向可以同时成立。不可将本轮说成正的期限信用协同，也不可因I为负抹掉实际10次兼容清除→0的连续性证据。

## 3. 实际恢复时长分布

所有39个下降窗均在同一root内恢复；0右删失、0边界截断。根据独立审计的canonical/private事件词汇，restored_within_same_root意味着实际恢复由Private应用产生，而非又一个Canonical事实。下面是观察到的事件时长，非总体分布/置信区间。

| 条件/分类 | 窗口数 | min ms | median ms | mean ms | P95线性分位 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|
|r0s0/avoidable|13|33.929|82.107|77.867|112.259|126.209|
|r0s0/necessary|6|219.421|316.214|333.446|427.326|428.372|
|r0s1/necessary|6|250.369|266.345|284.938|342.263|348.114|
|r1s0/avoidable|10|31.698|63.052|75.745|126.276|134.123|
|r1s0/necessary|2|195.774|217.207|217.207|236.498|238.641|
|r1s1/necessary|2|294.123|323.444|323.444|349.834|352.766|

S0清除后的可避免窗主要是几十到约百毫秒；这与Owner在Canonical后紧随发布Private snapshot的实际机制相符，不能写成每次都等待新的完整模型推理。前沿恢复不等于逐字文本恢复；有界窗口没有给恢复packet的publication ID或完整text/tip hash，故这里不作更强的消息身份断言。

## 4. 两个具体见证

### 见证1：RS18_CONFIRM60_V1_BAC009S0907W0440_r1s0_r1

- 分类：avoidable；完整边界：compatible_boundary；journal sequence=9，boundary job=e0-j000000009。
- Canonical应用时，实际visible frontier由4.500s回落到4.000s，移除0.500audio-s。
- 原观察时刻23947.287933686→23947.348619332，在同root的Private应用后恢复覆盖；窗长60.686ms，面积0.030342823audio-s×wall-s。
- before tip SHA `1738297e39998cb9fb39a8ef7b9f787256f776bbc9d980eee42417f03efb943d`；新Canonical SHA `de8b07dac4ea79044639190c8865c5d46bad9f7f0f555ce7a7d3bfaabc379372`。完整路径绑定由原独立应用审计核验，metadata_binding_checked=True。

### 见证2：RS18_CONFIRM60_V1_BAC009S0902W0343_r1s1_r0

- 分类：necessary；完整边界：refuted_boundary；journal sequence=15，boundary job=e0-j000000016。
- Canonical应用时，实际visible frontier由7.500s回落到7.000s，移除0.500audio-s。
- 原观察时刻21025.338499773→21025.691265744，在同root的Private应用后恢复覆盖；窗长352.766ms，面积0.176382986audio-s×wall-s。
- before tip SHA `4b737043639391768ea492f43f9f0f5d14b53722819c6a405c14b9845ff64d8a`；新Canonical SHA `f9e6a116a3e9eecf71ebbe6ce60c1d646d79242db846da79d6531e17b3b273a8`。完整路径绑定由原独立应用审计核验，metadata_binding_checked=True。

见证1是一个真实S0兼容清除：保留计算并未自动保住已显示视图。见证2来自Full/S1：实际新Canonical否证旧预测边界，S1正确撤回，而非无条件维持单调显示。两个重复都在S0902的120000→112000样本位置出现该必要下降。

## 5. 哪些来源有/没有S机会

| Speaker | r0s0机会 | r0s1机会 | r1s0机会 | r1s1机会 | Ready/S0库存命中 | Ready/S1库存命中 |
|---|---:|---:|---:|---:|---:|---:|
|S0769|0|1|0|0|0|0|
|S0901|4|4|4|4|0|0|
|S0902|4|7|4|3|0|0|
|S0906|1|1|0|0|0|0|
|S0907|4|4|2|2|0|1|
|S0912|0|0|0|0|0|0|
|S0914|0|0|0|0|0|0|
|S0915|0|0|0|0|0|0|

四个因子臂合看，零兼容机会来源为S0912, S0914, S0915；只看Full的两S臂，零机会来源为S0769, S0906, S0912, S0914, S0915。这些零值描述本轮既定工作点，不证明策略普遍等价。

## 6. 对本轮证据价值的解释

本轮确实在同一原生实现、同原任务/资源与现时控制面中同时测到了R和S：R提升首次期限信用，S选择性保留实际兼容ahead进展，必要撤回仍然存在。Conservative的同期信用、worker和能量锚点也全部有了实际测量。它连接了先前core与native分担的机制链。

需要保留的实际权衡是：Full/S1比Full/S0少1audio-s首次信用，却消除10次可避免清除；它仍有两次必要下降。Relative资源比较应分别报告：Full相对Ready可减少重复工作，而相对Conservative会执行额外提前工作；不要把所有资源轴都写成共同严格支配，也不要从8个既有source推广自然发生率。

这份解释不替代Root的最终V2执行/能量窗口重算门。V1错把physical drain要求晚于CPU SERVICE_END，是派生分析假设错误；它不把80次已完成的神经执行变成失败。完整输入SHA与逐事件记录均在同名JSON，供Root交叉复核。

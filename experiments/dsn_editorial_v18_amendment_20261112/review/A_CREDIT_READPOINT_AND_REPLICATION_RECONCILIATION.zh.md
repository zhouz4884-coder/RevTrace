# v18小修：首次信用、4秒缺失与跨runtime抵消的只读核对

只读取已归档标量/逐frontier表并做算术；无论文修改、新实验、模型或原始事件重放。A属于旧c16开发银行r2，每臂offered250.180s，不是H3主24人或当前native N8。

## 1. 201.960−194.735为何为7.225s

现有`dsn_service_stability_20261028/RESULTS_v1/aggregate/FRONTIER_PAIRED_EFFECTS.json`没有直接R10→R11行；它分别有135条R00→R10和135条R00→R11记录。按相同`(session_id,frontier)`和相同audio weight对齐candidate_credit即可得到以下四格：

| 原D2/C8首次信用状态 | 区间数 | audio-s |
|---|---:|---:|
| Compute-only与Joint都及时 |86|167.035|
| 仅Compute-only及时 |18|34.925|
| 仅Joint及时 |14|27.700|
| 两臂均不及时 |17|20.520|
| 全offered |135|250.180|

因此：

- Compute-only：167.035+34.925=**201.960**。
- Joint：167.035+27.700=**194.735**。
- Compute-only−Joint：34.925−27.700=**7.225**。

这是全部135个原offered interval的第一次显示/第一次certification端点比较，没有扣除后续withdrawal，也不会因再次出现而重复获credit。

## 2. 4.000s是已经记在201.960里的两个不同区间

`timely_continuity_v1/RESULTS_v1/TIMELY_LOSS_WINDOWS.json`中，`stability-c16-staggered-r1_s0-r2`有9个compatible interval-loss window；只有以下两个在各自原D2读点处仍缺失。二者均属于session7，source `3570-5694-0003`。时间全部相对**该区间自己的原ready时刻**，D2读点固定为2.000s。

| 音频区间 / frontier | 权重 | 首次visible | 撤回 | 原D2读点 | 再次覆盖 | 首次certified |
|---|---:|---:|---:|---:|---:|---:|
|12–14s / F224000|2.000|1.405608|1.939552|2.000000|3.966590|3.966590|
|16–18s / F288000|2.000|1.415829|1.934055|2.000000|2.221326|3.635438|

两行都满足first-visible<2、first-certified<8，故各自只获一次原credit；又满足withdrawal≤2<recovery，故在D2读点缺失。两次恢复均实际观察到，非right-censored。总缺失为2.000+2.000=**4.000audio-s**，是201.960的子集，不是另外加四秒或重记四秒。

源码证据：`timely_continuity_v1/source_v1/continuity.py`从归档frontiers读取固定`first_actual_visible_perf`/`dual_credit`；约111行按原frontier一次求和；约118行用`(session_id,frontier)`字典去重D2缺失权重；约125行求其和。恢复只关闭loss window，不重置ready/first arrival/credit。本例9个window本来已对应9个不同interval，event-sum与unique withdrawn均为13.605s；D2缺失仍只计其中两个interval。

### Joint的0究竟指什么

Joint的0是“**原本及时且仍兼容的进展，后来被撤到D2读点仍缺失**”这一secondary指标为0，不是所有offered interval都在D2前到达，也不代表它在相同四秒音频上全部及时。

对相同session7的两interval，既有paired表给出：

| frontier | Compute D / C | Joint D / C | 原首次信用 |
|---|---:|---:|---|
|224000|1.405608 /3.966590|2.318602 /2.682852|Compute有、Joint无|
|288000|1.415829 /3.635438|1.192948 /2.578953|两者都有|

所以“Compute多7.225s首次信用，却撤掉其中4s已及时进展”成立；“Joint在同样4s上全都及时、净收益4s”不成立。不能将4s直接从201.960扣除后称新goodput，也不能与7.225相加包装Joint优势。该例证明事件型首次端点与后续可用状态不可替换，而不是Joint对所有目标全面支配。

## 3. H3每cohort简单差与交互

以下全为`H3_RESULTS_v2/aggregate/RUNS.json`的原`dual_credited_audio_seconds`。

| primary/Qwen/rho1/staggered | R10 | R11 | Joint−Compute | 四臂I |
|---|---:|---:|---:|---:|
|A，offered240.520|226.565|229.355|+2.790|+18.530|
|B，offered237.580|215.930|226.110|+10.180|+6.205|
|C，offered236.010|221.655|225.295|+3.640|+17.555|
|合计714.110|664.150|680.760|+16.610|+42.290|

`I=Y11−Y10−Y01+Y00`；它不是Joint−Compute。额外`paired_jitter/staggered/A/r1`的Joint−Compute=−4.245s、I=−2.245s；primary-sync汇总Joint−Compute=−.790s、I=+2.565s。前者仍有5次、后者3次Consumer兼容超前保留机会，不能解释为“无ahead work”。

## 4. 两runtime的129.460为何可相同，但决策事件仍不同

对比原`dsn_native_confirmation_20261102/confirmation/SERVICE_RESULTS_v1/SUMMARY.json`与本轮三个闭合controller SUMMARY。四个改变的非EOS interval权重均为**0.500audio-s**；它不是0.5s延迟、不是半个deadline，D2始终2.000s。

| source / repeat / frontier | 旧D(s) | 当前D(s) | 该run旧→当前credit(audio-s) | 该interval信用变化 |
|---|---:|---:|---:|---:|
|S0901 r0 F128000|1.920003|2.063384|8.0→7.5|−0.500|
|S0901 r1 F128000|2.089332|1.856258|7.5→8.0|+0.500|
|S0902 r1 F136000|2.184100|1.883790|8.0→8.5|+0.500|
|S0915 r1 F88000|1.887220|2.089626|5.5→5.0|−0.500|

四行C均小于8s，信用变化由D2跨越造成。±0.500是该音频interval的score weight；实际D变化约+0.143、−0.233、−0.300、+0.202s。

信用差相抵：−.5+.5+.5−.5=0。miss计数也相抵：+1−1−1+1=0。四行均非EOS，EOS六个失配保持；原/当前总信用仍129.460s、总miss20/EOS6、整场pass10/16，但逐事件集合和四个run的信用已变。因此可称同一银行的**聚合结果复现**，不能称时序/决策事件完全复现，更不能借此排除时序波动。

当前cell ID：S0901两行为`SC_V16_pilot_existing_BAC009S0901W0183_fullcall_r{0,1}`；S0902/S0915为`SC_V16_CONFIRM_BAC009{S0902W0343,S0915W0286}_fullcall_r1`。旧cell均为`SC_NEWTEST_BAC009..._fullcall_r...`。原/当前NN、controller与参考身份保持原记录，不能互贴标签。

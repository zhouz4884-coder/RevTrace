# 历史内容与配对证据：正式 CPU 结果

2026-11-11。本轮完成两个独立冻结 CPU 实验，没有新 GPU、模型调用、论文修改或 CURRENT 改写。它们重读历史实际 Consumer 观察，补上真实编辑与身份寿命的事件账本，并复核所有110格配对和新8speaker的有限样本敏感性。

**最重要的新发现：主四臂数据的569确为LCP后缀关闭，不能称569个文字实际被删改。相同完整事件上，Joint的最少编辑对齐得到2次删除、47次替换；另一最优对齐规则得到3删、45替，总编辑距离完全相同。** view-only与完整正控也有相同的最少编辑计数，尽管LCP关闭量不同。旧native正式12格的新计数也与外部粘贴表不符。

## 1. 实验身份与完成门

| 项目 | 主分析 | 第二实现验证 |
|---|---|---|
| Experiment ID | REVTRACE-V16-HISTORICAL-CONTENT-PAIRS-20261111-V1 | REVTRACE-V16-HISTORICAL-INDEPENDENT-PROOF-20261111-V1 |
| 实际完整source commit | `91cd94d7739f4ff34bedda65357b976a1338c045` | `196b116dc908c3ac55819f3b2547edcc7029d7b7` |
| 完整source文件 |9|6|
| manifest SHA256 | `9f9c8b02df7aa53a01370731c334eafd62e753d5defdf9efa76c5dadeb39d083` | `675c77aaa074eaed3e6af994e837a4008cb0f5df27ab59c77fecfe9d2ece610a` |
| 冻结config SHA256 | `79a18dd205b32b783262fd55888274f2d333ac4e7a9b665299dbd870a27a89f3` | `ef3a04a7d35b29175c79d36ca963d8c1a85911b71f3e0c453d8f9aa396e2200c` |
| environment SHA256 | `2bb763bc4e72fcecafdbd1f80a7313195cc9dec1bccf75e62ad2cd32ae897a82` |同左|
| 控制 |16/16，零skip；其中12内容、4配对统计|3/3，零skip|
| 结果门 | PASS_ALL_INPUT_BYTES_AND_EDIT_CONSERVATION | PASS_INDEPENDENT_ALL_ORIGINAL_ROWS_MIN_DISTANCE_OPERATION_PROOF_AND_LIFETIMES |

干净独立source checkout、完整bundle、manifest及本地可解析execution ref均已完成。两个ref分别为 `refs/heads/codex/v16-history-cpu-v1` 和 `refs/heads/codex/v16-history-independent-v1`。两个新实验各有Root no-argument默认4f预检、显式source预检、预登记config/env/raw/summary/gate路径，未拿历史神经commit替代本轮分析source。

主分析读取29/29实际Consumer：old14中正式12与开发witness2；H3独立24speaker主Qwen/rho1/staggered全部五臂×三cohort共15格。5,500,869字节原Consumer逐项匹配历史 `INPUT_HASHES` / opportunity `ANALYSIS_RECORD`，再绑定本轮冻结输入。原始神经源仍分别为old14 `61c9afa...`、H3 `f0a8e7b...`、new8 `4f4c3ca...`；本轮没有重执行它们。

第二实现没有导入主编辑或统计模块：重读原始Consumer，逐一核对26,076条事件的原文与时钟；用独立rolling-row算法核最小距离，实际应用199,256项I/D/S操作重建after全文，独立传播出生/关闭身份及寿命，检查完整关闭/删失ledger。另独立核对220个run配对差、22个四臂交互、逐source差与符号检验分子，以及新8speaker全部256个交换。它没有独立枚举每个事件的全部最优对齐边界，不能把这部分说成第二实现已经重证。

源、配置和有界结果均在本目录。原始结果保留8TB：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_v16_20261111/{history_cpu_v1,history_independent_v1}`。

完整literal事件及字符寿命不搬入Git；有界结果取回主分析13文件3,607,842字节、第二实现5文件25,262字节，逐SHA验证。第一次bundle验证误在Git目录外调用，发生在分析启动前；修复仅改launcher，失败保存在 `STAGING_FAILURE_v1.json`，冻结分析source未变。

## 2. H3主分层：LCP569与真正最少编辑不同

下表raw口径，24条source，每source只在本臂所属cohort出现一次；三cohort共享服务调度，不能当24个独立部署。I含首次实际显示的全部插入，故总距离由10,575个最终可见码点主导。D+S是特定最优对齐下已显示身份的修改量，不是错字数、人工阅读事件或物理字形身份。

| 臂 | I | D | S | 总最少距离 | D+S | LCP后缀关闭 | D/S关闭前已显示≥2s | LCP关闭前≥2s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R00 |10678|103|47|10828|150|633|30|322|
| R01 |10577|2|47|10626|49|524|34|338|
| R10 |10794|219|48|11061|267|808|37|363|
| R11 |10577|2|47|10626|49|569|30|323|
| Standard |10577|2|47|10626|49|569|34|345|

每臂硬核对 `I−D=10575`、`I+D+S=总距离`；每格LCP关闭数逐格等于原正式汇总。不是更换分母后碰巧得到569。

第二条完整最优对齐历史把优先顺序从 MATCH/SUBSTITUTE/DELETE/INSERT 改为 DELETE/INSERT/MATCH/SUBSTITUTE：

| 臂 | 第二规则I/D/S | D+S | ≥2s关闭数 | 总距离变化 |
|---|---|---:|---:|---:|
| R00 |10679/104/45|149|30|0|
| R01 |10578/3/45|48|35|0|
| R10 |10795/220/46|266|39|0|
| R11 |10578/3/45|48|32|0|
| Standard |10578/3/45|48|33|0|

最少距离不依赖tie-break，删除/替换分解及身份寿命会依赖。R11的271个事件存在不止一种最优对齐；最长被修改身份寿命由主规则8.507秒变为第二规则27.526秒，因此不能把一个对齐给出的最长寿命叫作客观真实字符阅读时间。每事件完整最优操作/年龄边界保留在8TB的事件文件，但这些局部范围以该规则此前身份为条件，不是所有全历史对齐的总体置信区间。

**研究增量：** 对同一组实际Consumer数据，R01、R11与Standard的最少编辑序列总代价相同；LCP524/569/569却不同。它说明LCP后缀重识别会把内部插入后的未改后缀计为“擦除”，原数不能直接解释为文字修订代价。另一方面真实D/S和已展示寿命确实非零，不能改写成文字稳定、不修订或没有用户代价。

## 3. Native old14：正式12和开发2分开

正式12格，每臂4格、最终各184码点，raw与去Unicode空白口径相同：

| 臂 | I/D/S（主规则） | 总距离 | D+S | LCP关闭 | D/S≥2s | LCP身份关闭≥2s |
|---|---|---:|---:|---:|---:|---:|
| Sequential |184/0/0|184|0|0|0|0|
| Drop |188/4/16|208|20|22|0|0|
| Joint |223/39/12|274|51|57|20|22|

第二规则：Sequential不变；Drop为190/6/12、D+S18、≥2s仍0；Joint仍223/39/12、D+S51、≥2s仍20。开发Joint两个witness另112/20/6、距离138、D+S26、其中9个≥2s；LCP关闭29、其中10个≥2s。不得拼进正式表。

因此外部粘贴的Sequential179、Drop206、Joint279以及Joint41删+19替、≥2s编辑量2均**未复现**。粘贴值还不满足同一完整raw范围的长度守恒：Joint219I−41D=178而非184；Drop206总距离减5D减18S得到183I，183−5=178。这里已经有原Consumer逐hash、原LCP逐格守恒、最少距离独立核对和操作证明链，不能再把外部表当新正式结果。

本轮正确结果是：更早显示的Joint确有更多合法中间修订，比Sequential多51次最优身份修改，其中20个此前显示至少2秒。它是观察到的内容代价，不说明51个识别错误，也不是人与系统体验的实验证据。

## 4. 全110格配对：保留正负，p值有条件

正式输出包含22个五臂块的全部220个两臂差、22个四臂交互，以及10个分层内全部source配对符号诊断。没有把offered窗口、调用、两条时钟或同speaker重复当独立n。

主Qwen错峰：可避免撤回R00→R10为6→17，cohort分别3→7、1→6、2→4；R01唯一总撤回是必要不兼容清除。相应source差有11正、1负、12零。假定speaker符号独立可交换，精确双侧符号概率26/4096=0.00634765625；**同cohort共享一次物理服务调度，不满足已经证明的独立部署条件，故此数仅为条件诊断。** 三个cohort方向相同也不等于大量独立重复；以三个独立交换单位计，全部同向的双侧最小分辨率只能到2/8=0.25。

同主层期限信用的source差：

| 对照→R11 | 正/负/零 | 条件双侧符号p |
|---|---|---:|
| R00→R11 |11/3/10|0.057373|
| R01→R11 |17/3/4|0.002577|
| R10→R11 |10/4/10|0.179565|

所以本轮并没有把所有期限对照都变成“显著”。主三cohort信用交互18.530/6.205/17.555秒，但复用A来源的fresh jitter交互−2.245秒，R11比R10少4.245秒。其余Whisper、sync、coarse的负号、零效应、质量和同G对照缺口，均在 `H3_ALL110_PAIRED_RECOUNT.json` 与先行 `review/HISTORICAL_EVIDENCE.zh.md` 保留。不能只选6→17对应的p值代替完整结果。

## 5. 新8speaker：有限样本精确交换与删去敏感性

只读已经冻结的新8speaker报告，两个fresh重复始终留在speaker内。原主估计+53.2843479pp守恒；枚举全部256个speaker配对策略标签交换，只有全正/全负两个排列达到该绝对统计量，双侧精确p=2/256=0.0078125。它已到8对观测能达到的最小双侧分辨率，不应再显示更小的p或更强总体保证。

| 保留speaker | 所有相应删去子集的coverage差范围 |
|---|---:|
|8，不删去|+53.284pp|
|7，逐一删去，共8种|+52.109至+57.113pp|
|6，逐二删去，共28种|+50.578至+58.713pp|

这说明已测短语音增益不由单个或某两个speaker独占；范围不是CI，不增加新的声学来源或GPU重复，也不回答新长度/新负载的外推问题。交换p依赖speaker层配对标签的零假设可交换性，不能与H3共享cohort的条件符号诊断合并。

## 6. 可复核文件与SHA256

所有路径相对于 `history_ops/results/`：

| 文件 | SHA256 |
|---|---|
| PRIMARY_v1/SUMMARY.json | `7810ef069d36af7db9ddd19715ab81acad2ae3b1cb7b6ca8a003ba9f12254dab` |
| PRIMARY_v1/GATE.json | `c59e7f04290a24cbb7ebfe4789d4ba7fa7563301d9519625cf217bd78ef6b19f` |
| PRIMARY_v1/AGGREGATE_BY_STAGE_ARM_MODE_CONVENTION.json | `ee654bfef724ac532f926b17f4adbe1b70398e8fe77b7169ebd7861af07f54e6` |
| PRIMARY_v1/H3_ALL110_PAIRED_RECOUNT.json | `9ca01756412421571536cd715fb744864fa31e97d052bb77e9b5c7ce8d809ecc` |
| PRIMARY_v1/NEW8_EXACT_PAIRED_AND_LEAVE_OUT.json | `ece61c28940b692719e4978a828319d9d51006c94c740198296284d5c698eb59` |
| INDEPENDENT_v1/SUMMARY.json | `bec4b1660c7583f4284235b29315fddd21c21cfefec79cb80bef918c86639d5a` |

当前决定：**GO作为更准确的内容修订与有限样本证据，NO-GO把LCP关闭量称真实文字删改、把条件p写成独立部署普遍优势、或把本轮CPU分析说成新GPU性能验证。** 用户新增的“已显示后修改字符秒”和“稳定前缀时间曲线”将另列v2合同，不修改这两份已冻结source和结果；未获Root纳入计划前不启动新正式CPU。

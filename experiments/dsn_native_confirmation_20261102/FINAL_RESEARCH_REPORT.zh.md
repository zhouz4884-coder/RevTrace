# RevTrace：严格新8speaker确认与DSN写作收束

2026-11-02。本轮数据、参考、服务、实际轨迹及结果报告已经完整结束。**新八speaker应进入v11正文，成为最终原生实现的主要独立确认。** 它在同一原始反馈任务、同样两完整模型和完整保护路径下，把双期限音频覆盖从40.62%提高到93.90%；八个speaker全部正向，speaker-paired主估计为 **+53.284pp，95%区间[44.769,59.618]**。

这项补强的重要性不仅是样本增加：新来源的选择没有读取模型效果，原程序结果和质量保持，全部32格与实际Consumer得到独立闭环；“同一选定内容更早到达”的证据也从最终实现的原输出中得到确认。现在应停止打开实验分支，集中把这条证据链写成v11。

## 1. 完整执行范围

本轮覆盖了以下已授权工作，未按性能结果裁剪范围：

1. 本地与authoritative历史元数据census，处理重命名/路径/hash别名，排除已记录RevTrace工作中的43个speaker；合并后无未解决AISHELL身份。只在同一官方test split选择来源，没有为凑12人混入其他split。
2. 冻结全部8个符合8–9s元数据条件且未用的test speaker，每人一条完整原始WAV。选择时没有读取新WAV、reference文本或新模型效果。最终8人即该条件下全部8个eligible speaker。
3. ZIP CRC、实际PCM16/mono/16k header、帧长、WAV/PCM SHA与历史碰撞检查全部通过；无裁剪、拼接、重采样或padding。网络Range失败保留后，使用同一已锁member的有界staging字节并重验，没有换source。
4. 真实4f上连续原作者引擎141步，与每个完整输入上两次restored full-step，共282次恢复输入调用，完整状态、原C和返回IDs全等；参考费用单列。
5. 8speaker×2策略×2fresh，共 **32个真实正常服务trial** 完整执行；每策略16trial，原500ms、D2/C8、全部offered与EOS不变。
6. 原c4检查器对32格 **564个选定转移** 完整PASS；原task/quality、Consumer、实际来源与依赖路径闭环。
7. 报告V2保留预定20,000次speaker-paired bootstrap，附加聚合原NN4f已经产生的raw/whitespace同G内容分区，没有新模型或新raw-reader实验。
8. 对旧四speaker matched/resident的544个原offered端点完成固定期限敏感性，原D2/P99/6of8/7of8结果守恒。

最后资源门为 `PASS_GENERATION_BOUND_PROCESSES_AND_CUDA_RELEASED`：32格原PID generation均不再执行，服务controller已退出，CUDA compute owners为空。没有为收束而终止别的任务。

## 2. 冻结、对照与统计方法

实际神经/协议依赖始终为 **NN4f `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`**，其原ASR/Correct/Update、完整状态与资格/持久化/Consumer路径未换成新的预测或代理任务。Conservative与RevTrace均使用两个完整FP32识别—纠错worker、同模型/精度/allocator、同真实learned-C warmup及原2s lookahead。区别是是否允许在条件完整输入上提前执行，并在真实父状态确认后保留原调用。

来源、完整4N矩阵、原期限与统计方案在新效果读取前冻结并归档；每run有完整实际source/manifest/config/environment/raw/summary/gate记录。参考DETAILS、GATE与GENESIS的终结hash先绑定，才冻结服务config。报告代码的实际执行身份另列，未把它或GitHub archiveHEAD当作NN执行commit。

**这次实际完成了每speaker的ABBA。** 使用固定seed20261102在元数据speaker上排列并选择各speaker的r0策略顺序；r1直接取该speaker保存顺序的 `[::-1]`。同一repeat两策略使用相同GPU角色，r0/r1交换primary GPU0/1。完整计划硬核对每speaker的逆序，没有复用旧cost计划的block-parity规则。

独立声学单位是8个speaker；32trial、564转移和每个500ms前沿不增加n。先在speaker内合并两次时序重复。主估计为audio-duration加权的两策略coverage差，第二估计为8个source配对pp差的均值；两者均报告。bootstrap固定为 `random.Random(20261102)`、20,000次、每次有放回采8个speaker，策略与两repeat始终成对。95%percentile区间使用索引 `(n-1)*p` 的线性插值；不裁负差、不换seed或择优估计量。

## 3. 全部32格的主要结果

| 原始端点 | Conservative | RevTrace完整调用保留 |
|---|---:|---:|
| Trial数 |16|16|
| 全offered音频 / s |137.864125|137.864125|
| 原offered前沿数 |282|282|
| 原D2/C8双期限信用 / audio-s |56.000000|**129.460000**|
| Duration-weighted覆盖率 |40.6197%|**93.9041%**|
| 原whole-run D2/C8通过 |0/16|**10/16**|
| 各run Display P99的中位数 / s |5.0266|**1.7623**|
| 各run Display P99范围 / s |3.9559–6.5887|0.8503–3.0736|
| 各run Certified P99的中位数 / s |5.3120|**2.1207**|
| D2 miss（其中EOS） |170（16）|20（6）|
| C8 miss / missing D / missing C |0 /0 /0|0 /0 /0|
| 共同model-drain窗口两板能量 / kJ |95.263|**90.280**|

全部6个RevTrace whole-run失败都保留在16格分母中，原D2/C8没有改绿。10/16与93.90%是不同层级的服务结果：前者是trial双P99门，后者是全部音频时长的双期限信用。

主估计（ratio-of-sums覆盖差）为 **53.284pp [44.769,59.618]**；source均值估计为 **53.451pp [45.083,59.658]**。主量的定义与audio-duration加权端点一致，第二量展示source一致性，不以哪个区间更好看来选择主结果。

共同能量窗口是实际service origin到外部确认物理模型drain，保留了实际在途工作、退出及原Consumer路径；两板总能量降低约 **5.23%**。这是整个固定cohort的节能，不是所有source逐一节能：S0902与S0915的配对能耗增加，原值保留。

### 八个source全部正向

下表每行先合并同一speaker的两次时序重复，单位pp；没有把两次重复当两位speaker。

| 新speaker / utterance | 配对覆盖增益 / pp | RevTrace原通过数 |
|---|---:|---:|
|S0769 / W0190|61.402|2/2|
|S0901 / W0183|61.440|0/2|
|S0902 / W0343|61.289|0/2|
|S0906 / W0197|51.986|2/2|
|S0907 / W0440|47.528|2/2|
|S0912 / W0434|61.111|2/2|
|S0914 / W0456|55.072|2/2|
|S0915 / W0286|27.784|0/2|

最弱source仍有+27.78pp，但没有因此删除它或把其0/2改写成服务全达标。这个结果比再挑一个最好点更有论文价值：完整调用保留的timeliness收益跨八个事前冻结来源一致出现，同时原服务门保留真实边界。

## 4. “相同内容更早”已经有最终实现证据

原NN4f的 `posterior_whole_text_support` 已按每个offeredF的首次实际Consumer行分类；分类使用该行自己的实际前沿 **G**，将整段文字与后来同G的selected Canonical文字比较。新报告仅聚合这些原输出，没有新建normalizer、截取F前缀或用最终EOS替换G。

| 原D2/C8信用的内容分区 / audio-s | Conservative | RevTrace |
|---|---:|---:|
| 首次全文与后来同G selected text一致 |47.000000|**107.161875**|
| 首次全文不同 |9.000000|22.298125|
| 同G参考未知 |0|0|
| 原总信用 |56.000000|129.460000|
| 未获原deadline信用 |81.864125|8.404125|
| 全offered分母 |137.864125|137.864125|

及时且同G全文匹配的覆盖从34.09%提高到77.73%。raw逐码点与仅去Unicode空白两种判据数值完全一致，unknown为0，两套原分区均完整保存。

更关键的是，**全部offered前沿的同G全文匹配计数两臂都是218/282，失配都是64/282，unknown都是0**。因此新的正结果不是总体匹配率、识别准确率或最终文字数量增加；原选定任务不变，而更多匹配的完整内容在原期限内交付。这与论文“将合法工作变为及时、持续的实际服务”的主线直接一致。

两策略及两次重复的最终原任务质量完全相同。按8个独立参考各只计一次，共 **23个字符编辑 /174个参考字符，CER=13.22%**；没有把重复trial变成696个独立参考字符。该质量使用原4f固定whitespace-only协议，后验同G全文匹配与人工转录质量是不同证据。

## 5. 原程序、参考与c4闭环

参考生成真实调用原NN4f：连续原作者engine不在步骤间restore，141个完整边界；每个完整start再做两次restored调用，共282次。完整状态、原Correct选择、返回IDs全部一致。141+282是参考full-step调用账，不是服务trial；加载/内部预热等神经forward总数未被改名为这个数。

参考窗口单列：约347.462s、两板 **87.305kJ**，包括其模型导入/加载/预热/参考与诊断；`actual_serving_runs=0`。该费用没有加入或抵扣服务coverage、服务通过数或共同服务能量。

原c4检查器完成 **32/32、564个durable original transitions** 的实际完整调用与Consumer/refinement核验，最终状态 `PASS_COMPLETE_ORIGINAL_C4_CONFIRM32_TRACE_CLOSURE`。原source身份、选定输入/输出/C/IDs、物理调用来源、原输入时钟与完整Consumer依赖证据均以该终门闭合。每case执行原35项checker controls，不把35×32说成1120种故障。

报告V2的主统计与原V1逐字保持；新增secondary聚合只读原SUMMARY里的raw/whitespace matching/mismatching/unknown分区，逐cell/source/全cohort守恒到原信用和全offered分母。12项正式report controls及全量报告已PASS。

## 6. 旧四speaker敏感性：原D2没有改变

固定C8=8s，在事前固定的display预算0.5–6s、步长0.25s上分析原四speaker matched/resident的544个实际offer/D/C端点；同时保留全有限CDF与source内两repeat配对。没有增加模型调用或把放宽预算当作原服务成功。

| 旧bank | 原D2信用 / audio-s | 原D2/C8通过 |
|---|---:|---:|
|Matched Conservative→RevTrace|30.0→65.821625|0/8→6/8trial|
|Resident Conservative→RevTrace|31.0→64.118875|0/8→7/8request|

每bank每策略分母仍66.33975s；原P99、partialEOS及上述通过数全部守恒。原D2每source配对增益：matched48.43–60.83pp、resident34.87–59.04pp。它显示timely coverage的宽预算左移，并回应结果是否只依赖单个D2截点；两个bank仍是同一四speaker，不扩成8个独立声学样本，也不与新8source池化做主CI。

三张图与完整数值适合artifact；正文最多两句交代deadline稳健性，将空间优先留给新八speaker主结果。

## 7. 真实代码角色与原始结果定位

| 执行角色 | 实际commit |
|---|---|
|历史census/metadata选择|`c95735f0dfefd10c60820830616f579374b91c50`|
|完整音频acquisition|`1a4e129b02e03dba491a1bdcd80de1e585d20f0c`|
|连续original/restore参考generator|`437d7628944076205eaccaea9bdee18964956f7b`|
|实际原始NN/完整协议依赖|`4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`|
|32格服务driver|`d865af11e9a8d6c451146942d1708a8caed8d1d9`|
|生产外部资源/READY/task审计支持|`a13fa0a335529dc188f7e738877a3acd027ce4a7`|
|c4闭环controller|`6d941594ba4240c24fcc8c41baef2d331bfcdebb`|
|原实际c4 checker|`c4dde9ea9c7abf80fae084bc2293e193262c71e6`|
|最终primary+posterior报告V2|`c023ad046e14abf481c0508e70a70fb264a3ea92`|
|旧四speaker敏感性|`92c29c5b1df764496393a66737bf789a84833efa`|

这些是实际执行/分析角色，不能以相邻archiveHEAD互相替代。每阶段的完整manifest、环境、冻结输入与Root noarg/prelaunch收据均在本E的packages/controls与各RUN_RECORD中。

8TB根盘：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9`

原始结果主目录为该盘下 `results/revtrace/dsn_native_confirmation_20261102/`：

- `audio_acquisition_v2/`：原Range、CRC/header/attempt记录、DATA_MANIFEST、SOURCE_RECEIPT；完整8WAV在 `datasets/revtrace/dsn_native_confirmation_20261102/audio/`。
- `short_references_v1/`：连续原程序/恢复调用原记录、REFERENCE_DETAILS（4,973,321bytes）、GENESIS、参考能耗及终门。
- `service_confirmation_v1/`：全部32格原CONFIG、完整facts.wal、actualConsumer/ingress/publications、每Owner dispatch/worker/audit/state记录、原模型power及独立external power、各task/a13审计。
- `actual_c4_closure_v1/`：32case原checker输出、输入SHA守恒与终结scope。
- `report_v2/`：原20,000bootstrap draws、全部source/cell/内容分区CSV、最终SUMMARY/GATE/PAPER_DATA。

本地有界复核入口：

- `confirmation/FINAL_REPORT/PAPER_DATA.json` 与 `SUMMARY.json`；
- `confirmation/SERVICE_RESULTS_v1/SUMMARY.json`；
- `confirmation/FINAL_C4_CLOSURE/`；
- `confirmation/REFERENCE_RESULTS_v1/`；
- `selection/ACQUISITION_RESULTS_v2/`、`METADATA_SELECTION_v2/`；
- `sensitivity/RESULTS_v1/`、`sensitivity/FIGURES_v1/`。

本文另外只读原服务SUMMARY，按策略重新加和16格的offered、credit、通过数、D2/EOS/C8 miss、共同两板能量及selected步数，分别得到137.864125s、56/129.46s、0/10通过、170/20D2 miss、16/6EOS miss、0C8 miss、95,262.640/90,279.610J与282/282步，与正式报告一致。**这是本地数字复核，不是新模型实验、raw-reader重跑或第二次独立GPU确认。**

## 8. 哪些结果真正补强DSN

**第一，新八speaker应替代旧四speaker的小型正常态结果成为正文headline。** 它使用最终4f、严格同split、全历史未用来源、完整预定矩阵和实际ABBA；正效应跨全部source出现，主区间下界明显为正。它把原生接入从“少量开发示例可运行”提升为可复查的独立确认，仍围绕原反馈程序这一同一问题。

**第二，正文应把“原任务保持”与“及时服务增加”紧接着写。** 32格完整state/C/IDs质量相同、c4实际链闭合，随后给出40.62%→93.90%、0/16→10/16。读者能直接判断收益没有靠替换纠错选择、降低模型精度或放松认证获得。

**第三，47→107.161875s及218/282相同是最适合连接意义与创新的内容证据。** 它解释收益是同一选定任务下匹配内容更早，而非多生成字符或提高ASR准确率。与核心R×S反例和whole-view支持条件相接，论文讲的是可信反馈推进时计算/交付资格的协调，而不是又列一组更大的token数。

新8组Full-call对照回答[EL]/[AU]下的原任务提前执行；它不能代替核心R×S对[EL]/[SUP]交互的隔离证据。将这两类实验证据保持互补，是比把所有数合为一个总提升更有说服力的写法。

## 9. v11取舍与停止开分支的决定

建议正文保持一条论证链：**实际兼容进展丢失 → 三种可检查见证与对象动作 → 核心因子证据 → 新八speaker原程序确认/匹配内容更早 → 已接收对象跨producer失败与物理生命周期 → 必要运行边界。**

新八speaker覆盖率/CI及同G内容分区值得正文的主表或主图；source级配对图可承担跨来源一致性。5.23%能耗为辅助系统结果，不应抢走中心论点。

旧resident结果保留artifact，它检验常驻独立请求合同，但复用旧四来源，不能与新8混成额外独立确认。旧negative admission probe没有形成稳定的新策略机会或已实现贡献，没必要在正文再安排一段；原结果与NO-GO完整保留可查。长期no-reset质量/冷恢复等直接约束现有服务承诺的边界仍应简洁保留，不扩成实验目录。

现在停止新增模型、来源、τ网格、pacing或取消机制分支，理由是本稿最高优先的证据缺口已经完成：真实独立来源、原程序严格保持、实际服务增益、source统计、完整内容意义和c4闭环。再横向追加一个模型或调一个更好点，预期收益低于把这些已经成立的事实清晰写入v11。

下一步只做正文与图表整合、引用/claim映射、实际栏宽/灰度/PDF验收及既定GitHub交付。这个决定针对当前论文主线与证据组合，不宣称研究空间达到理论上限，也不承诺DSN录用。

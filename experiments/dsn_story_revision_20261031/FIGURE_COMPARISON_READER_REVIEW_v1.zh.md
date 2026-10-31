# 双臂完整区间 reader 独立预启动审查

2026-10-31。结论：**GO_FOR_FROZEN_REAL_INPUT_EXTRACTION_AFTER_ROOT_SOURCE_GATE**。本审查清除的是 reader/绘图入口的已知静态问题与合成反例；尚未运行实际14个比较输入，也不将合成控制称为真实曲线结果。

范围：`figure_source_dev/extract_comparison.py`、`render_story_figures.py` 的 comparison 路径，以及SOURCE_MAP/CONFIG/24个固定输入的副本与原文件哈希。本审查没有执行真实 reader，没有SSH、原始远端扫描、模型初始化或GPU调用。绘图源的最终独立commit、完整manifest和Root真实preflight由主执行者随后冻结。

## 发现与修正

| 项目 | 初始问题或审查点 | 冻结前闭环 |
|---|---|---|
| 启动入口 | `main` 用 `controls={…}` 遮蔽已导入 `controls()`；实际执行会TypeError | 字典改名 `control_hashes`，原RAM controls函数可调用，前后哈希核对保留。 |
| certified文字与visible文字 | `first_certified_whole_text` 最初取首个cert覆盖行的 `visible_text`；若该行保留更ahead私有视图，就不是选中文本 | 改为 `certified_text`；输出两种实际frontier；另在首次实际view自己的G定位对应Canonical全文，缺记None/UNKNOWN，同G多条歧义拒绝。 |
| 跨臂同文字 | 相同目标F不能证明首次完整视图相同 | 分别输出first-visible/first-certified全文等值和实际frontier等值；caption随真实等值结果写，未预设相同短语。 |
| 结果与实际应用绑定 | 仅有同版本/部分token绑定不足以区分安装文本与ahead文本 | 私有job的target/SID/source、result.text、实际display text/frontier绑定；Canonical原job target/source、token/state、publication.text、Consumer.certified_text和结果text绑定。 |
| 实际输入链 | 复用的vendor函数允许缺少execution audit时回退声明prompt；不能把缺项当额外实测执行证据 | wrapper逐route节点核实 `execution_context_audit.executed_prompt_tokens`，缺项UNKNOWN、实际不等反驳；不静默补0或补相等。 |
| 时钟与截取范围 | 各臂不同物理origin；Publication不能晚于实际Consumer使用；图轴可能截掉较晚cert点 | 各臂独立 `episode.origin_perf + session.offset + F/16000`；实际Consumer时钟finite/顺序检查、实际使用晚于publication；横轴范围覆盖两臂first-certified。 |
| 源身份与输入门 | 原模型、旧提取器、新renderer应分开 | reader明确原NN源f0与原streammanifest；原source/audio/区间一致；新plotcommit只供实际分析/制图身份。CONFIG输入map哈希、24个input、vendor与25个v4保护项前后检查。 |

这些问题在正式真实输入执行前发现并修正，未形成原结果的事后重标或删改。

## 已核实的实现语义

1. **ready clock**：每臂都由自身EPISODE origin加本会话offset、原目标F/RATE构造。代码没有借用另一臂origin，没有以Owner publication代替actual Consumer application。
2. **首个覆盖与全文支持**：`first_cover` 先检查实际Consumer顺序，再找实际frontier覆盖。首覆盖目标F与first-view实际G、整段view文本、Canonical文本分别保存。后验同G比较不等于人工正确性或在线认证。
3. **旧案例一致性门**：只对原R1S0已发表案例断言1.4439057689160109/1.543663284741342/3.7196051217615604秒和2.1759418370202184秒兼容缺口，以及相同全文返回。Joint未设定更早、无gap或相同对象的成功目标。
4. **Joint未被预设为反事实**：两臂实际曲线独立导出。输出 `same_execution_interleaving=False`、`paired_counterfactual=False`；旧案例记载Joint同根无ahead view这一事实不能被实际另臂曲线抹掉。
5. **完整链**：实际已发布complete结果、同source/session/contract/generation、完整state/token/text与执行输入分别核对，前驱必须真实可供子调用消费。缺证据的链保留UNKNOWN，失配保留incompatible，不把所有回撤都画作兼容错误。
6. **结束观测**：完整trace以该source最后一条actualConsumer行为终点；未恢复缺口只到该行右删失，未延伸到SERVICE_END、下个请求或虚构UI存活时间。真实输入可能已完成覆盖，也可能使门失败，审查不预先宣称无删失。

本core路径的 `result.text==display.text` 严格检查有实际代码依据：冻结source_v3 `runtime/src/revtrace/live_qwen.py:538` 原样发布result文本；`certified_display.py:29–32` 先校验trusted-render与result文本一致。因此没有为了过门而放宽为模糊文字或归一化相等。

## 控制与输入哈希结果

- 作者reader的 **10/10** RAM控制通过：独立origin、借错origin的反例、actual首覆盖、逆序拒绝、同frontier异文本、精确文字相等、完整实际输入、失配输入、缺失published节点和缺execution audit。
- 独立构造的 **8/8** 完整arm字典控制通过：兼容撤回后实际返回、ahead visible文本不冒充certified文本、覆盖F但缺实际G的UNKNOWN、plotcommit不能顶替NN源、使用早于publication拒绝、Canonical文字绑定拒绝、jobtarget绑定拒绝，以及必要不兼容撤回分类。
- 这些控制只构造内存字典。没有打开实际测量JSON来运行reader。记录和独立控制源码为 `FIGURE_COMPARISON_RAM_REVIEW_v1.json` / `review_comparison_ram.py`。
- 24个副本input与其原始bounded文件逐项bytes/SHA一致；14个source7文件另与旧下载inventory匹配；1个vendor依赖与原文件一致；25个v4保护项未变。记录 `FIGURE_COMPARISON_STATIC_PIN_REVIEW_v1.json`。这属于身份检查，不是第二次实际结果提取。
- 已审reader SHA：`c458188376071f94cedcaded017987a3d0a296cc21fdb5201bf787e731e7283b`。若冻结前后科学reader再次变化，须针对差异复核，不能把本GO无条件迁移。

## 正式结果回来后必须再看的内容

本审查不预先报告Joint的D、C、全文同值、缺口数或兼容保留率。应只读正式 `ACTUAL_INTERVAL_COMPARISON.json`，核查两臂实际G、首次全文与选中全文及原曲线，对照输出事件/输入hash；必要时复核哪些gap真实兼容、哪些为必要撤回或UNKNOWN。caption和主文应按实际结果解释，也允许Joint没有相同ahead机会或更晚显示。

图3的native内容分解来自另一批final4f日志，不把此f0 core案例转移为native4f或24-speaker独立确认的新证据。正式绘图产物的数值与视觉QA及原source gate仍需完成；本报告不是最终PDF逐页视觉验收。

## 正式实际输出复核：已完成

独立结果QA：**PASS_INDEPENDENT_EMITTED_COMPARISON_OBSERVATION_QA**，记录为 `FIGURE_COMPARISON_ACTUAL_RESULT_REVIEW_v1.json`。实际提取source为 `73026a11f6db202d723e6028ad85e6833888ec78`，原NN仍f0；实际输出 `FIGURES_v1/ACTUAL_INTERVAL_COMPARISON.json` SHA为 `7df3c385a14c8842f745a66c8fb4f3635fee7cd916aad6d1e23af7cfdc80fd94`。

这一步只回读已输出JSON和冻结副本的对应观测/单节点证据，没有再次调用通用实际输入reader。33个完整源码快照、24输入pin匹配，两臂各21条实际Consumer观测逐点与原行的相对时间、frontier和全文SHA对应；首显/首cert行及自身ready origin、实际G、全文值和最后观测全部相符。

| 实际观察 | Computation retention only (R1S0) | RevTrace joint (R1S1) |
|---|---:|---:|
| 首次覆盖原F14区间 / s |1.4439057689160109|2.0274376049637794|
| 首次Canonical覆盖 / s |3.7196051217615604|3.7943886145949364|
| 首显实际G / audio-s |14|14|
| 该区间原D2/C8 |pass / pass|fail / pass|
| 首显后F14缺口 |2.1759418370202184s，实际兼容撤回|0个实际窗口|
| 最后实际同源观测 / s |8.439693992957473|8.327894708141685|

两臂首次完整文字、首次Canonical完整文字四者精确相同，各自同G14后验比较也相同。**Joint首次显示比D2晚27.4376ms**，必须在图注/邻近文字保留。它没有F14首显后的后续缺口，不等于它避免了另一臂相同墙钟交错的缺口；Joint在原F12安装时没有那个ahead对象。不能以这一对图宣称Joint在该区间首次交付更快或提高其期限信用。

### Joint自身的一次确切R/S见证

以下索引相对冻结输入副本 `figure_snapshot_v1/inputs/R1_S1_*.json`，数组索引为0-based。它发生在Joint自己的Canonical F14更新，而不是原计算单开臂的Canonical F12更新。

- `CONSUMER.json[14]`：实际display，observed_perf `4930925.372114137`，Canonical F12，实际whole view F16。
- `CONSUMER.json[15]`：实际canonical-display，observed_perf `4930925.702125338`，Canonical从F12到F14，实际whole view仍为F16。前后274个code points完全相同，全文SHA `8d4803fe0f578ab6aab20e1245d808d961b13548e17d42be62843d61188a92db`。这不仅依赖行中 `compatible_provisional_retained=True` 标记。
- `EVENTS.json[173]`：`private-continuity-proof`，witness为 `proposal-7-205` 和 `proposal-7-228`，frontier224000/Canonical version7，branch_generation1。
- `[174]`：`verified-private-prefix-retained`；`[175]`：原commit version7；`[176]`：对应Canonical publication。实际Consumer在其后应用。
- `WORKER_RECORDS.json[12]`：boundary job `proposal-7-205` 的完整目标是F14；其完整output state tokens与实际新选中P相同。
- `[13]`：successor `proposal-7-228` 从chunk7启动并完成F16；实际executed prompt、声明prompt、boundary205完整输出以及commit175的新P四者相等。同一generation1，boundary end_window7与successor start_chunk7连续。

实际/声明/新P的token-array SHA均为 `65617c2cef76661d5511360dd13dbe738c032d4f36235ac77375332b1582e682`（JSON紧凑数组编码）。这为“Joint在自己的兼容F14更新上保留已有F16计算和整视图”提供具体记录；不与首显F14无gap或另臂F12缺口互换。

可用英文解释：

> In the joint run, an already visible 16-s whole hypothesis remains unchanged when the selected frontier advances from 12 to 14 s. Its complete boundary output equals the newly selected feedback state, and the successor consumed exactly that state. This witnessed retention is separate from the 14-s interval's first-delivery deadline, which this run misses by 27 ms.

### 整体绘图门与实际提取门保持分开

第一次整体render命令 **exit1**：比较图的4.5刻度超出已固定的坐标范围。前五张图和实际提取输出已经生成；这不允许把原CLI改写为通过。上述数据QA只覆盖已发出的真实观测与绑定，原失败须保留。后续v2只能按其实际新source身份重绘并复用已固定比较JSON；它的plot PASS不回写旧CLI，也不算第二次模型/旧日志扫描。

另发现比较图原ymax15.1会裁掉Joint在图内时段的F16真实视图；已要求绘图者统一两面板可见范围至至少16.5并保留F16刻度。最终图面、灰度、版面和全页PDF仍由Root实际审阅，本数据QA不替代视觉验收。

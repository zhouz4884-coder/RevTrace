# 被主结论掩盖的强证据与尚未补上的实验

2026-11-11，先于本轮新实验的只读审阅。本文核对已有有界 JSON、正式报告和执行合同；没有启动新 GPU、正式 CPU 重计、假设检验或模型调用。配套 `HISTORICAL_EVIDENCE.json` 保存原值摘录、具体 cell/source 身份与输入 SHA256。以下是历史证据的重新核对，不是本轮新实验结果。

## 1. 首要发现：正确的可避免撤回比较是 6→17

H3 独立 24 speaker 主分层，Qwen/rho1/staggered，五臂各三 cohort、每臂 offered 714.110 秒：

| 臂 | 总撤回 | 可避免兼容撤回 | 必要不兼容撤回 | 双期限信用 s | 兼容机会保留/总机会 |
|---|---:|---:|---:|---:|---:|
| R0S0 |12|6|6|654.115|0/6|
| R0S1 |1|0|1|628.435|4/4|
| R1S0 |17|17|0|664.150|0/17|
| R1S1 |0|0|0|680.760|18/18|
| Standard complete positive control |0|0|0|667.530|15/15|

证据不是从文本或音频倒退猜兼容性：`physical_retirement_20261028/H3_RESULTS_v2/opportunities/SOURCE_OPPORTUNITIES.json` 有 `clock_scope=consumer_apply` 的完整依赖链判定。`COMPACT_TABLES.json` 和 `aggregate/RUNS.json` 给出总撤回、信用和 cell 身份。Owner 与 Consumer 两种时钟不能算双倍机会。

具体到 cohort：

| cohort | R0S0 可避免/必要 | R1S0 可避免/必要 | R0S1 可避免/必要 | R1S1 可避免/必要 |
|---|---:|---:|---:|---:|
| A |3/4|7/0|0/0|0/0|
| B |1/1|6/0|0/1|0/0|
| C |2/1|4/0|0/0|0/0|

所以三个 cohort 的可避免撤回都随仅计算保留增加，分别 3→7、1→6、2→4。不能把这当成 24 次独立部署、或用 368 个更新作独立统计样本。原来 12→17 混入了基线的六次必要修订，但修正后不削弱反直觉机制，反而更明确。

**R0S1 唯一撤回已定位：** cell `primary-qwen-rho1-staggered-CB-R0_S1-r0`，session 6，source `composition-5456-24741-0003-0007`。判定 `incompatible_ahead_updates=1`、`incompatible_cleared=1`，原因 `private_feedback_boundary_precedes_selected_root`；该行 `compatible_cleared=0`。其余四个兼容机会全部保留。

这条对照比单独“联合归零”更有信息量：**视图保留自身已能消除这组可避免撤回，但及时信用较低；联合设计同时保留及时计算和兼容视图。** 因此不能主张“两个因素都是实现零可避免撤回的必要条件”。R0S1 是实测的反例。真正值得解释的是及时性与连续性的联合目标，而不是再增加防御性限制语。

## 2. 主分层不是唯一证据；完整 110 格包含强的相反工作点

110 cells = primary60 + paired-jitter20 + coarse30，共22个完整五臂块。独立声学内容始终24speaker/24source/714.110秒，880个source/run行不增加独立 n。paired-jitter只复用cohort A八人。完整明细见配套JSON中的 `all110_existing_strata`，不能只看主分层总和。

以下引用既有正式阅读中的 U_norm，即首次双期限信用与后来实际同 G 全文相符的交集；不是语义正确率或在线认证。rho3缺同G对照时不能把原期限信用冒充U。

| 层/模型/arrival | R00 | R01 | R10 | R11 | Standard | 四臂交互 I |
|---|---:|---:|---:|---:|---:|---:|
| primary Qwen sync |708.465|705.110|712.230|711.440|711.440|+2.565|
| primary Qwen staggered |654.115|628.435|664.150|680.760|667.530|+42.290|
| primary Whisper sync |412.000|414.000|412.000|412.000|419.320|−2.000|
| primary Whisper staggered |422.000|424.000|422.000|422.000|448.790|−2.000|
| jitter Qwen sync |239.355|239.355|238.565|238.565|238.565|0|
| jitter Qwen staggered |216.000|214.000|230.565|226.320|227.300|−2.245|
| jitter Whisper sync |156.000|156.000|156.000|156.000|157.320|0|
| jitter Whisper staggered |168.000|168.000|166.000|166.000|164.000|0|
| coarse Qwen sync |227.570|227.790|231.450|231.450|231.450|−0.220|
| coarse Whisper sync |92.010|92.010|92.010|92.010|92.010|0|

入口：`physical_retirement_20261028/analysis_tools/H3_INDEPENDENT_READING.zh.md`，其逐源/逐cell输入为 `H3_RESULTS_v2/{aggregate,usefulness,opportunities}`，并非图上读点。原期限信用与U数值在主Qwen错峰相同，在其他层并不总相同。

主Qwen错峰三个cohort交互 +18.530/+6.205/+17.555秒，方向一致；但同一A来源fresh重复交互 −2.245秒，R11比R10少4.245秒。逐speaker主层R11相对R10的改善/相同/变差是10/10/4，相对R00为11/10/3，均不能写逐源支配。15/15主分层cell的Display P99>2秒，不能把95.33%信用写成整场通过。

Whisper也不是一个应藏起来的失败臂：rho1 Standard有更高期限/同G支持信用，却有27/32次音频撤回；R11两arrival均零撤回。这是可读的期限—连续性权衡，不是全面胜负。fine Whisper pooled WER83.12369%是整个反馈任务边界，所有策略共享相同历史，不能归因于Consumer。

**实质补强机会：** 将既有22块全部展示为条件效应和相反工作点，而不是只为12→17加一个不可靠的小样本CI。全110格的paired块、source和兼容/必要事件都可达；需要按原speaker/cohort服务依赖解释，不能把小窗口当独立样本。

## 3. 另外两层历史复现应并列，不能混池

### 当前core开发池36+12格：连续性有真实区间终点

`dsn_service_stability_20261028/RESULTS_FINDINGS.zh.md`：旧16speaker开发池三个工作点×四臂×三fresh，共36双GPU格。c16错峰R-only兼容撤回16/17/12，联合0/0/0；R-only每次都有，不是单个总数。R11相对R10信用差 +18.910/+5.055/−7.225秒，交互 +20.910/+26.380/−9.575秒。因此连续性方向稳定，额外期限收益非每次为正。全部36格74次音频撤回恰分60兼容与14不兼容，other-triggered为0。

`dsn_manuscript_update_20261028/timely_continuity_v1/README.zh.md` 是另外冻结的post-hoc secondary CPU分析，原offered、D2/C8、质量与首次credit不改。c16 R-only撤去已及时合法进展的事件10/11/9，原D2读点缺失6.000/10.675/4.000音频秒；相应单root缺失面积24.903/23.635/15.736 audio-s×wall-s。联合全部为0。最强反例是r2：R-only首次credit比Joint多7.225秒，却仍有4秒已记credit的音频在D2读点缺失。这直接证明首次交付与持续可用性不能互相替代。

低负载c8错峰所有四臂三次整场P99通过，但R-only仍有1/2/1次及时兼容撤回；并非只能在所有策略均过载的点展示该问题。绝对面积很小，应照实显示。

`dsn_midpoint_continuity_20261029`另有唯一c12错峰12格，共48格合并表见 `COMBINED_DATA_v1/RUN_ENDPOINTS.json` 和 `dsn_story_revision_20261031/CORE_PRESENTATION_AUDIT_v1.zh.md`。c12全部D2失败；R-only secondary windows1/1/3但强完整2秒非EOS见证为0/0/0，不能把小窗口说成不存在，也不能事后把阴性中点删除。它们仍是旧开发来源，不能充当H3或新native的独立新speaker。

### Phase D：受控机制复现与更早执行合同

本机实存入口为 `dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/FINAL_RESEARCH_REPORT.zh.md`，原根下 `experiments/phase_d_20261021` 不在本次本地树中。该归档报告的最终runtime为 `2a4b56bc5d8dcbf3884f03f8213f9c39101f59f8`，不能用当前f0/4f标签替代。

Fine匹配因子三fresh：Neither撤回67/61/77，view-only20/24/24，compute-only93/77/77，joint0/0/0；固定选定内容的hold干预12/12配对使回撤率增加。这支持时序与组合机制的可重复性，但旧表没有在本轮逐事件重分必要/可避免；不能直接把这些总数叫可避免撤回，更不能合并进当前6→17的统计分母。Standard Safe Async在旧合同中有相近结果，必须保留强正控身份。

## 4. 文本端点：有三个不同数据银行，不能把新数字搬错对象

1. **H3 headline569**：主Qwen错峰R11的 `erased_visible_characters_sum=569`，代码为LCP后缀关闭量；Standard同为569，R01为524。它不是最少编辑数，不是错字数，不说明文本永不修订。正式来源为H3原Consumer日志与 `COMPACT_TABLES.json`。
2. **native old14**：`dsn_native_content_20261029/RESULTS_v1/RUNS.json` 的2个witness与12个formal必须拆开。正式四cell/臂：Sequential引入184/LCP关闭0/最后184；Drop206/22/184；Joint241/57/184。Joint两个开发witness另121/29/92，不能拼进正式比较。`LCP_OCCURRENCE_SPANS.json`有literal文字与寿命，`ACTUAL_TEXT_EVENTS.json`只有全文hash、时间和LCP计数，不含每行完整文字。
3. **final NN4f与新native8**：原SUMMARY已有实际首显示G与后来同G完整selected transcript逐字比较。新8speaker每策略282offered前沿，match218/mismatch64/unknown0完全相同；但在原D2/C8内匹配的音频信用47.000→107.161875秒。这证明同一任务下匹配内容更及时，不证明准确率提高。旧final4f matched为22.5→51.0秒，resident为24.0→50.2590625秒，不能与新8speaker池化。

第三项入口：`dsn_native_confirmation_20261102/FINAL_RESEARCH_REPORT.zh.md` §4；定义在该目录 `review/CONTENT_REUSE_DECISION.zh.md`。旧final4f入口为 `dsn_writing_closure_20261031/FINAL4F_CONTENT_RECOUNT_REPORT.zh.md`。

**外部粘贴的新Levenshtein表尚未在本地正式结果中找到对应可运行报告。** 所称Sequential179、Drop206、Joint279及41删+19替不能直接覆盖H3的569：两者本来就来自不同银行。另有算术警报：正式Sequential最终184码点、从空文本开始且没有删/替时，累计插入必须等于184，不能是179。若179用了不同文字变换或漏首行，必须明确并重新核对。

寿命也不能混接。LCP某次后缀身份关闭会包括仅因中间插入而移位、实际未改的字；真正edit删除/替换字符的寿命是另一条身份轨迹。不能把“22个LCP身份已显示≥2秒”说成“60次实际删/替中的22个”。Levenshtein最优对齐可能不唯一，需要公布tie-break、事件ledger和敏感性范围。

**值得做的新CPU实验：** 对同一完整actualConsumer序列从空文本起独立计算Unicode码点最少编辑，分别列I/D/S、真实edit身份寿命与LCP身份关闭；新三策略直接复用同一离线reader，不增加runtime callback。H3主层与native正式12应分别跑，不用old14替代569。每格硬核对 `I−D=最终可见码点数`、`I+D+S=总编辑距离`，重复/开发witness/归一口径不混合。准备源在 `../history_source/`，尚未运行，不能称已取得新结果。

## 5. 真正漏掉的研究机会，而非仅补几个限制句

| 优先级 | 现有强证据 | 它已经回答什么 | 还需要什么才能改变审稿判断 |
|---|---|---|---|
| P1 | 可避免6→17，三个cohort同向；R01零可避免但期限较差 | 计算与视图是不同对象，联合目标不能只报withdrawal | 现有22块完整再呈现；新增自然来源/同期竞争策略回答适用范围 |
| P1 | c8整场P99通过仍发生及时合法撤回；c16r2首次credit更高仍D2读点缺失 | continuity有独立服务意义，不是新术语 | 保留原区间ledger；新三臂用同一指标核对，不更改原credit |
| P1 | 218/282两臂相同但47→107.162及时同G全文信用 | 性能收益没有靠改变最终任务/匹配比例 | 同三臂量化及时支持信用与实际文字修改代价的权衡 |
| P1 | H3 569是LCP，old14正式/开发可拆，外部179出现守恒冲突 | 旧“擦除字数”含义不准确，新表也需独立验证 | 冻结独立CPU编辑/寿命reader，逐事件可审计，不拼不同银行 |
| P2 | H3 jitter反号、Whisper更高期限/更多撤回、rho3缺同G对照 | 时序和任务合同会改变收益条件 | 新独立speaker按metadata长度层冻结；无需把旧110格包装大n |
| P2 | 当前90个S-on历史重放joint34与正控22均无额外selector机会 | 一般Max-history查询不是当前有证据的缺口 | 不因历史14正时点再盲加模块；若新负载出现残余再开实际对照 |

历史selector入口：`dsn_continuity_cost_20261102/FINAL_RESEARCH_REPORT.zh.md`。旧三条轨迹14段、20.77294会话秒是零额外选择/应用延迟的离线机会；当前唯一残余在一个R0S1运行两段1.72585秒，不能拿它推销当前joint新算法。该结果应防止把有限GPU预算耗在已有阴性的分支上，而不是阻止新的强竞争基线。

以上足以让导师先判断“已有强证据到底在哪里”；R1新三策略服务与Q21真实故障成本仍需其他子任务的独立执行。本文不宣告论文问题已关闭，也不把重新整理旧证据冒称本轮补强实验完成。

## 6. 外部新报告的本地可达性

对本工作树做精确路径检查，`experiments/dsn_review_response_20261111` 及其 `reproduce_frozen_audit.py` 均不存在。对用户Downloads、Documents及Codex attachments的文件名检索，仅找到本次已读导师审稿文件；未找到题为“RevTrace v16 实质补强与三策略实验执行方案”的独立下载文件。粘贴文本第698行只有下载标题，没有可读取的附件路径或实际URL。因此该方案的详细条款不能假称已经读取，声称脚本exit0或新Levenshtein结果已复现也没有本地依据。

这只说明上述本地范围内不可达，不证明文件从未生成，也不是对当前GitHub链接的联网核验。现有导师意见与706行粘贴文本均已实际读取；它们是待核查意见与历史数字线索，不能替代可解析执行commit、冻结配置与原始结果。

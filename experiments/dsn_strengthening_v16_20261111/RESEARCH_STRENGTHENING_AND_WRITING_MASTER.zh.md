# RevTrace：导师评议后的补强总记录与正文决策

本记录覆盖**阅读导师AI审稿意见之后**的完整工作链：重新检索旧仓库找回的有用证据、所有新CPU/GPU实验、失败与修复、建议的采纳／不采纳、未启动方案，以及正文怎么写。它不是主文目录，不要求把全部实验塞进论文。逐项身份、路径和哈希以实验登记表及原始gate为准。

**当前收束决定：** 用户已明确要求停止继续扩实验，完成正在运行的最后16格后转入正文重写。没有批准新的NN4、模型训练、调度分支或新语料GPU扩跑。必要的现有结果统计、审计、制图、编译和版面检查继续进行。

## 0. 接续入口与状态优先级

- [逐实验登记表](EXPR_REGISTRY.zh.md)：人读索引，按实验组／GPU子cell两层列出全部记录。
- [机器登记JSON](EXPR_REGISTRY.json)、[可筛选CSV](EXPR_REGISTRY.csv)：实际experiment ID、执行commit、config/env/raw/summary/gate、镜像路径与缺项；重复镜像去重，不把controller再算一个GPU cell。
- [运行接续检查点](EXECUTION_CHECKPOINT.zh.md)、[当前工作状态](WORKING_STATE.json)、[时间戳进度](LIVE_GPU_STATUS.json)：旧快照可能落后，终门和最新同PID/start_ticks实况优先。
- [最初交付的强证据清单](MISSED_STRONG_EVIDENCE.zh.md)、[后续新证据摘要](NEW_EVIDENCE_AND_EXECUTION_DELTA.zh.md)。

**最终闭合更新：** 已完成56个真实服务GPU cell：六策略pilot24＋同资源多会话8＋新增两source确认8＋最后4source确认16。另有两个真实GPU原任务参考campaign，合计141连续step、282恢复step和2次warmup，参考step不算服务cell。全部controller已结束、GPU已释放，不再追加研究实验。CPU版本控制203/214/225、driver50/56等有重叠，不能相加冒称独立测试规模。登记表共87条闭合记录（56服务子cell＋31容器／CPU／metadata），没有活跃或未观测子cell。

当前实际NN为`de0936b2e30179d63aeef6e235cd1af685578c58`（66文件）；pilot/reference controller为`f367c4e1068a9391a0e99d8537c94995a3388e13`；后续两臂controller为`4fb6d05f1cf4ad80e73bae9934afaed04c60edeb`。GitHub归档commit不是这些实际执行commit。legacy dirty根HEAD `7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f`保持不变；不得pull/reset使出处看起来更新。

## 1. 研究目标与不能再丢的判断

目标是DSN Regular论文，核心是**可信反馈修订时保留仍合法的计算与实际可用进展，同时保持原反馈选择任务**。创新可以是已有方法在新问题上的适用条件、必要协调、实现与新发现；不要求每个原语从零发明。

不能因为作者构建的强控制复现了完整组合，就说别人已经做出了这个组合。也不能把强控制追平解释成全部系统机制失效。需要识别：对照共享了哪些已提出的义务和实现，真正改变了哪一项规则，哪一项增量尚未观察到。

“每补一项证据就扩大一次主张”会使研究永远不收束。后续正文只承诺已有证据能回答的问题；不能为争取某一算法独占胜利不断换负载。AI给出的4/10、5–6/10不是经过录用校准的接受概率。

## 2. 从旧仓库找回、值得保留的证据

### H1：首次交付达标仍可丢失合法进展

第一幅动机图的真实轨迹有2.176秒已交付合法进展缺口。更重要的补回证据是：开发c8错峰点12个cell全部满足整场P99期限，仍出现1／2／1次兼容更新下已及时交付内容缺失，joint为0。它说明问题不只来自严重过载。

开发c16的D2读点缺失分别为6.000／10.675／4.000音频秒；对应缺失面积24.903／23.635／15.736音频秒×墙钟秒。第3重复中，compute-only的首次信用反而高7.225秒，但读点仍缺4.000音频秒。**首次到达信用和持续可读性不能互相替代。** c12探索点与负号也保留，不做自然流行率推断。

出处：[历史证据复查](review/HISTORICAL_EVIDENCE.zh.md)、[机器提取](review/HISTORICAL_EVIDENCE.json)，原`dsn_service_stability_20261028`与`dsn_manuscript_update_20261028/timely_continuity_v1`。

### H2：核心严格2×2，真正的组合权衡

主Qwen/rho1/staggered层：24个speaker，3个cohort；每臂offered714.110音频秒。

| 臂 | 双期限信用/audio-s | 总撤回 | 可避免兼容撤回 | 必要不兼容撤回 |
|---|---:|---:|---:|---:|
| R0S0 |654.115|12|6|6|
| R0S1 |628.435|1|0|1|
| R1S0 |664.150|17|17|0|
| R1S1 |680.760|0|0|0|
| alternative joint正控 |667.530|0|0|0|

最有力的现象是**可避免撤回6→17**，不是混合性质的总数12→17。S-only已经消除了可避免撤回，却少25.680秒信用；joint同时达到更高信用和低撤回，不能说只有joint才能零可避免撤回。

主三个cohort信用交互18.530／6.205／17.555秒，原speaker bootstrap平均+5.90pp、区间[+1.13,+10.28]。全110格为22个五臂块，不是110个独立声学样本；复用A来源的fresh jitter交互−2.245秒，joint相对compute-only少4.245秒，sync也有收敛或负差。15个主headline cell的D99均超过2秒，不能把95.3%覆盖写成该层全部整场达标。

出处：`physical_retirement_20261028/H3_RESULTS_v2`；本轮[全110格配对复算](history_ops/results/PRIMARY_v1/H3_ALL110_PAIRED_RECOUNT.json)、[完整CPU报告](history_ops/HISTORY_CPU_RESULTS.zh.md)。

### H3：内容证据比LCP后缀量更强、更具体

本轮重读29格原始实际Consumer，第二实现独立检查26,076条观察与操作证明。核心主层实际最优码点对齐如下：

| 臂 | I/D/S | D+S | 修改前曝光/码点秒（主／第二对齐） | 原LCP后缀关闭 |
|---|---|---:|---:|---:|
| R0S0 |10678/103/47|150|175.635／247.988|633|
| R0S1 |10577/2/47|49|135.565／209.206|524|
| R1S0 |10794/219/48|267|203.297／276.509|808|
| R1S1 |10577/2/47|49|134.207／208.373|569|
| alternative joint |10577/2/47|49|130.894／204.093|569|

compute-only→joint：D/S修改267→49（−81.65%），曝光203.297→134.207（−33.985%）；另一最优对齐也改善（266→48、276.509→208.373，−24.642%）。信用同时多16.610音频秒。同源最终actualConsumer全文hash相同，不只是相同长度或WER。

旧native正式12格必须单列：Sequential184/0/0，Drop188/4/16，Joint223/39/12；其修改曝光0／13.423／82.027码点秒。更早显示临时内容会承担更多合法修订，不能拿H3的改善替换此bank。开发2个witness不混进正式12格。

569是LCP后缀身份关闭，不是569个实际删改字。WER26/1908的分母是词，不是码点。外部179/206/279及“仅2个已显示≥2秒修改”未在相同完整范围复现，不能采用。曝光身份依赖对齐，属于展示活动代理，不是人工阅读／用户满意度实验。

出处：[最小编辑与统计报告](history_ops/HISTORY_CPU_RESULTS.zh.md)、[曝光／稳定前缀／最终全文报告](history_ops/EXPOSURE_CPU_RESULTS_v2.zh.md)。

### H4：旧四来源真实在飞计算及完整资源账

旧4 speaker、16 cell，BDFA执行源，与后来的8source NN4f不同。92次真实跨出生版本保留均有原模型执行，实际模型路径覆盖父确认时刻；20次该调用对自己后继的预测与实际结果不同，不能把输入合法等同于认可预测。

整call占用69.016526 worker秒／68.308115同步infer墙钟；真正父receipt→install确认边界之前已投入的worker工作22.428636–24.487472秒，infer区间21.865507–23.924343秒。69秒不能全部称确认前节省的GPU计算。23.779087秒是固定推理成本重启代理，不是观测到的因果完成延迟节省。

24次before-C退出共12.573526 worker秒，已执行ASR，infer计时缺测不是0；另2次完整后拒绝0.941216 worker秒。两次同位置late拒绝的父模型结果分别在原before-C检查点之后至少6.739／70.530ms才形成，不能只说更快发同一hint即可赶上原检查点。后置复查或新安全检查点是未测候选，不一概排除。

完整298job预算：Conservative136派发＝136安装；spec162＝136安装＋24退出＋2完整后拒绝，全部ready/inflight/lifecycle余项闭合。总worker占用87.194→104.676秒（+20.05%）；信用37→66.33975，信用/占用worker秒+49.35%；及时且后见同G全文支持的对应生产率+47.98%。它是原始闭环服务结果的资源生产率，不是GPU活跃时间或service-wall goodput。

出处：[正式资源账](history_ops/LEDGER_CPU_RESULTS_v2.zh.md)、[独立复核](review/LEDGER_v2_INDEPENDENT_REVIEW.zh.md)、[完整预算派生报告](history_ops/LEDGER_FULL_BUDGET_DERIVED_v1.zh.md)。

### H5：既有独立8source、质量与有限样本证据

此前NN4f新8speaker确认：dual-deadline覆盖40.6%→93.9%，整场0/16→10/16；paired gain53.284pp。两策略后见同前沿全文匹配计数218/282相同，及时同G支持覆盖47.000→107.161875音频秒；最终CER23/174＝13.22%，selected trace相同。

本轮枚举全部256个speaker配对标签交换，双侧2/256＝0.0078125；重复保留在speaker内。删去任一人仍+52.109至57.113pp，删去任两人仍+50.578至58.713pp。它们是有限样本敏感性，不能当新GPU实验、总体保证或把条件检验与共享cohort独立性混合。

出处：原`dsn_native_confirmation_20261102`，本轮[精确配对与删去表](history_ops/results/PRIMARY_v1/NEW8_EXACT_PAIRED_AND_LEAVE_OUT.json)。

### H6：历史外部策略资产已经存在

Phase D已经有来源署名的LocalAgreement2/3显示策略适配与Standard Safe Async。归档`dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/FINAL_RESEARCH_REPORT.zh.md:78`及`R3_BASELINE_SOURCES.md:3–5`明确记录：早期LA等待时错误清空已确认文本，旧12个LA GPU cell无效；修复并全部重测。无词音对齐时稳定词前缀音频覆盖只能给保守下界，不能借此宣称原生Whisper-Streaming容量失败。

因此不再说“从未实现过任何有来源的对照”；也不把此历史适配等同最终递归纠错原任务的完整外部系统复现。当前新LA2-CP是后续独立离线适配，不是首次发明LA。

### H7：形式化与恢复的补回证据

旧手写Python/dataclass BFS规格：normal2frontier/max3issued/depth12为6,231状态／11,142边；failure1frontier/max2issued/depth12/max1fault为14,074／25,799；存在depth cutoffs，未声称穷尽无界系统。27named controls不是27个一般定理。本轮新增8个phase/action控制后35项PASS，36,941条动作边核查。

重要修正：installed Canonical是已验证durable prefix，不必等于durable tail；sync成功与install之间允许有真实间隙。before_commit结果不确定冻结进一步写，恢复重放持久事实不产生新的神经计算。

旧Owner-after-durable四格首个新调用不仅都是32000→40000音频samples，完整父cut与音频slice也逐字节相同。RevTrace旧两次比Conservative慢17.385／17.906秒，其中97.52%／98.25%落在Owner start→ready；ready→new fact约0.7秒且接近。模型构造发生在coordinator创建前。不能把旧差距归为固有算法税，也没有证据证明页面缓存就是原因。

已查到Whisper原loader GPU checkpoint→CPU参数→GPU可能有多余转移，尚未实际比较CPU-map loader。当前PILOT24提供了额外fresh启动观测，但未完成新的受控Owner恢复／page-cache／loader实验。旧轻renderer恢复是RevTrace和Standard共享的旧事实可见性改进，不是exclusive scheduler胜利。

出处：[形式化/恢复机会](review/FORMAL_RECOVERY_OPPORTUNITIES.zh.md)、[新35控制结果](review/FORMAL_RECOVERY_CPU_RESULTS_v1.zh.md)、[加载诊断合同](review/LOADER_CONTROL_REVISION_v2.zh.md)、[C1动作备忘录](review/C1_ACTION_INVARIANT_MEMO_v1.zh.md)。

## 3. 导师评议后全部新实验：分组总账

下表是阅读导航；精确ID、全commit、config/env/hash、raw/summary/gate、每个GPU子cell都在[完整登记表](EXPR_REGISTRY.zh.md)。不以成功结果替换失败版本。

| 组 | 工作／状态 | 科学与交付定位 |
|---|---|---|
| P0 历史证据清点 | 完成旧报告、源码和原始有界提取；先交付强证据后开新实验 | 不算新GPU；用于找回主张依据与避免混bank |
| CPU baseline v1/v2/v3 | 203／214／225控制PASS，实际源2353815／14ae77／de0936 | 累积版本，不相加；v2增safe UIR与receipt时刻，v3共享canonical-first RR |
| CPU disjoint accounting | 9控制PASS，11e639 | promotions是注释，安装/拒绝/退出/生命周期/ready/inflight互斥闭合 |
| CPU pilot driver v1/v2 | 50／56控制PASS，2fac／f367 | 新实际NN参考不可改旧4f标签；full4→预定first2精确绑定 |
| CPU entry route | 实际24配置路由PASS，948f363 | 新f367只走resilience_trial；旧三臂stage/campaign存在但不执行，不能简单扩旧assert混成不同任务 |
| CPU action/formal | 35控制PASS，aa9db5 | 27旧＋8相位动作；有界，不冒充全程序机械证明 |
| CPU content/history | 主16控制＋独立3控制PASS，91cd94／196b116 | 29Consumer、26,076事件，编辑操作/守恒/配对复算 |
| CPU old-native resource ledger | 6控制PASS，817ebb | 16格、136输入文件、298jobs；完整成本与确认前投入分开 |
| CPU exposure/prefix | 主6＋独立6控制PASS，fc096…／52352… | 888身份组面积守恒、8,692曲线行、56跨臂末文组相同；全commit见registry |
| CPU current assets v1 | **失败保留** | checker把resolve实际路径与未resolve期望路径比较，同Python symlink误拒；无模型，权重核验未开始 |
| CPU current assets v2 | PASS，3fb195 | 31declared assets＋8WAV全字节、包版本、GPU拥有者；约15.85GB核验会暖页缓存，不叫冷加载 |
| CPU grouped resource driver v1 | **失败保留**，cd958 | 合成fixture缺speaker_id；不是实际模型失败 |
| CPU grouped resource driver v2 | 5控制PASS，7b83 | 真实OS Pipe、2/4source Owner/Consumer/WAL多源审计 |
| CPU focused controller v1 | **失败保留**，0d8969 | 裁剪包遗漏共享测试fixture，保留导入失败 |
| CPU focused controller v2 | 10控制PASS，4fb6 | 新scope精确参考切片、双臂/顺序/原G/实际Owner Pipe；NN不变 |
| CPU complete opportunity audit | 22控制、24cell绑定PASS，0d5463 | 522frozen inputs164MB、facts/receipts/Consumer/provisional/job/energy核查；不是另跑神经模型 |
| CPU EOS diagnostic | 4控制、24端点重算PASS，a5e069 | EOS-only理想化诊断，不是已部署修复 |
| CPU MAGICDATA header controls | 12控制PASS，3e5bed | 官方test metadata24,279条/43人join；没有下载2.20GB音频归档，合格6–20s N未知 |
| CPU external LA2 v1 | **未执行**，a105e3 | 静态审查后另冻v2，不改旧源 |
| CPU external LA2 v2 | 28控制、24轨迹/96rule行PASS，7e53cd | 固定日程只读发布策略，不是新GPU/闭环或整个Whisper-Streaming系统 |
| GPU reference first4 | PASS，f367/de09，69连续＋138恢复＋1warmup | 原状态/C/IDs全同，参考费用另列；不是69服务请求 |
| GPU pilot24 | 24/24原任务PASS，f367/de09 | 2source×6arm×2fresh；全部SLO失败留分母 |
| GPU resource8 | 8/8原任务/多源端点PASS，7b83/de09 | 2/4同步source×2arm×2fresh，同2GPU；不是8个新speaker |
| GPU confirmation next2 | 8/8原任务PASS，4fb6/de09 | S0902/S0906，Full/Ready×2fresh，新对照从2扩4 |
| GPU reference last4 | PASS，f367/de09，72连续＋144恢复＋1warmup | S0907/S0912/S0914/S0915，新真实原任务参考，不能把first4改标签 |
| GPU confirmation last4 | **16/16完成，原任务PASS**，4fb6/de09 | S0907/S0912/S0914/S0915；4source×Full/Ready×2fresh；N8最终结果已闭合 |
| 最终32格timer派生 | 2控制及输入／终结账PASS，a3ebaf9 | 仅完成已测数据的worker计时算术，不是新工作负载／模型实验；abort infer保持缺测 |

最后16格：PID2952964/start615526505，13:54:15UTC启动，14:14:08UTC已核对结束与CUDA为空；plan SHA `f1384d4733f23b12cb5ebcba6e538be99d29d79fc728f59e3cf25a024e0eaaad`。[Root handle](launch_ops/CONFIRM_LAST4_FULL_READY_V1/HANDLE.json)与资源闭合记录保留原身份；不要将历史SSH超时当进程死亡重启。原始结果全在8TB；正文/匿名v15旧release保持冻结。

## 4. 最新真实策略证据与可说到哪里

### 六策略pilot24

每臂4格、offered33.11625音频秒：

| 策略 | 信用/audio-s | 覆盖率 | 整场D2/C8通过 |
|---|---:|---:|---:|
| Conservative |12.0|36.236%|0/4|
| Ready-only |12.5|37.746%|0/4|
| Dependency-versioned |32.340125|97.656%|2/4|
| RevTrace/fullcall |32.340125|97.656%|2/4|
| safe UIR |30.840125|93.127%|2/4|
| strict birth-version附录 |12.0|36.236%|0/4|

实际审计：Full保留56个父确认时模型仍在执行的合法调用（30＋26），全部在父receipt→install整个区间内仍active；VDag同56，两实际轨迹的祖先-only/完整输入判据分歧均为0。Ready完成态命中0，但同输入目标重派56、49次policy before-C退出＋9次完整后拒绝；worker82.145秒，Full51.765秒。**合法在飞保留→避免重派→更高实际期限信用**这条机制链有实测，不是只剩抽象名称。

UIR仍执行原使用前输入/AU/SUP。它抑制2条known-invalid hint，完整算完2个错父结果，均被拒、0安装；Full实际before-C退出2次，仅在S0901发生。Full比UIR多1.5音频秒信用，整场通过数相同。能量总差大部分来自没有取消机会的S0769，不能把整段能量差归为取消的因果收益。

### N4确认及最后N8

新增S0902：Full8.5/8.5，Ready3.5/3.5；S0906：Full8.3309375两次，Ready3.5/4.5。新增阶段每臂offered33.79375，Full33.661875（99.6098%）、Ready15（44.3869%）；原任务均同。

与pilot对应双臂合计N4、每臂offered66.91：Full66.002，Ready27.5。pilot2与后续confirm2分别标注；不是4位实验历史从未用过的新speaker。

**最终N8：** 32个Full/Ready子cell，8speaker×2arm×2fresh；每臂offered137.864125音频秒。Full129.460（93.9041%），Ready58.500（42.4331%），加权差51.4710pp；8个source配对及16个repeat配对均Full更高。整场10/16对0/16，所有32格原任务完整P/C/IDs检查PASS。Ready全N8有3次真实ready-bank命中，不能沿用pilot零命中表述。

worker占用Full223.214950秒、Ready322.990539秒，少99.775589秒；两卡origin→physical-drain能量91,879.706对117,822.718J，Full低22.0187%。全派发终结账：Full328＝282安装＋42before-C＋4完整后拒绝；Ready520＝282安装＋208before-C＋30完整后拒绝。worker计时无缺项；42／208个abort缺infer计时，因此总infer仍NA，不能把仅completed observed infer当全模型／GPU活跃总量。

出处：[最终N8报告](FINAL_N8_SUMMARY.zh.md)、[机器汇总](FINAL_N8_SUMMARY.json)、[逐来源CSV](FINAL_N8_PER_SOURCE.csv)、[worker端点](final_n8_worker_ops/FINAL32_WORKER_ENDPOINTS.json)。前2pilot＋6后续确认分别保留，旧8speaker原程序比较不额外增加独立人。

### 同两卡多会话

2同步source：两重复Full11.5/33.11625（34.726%），Conservative10.5（31.706%）；4source：Full9/66.91（13.451%），Conservative10（14.945%）；全8整场SLO失败保留。canonical-first RR下，4source Full的69次派发全是canonical，2source每次只有2次conditional。不能把单链收益自动推广成任意并发容量提升。

已观察21/23及8/8个两类候选同时可用派发点，仅能证明另一个分配规则存在可作用位置；没有测得新调度收益。两个独立分析均认为先完成N8，更换调度可能只是QoS集中与fairness权衡，暂缓新NN4。

## 5. 外部规则、EOS和已拒绝／暂缓的建议

### 已完成：LocalAgreement适配的有限问题

当前StreamCorrect本身含AlignAtt；替换内部ASR决策会改变原C/U，因此本轮LA2-CP只在固定实际调度的消费边界适配。它用严格增加的真实音频更新，不能把同前沿ASR/full/重复publication算两次；任意字符LCP没有自动音频边界；EOS flush只能在实际最后C/U后单列。原ACK影响GC/pins，因此离线结果不能冒称新闭环加速。

Full固定日程：actual SUP信用32.340125/33.11625、4个修改字符；LA2-CP信用31.340125（94.6367%）、0修改；canonical-only30.840125（93.1269%）、0修改。它是**原计算保留＋SUP上可组合的发布策略**，以1音频秒信用换更少改写，不是没有C1的新端到端竞争系统。sustained area也完整保留，不能只宣传免费稳定。

出处：[LA2结果](external_rule_ops/EXTERNAL_LA2_RESULTS_V2.zh.md)、[完整有界索引](external_rule_packages_v2/PUBLICATION_INDEX.json)、[独立审查](review/EXTERNAL_LA2_PRELAUNCH_REVIEW_v1.zh.md)。正式原规则：[Whisper-Streaming](https://aclanthology.org/2023.ijcnlp-demo.3/)、[CUNI-KIT2022](https://aclanthology.org/2022.iwslt-1.24/)；hold-n指保留最后n输出token；[STACL wait-k](https://aclanthology.org/P19-1289/)不是当前ASR里的wait-N。

### 已完成：EOS诊断，未实施EOS修复

把EOS D理想化至1.999999或0、其他实测D/C和权重不变，Full/VDag均最多2/4→3/4，信用32.340125→32.61625；S0901 r0 F128000 D=2.063384仍超期。EOS已经有early-ASR，offer→dispatch1.901/1.689秒，dispatch→display0.701/0.718秒；不能说是一次额外corrector0.55秒已经归因。

第一批前3点下降是已有READY后的算法minchunk／pipeline fill，不是权重未预载。主指标不删初始点。0.5音频秒、不同EOS权重是精确离散贡献，不是“±1.5pp测量误差”。不缩D2制造必要性，不漏EOS／预取未来音频／改变原调用。

出处：[EOS报告](review/EOS_DIAGNOSTIC_v1.zh.md)、[全24表及发布索引](eos_packages_v1/PUBLICATION_INDEX.json)。

### 有用但必须精确定义的理论想法

可保留“信息受限的证据不足”论证：若两个可达历史在规定观察O下相同、真实资格不同，则仅凭O的**即时二元分类器**不可能既sound又complete。版本若已经编码完整输入身份，就不在“缺此信息”的受限类中。safe UIR可先保留两者、稍后AU校验，所以不能不加限制地写成“必丢合法工作或安装非法结果”。

有用的逻辑链是：**为何角色需要不同信息→输入如何决定合法继续→原C/U如何保持→支持路径如何使进展继续可用**。它补足科学认识，不替代工作系统和实际收益。

外部`analysis/divergence_v1`的四文件是未冻结对话分析，不能直接当新正式独立实验。其“canonical无洞必然birth-parent间隔1”推理不成立；现有35控制中的`test_unknown_future_input_survives_ancestor_loss_then_converges`已经给出contiguous P0→P1→P2→P3、C出生P0起点P2的合法反例。B可先buffer但永不selected，因此0 ready-reuse也不能排除跨多代。

同样，Consumer无撤回不蕴含计算祖先从未失效；只在install点抽样UNKNOWN=0不蕴含全生命周期无pending。不要为了造分歧跳过原frontier、回退Canonical或强加跨会话祖先，这会改合同。

### 暂缓／未运行，不能写成已有成果

- 新MAGICDATA长语音：只有metadata与header程序控制就绪，音频未获取、实际合格N未核。用户最新收束决定下不再作为新实验前置。
- 原loader vsCPU-map、同输入新故障5对：已写控制合同／profiler原型，没有新的该GPU结果。
- exact-resident连续原程序fastpath／在线原作者连续基线：发现Conservative无条件restore的潜在封装税；现有包内非infer区间只是混合上界，尚未做在线fastpath实验；也不等于恢复KV缓存。
- 常驻worker跨Owner adoption：共享免冷加载工程收益大，旧调用adoption的额外关键路径收益未证、需registry/cap/WAL去重改造；未实施。
- deadline/usefulness-aware dispatch、priority/EDF：同预算下会重分配不同source QoS，尚无新结果；用户要求不再开分支。
- 更密修订、改deadline、训练更大corrector、盲扩96/160格：不自动做，不把扩大工作量当提高竞争力。

## 6. 建议怎样进入正文

### 一个主信息

> A trusted feedback revision can change whether a running call remains reusable, whether its result may extend the selected execution, and whether a delivered whole view remains supported. RevTrace coordinates these decisions to preserve valid progress without bypassing the original feedback task.

先写读者可复述的能力，再拆EL/AU/SUP。不是以术语清单开场，也不是给所有版本系统判失败。把作者自己的完整组合被另一个实现达到视为条件可实现性与强控制，不抹掉应用／组合创新；也不宣称未激活规则有独占加速。

### 贡献候选与落点

| 候选 | 已有可承载证据 | 正文位置 |
|---|---|---|
| 新可靠性问题：首次达标后合法进展仍可消失 | 2.176秒真实gap；c8全P99通过仍1/2/1 loss | 引言开场＋Fig1 |
| 可执行的角色专属合法性与完整原调用协调 | 冻结输入、原选择、whole-view支持；convergence最小交错；动作不变量 | 合同＋设计／正确性＋Fig2 |
| 联合协调的系统价值 | 严格R×S权衡、6→17→0、267→49、曝光下降、同最终G | 主评估第一结果＋Fig3 |
| 在飞保留的真实成本与服务收益 | 56真实active确认／Ready56重派；N8 Full/Ready最终实际值 | 主比较＋Fig4／主表 |
| 原任务与可靠执行 | 全状态/C/IDs参照；epoch／durable-prefix／physical lease；故障事实与现有成本 | 执行协议＋简短故障评估 |
| 可组合发布策略与部署条件 | LA2-CP tradeoff、同GPU多会话结果 | 精简评估／discussion，细表artifact |

“最精细ancestor规则独占更快”“所有版本管理不足”“零文字修订”“所有任务／负载P99都过”“恢复主张覆盖Byzantine/GPU算术”均不作为贡献。

### 主文骨架与图

1. **Introduction：** 一段真实失败，解释重要性，点名协调机制图，给系统能力和可证伪贡献。
2. **System and Feedback Contract：** 先对象／原任务／故障模型，再给三个判断与可避免损失定义；一页内让读者知道什么被保证。
3. **Design and Correctness：** 同一call/parent/view案例，未知不等于失效；原选择与view支持分别处理；动作归纳代替循环假设。Fig2解释因果示意，不装成测量。
4. **Execution：** 实际受保护完整调用、串行持久化、实际Consumer、物理lease和恢复；不把线程／文件名当产品流程。
5. **Evaluation：** 能力问题→公平对照→结果→机制教训；N8主表、core联合图、成本和一个部署条件。按bank／单位区分，不写阶段目录。
6. **Related/Discussion/Conclusion：** 分机制定位已发表工作，给实际实践教训；统一scope段，主图注只留最关键界定；全文不堆防御句。

保留四图主干：Fig1真实失效与joint对照；Fig2图形化权限／生命周期机制；Fig3联合Pareto和真实文字修改；Fig4最终Native强策略与资源。细baseline、多负载符号、完整模型profile、所有失败/修复进入artifact。本总记录和registry保留全部，主文可有选择。

## 7. 稿件质量与收束规则

DSN2027官方[征稿](https://dsn2027-berlin.github.io/call-for-contributions/)要求Regular11页技术内容，参考文献不计；首页摘要至多150词、10pt双栏、灰度可读图。不是“只有生产部署／形式化两种论文”的硬分类。以已核公开VampOS/ReCraft/PRAXIS为表达实例：问题具体、对象先于线程、结论紧接比较与机制、故障模型有锚点；不把少量范例当录用因果公式。

用户偏好：学术但可读，图形形状为主、少文字、有信息层级；可以组合创新，不能把原创限定为从零方法；选择真正有竞争力的证据，不把一堆限制填满正文。保留真实AI使用披露，不发明精确接受概率。

最后16格完整终门后：汇总N8、逐source配对、原任务／资源闭合；更新registry与本记录；不再开新研究分支。随后完成v15→v16正文、图表、引用、编译与逐页视觉检查。原v15／旧匿名材料保持独立冻结，新的匿名release需待新稿与artifact最终一致再更新。

前一批已验证GitHub归档：`d6d5bab095cf5aa357af62ca8f80993ef44a817c`。最终确认、总记录和新稿按各自归档回执继续同步；无模型、缓存、原始大文字ledger入Git，不强推覆盖历史。

## 8. 收束后的实际交付（2026-11-11）

最后16格和N8总比较已闭合，不再开展新增研究实验。v16全文已重写、编译并完成逐页检查：10页技术内容＋1页参考文献，142词摘要、31篇引用、4图。主文按证据解释问题与联合协议，全部实验保留在本记录和registry中。参见[最终写作与研究收束记录](V16_WRITING_AND_RESEARCH_CLOSURE.zh.md)。新稿私有GitHub提交为`e14faa27da272695719b6ca37ad88792f9ff5397`，已独立逐blob回读；最终公共证据归档以对应DELIVERY_MANIFEST和提交回执为准。旧匿名镜像未在本轮刷新，不能把它当作新稿和新实验的入口。

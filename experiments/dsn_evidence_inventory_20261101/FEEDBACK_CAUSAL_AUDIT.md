# Feedback、Authority 与未来后果：遗漏证据审查

日期：2026-11-01。范围：旧 Paper/TC 的数值差异—反馈传播，Oct6 剂量干预，Phase D R5/R6，role-limited coherent-return，M 非 ASR 内存应用，以及其与 DSN release v9 的关系。

本次只读检索现有源码、冻结协议和有界本地结果，并读取当前与旧稿 TeX；未重新执行模型、GPU、SSH、故障注入或旧 auditor，未改 runtime、CURRENT 或论文。以下“已核验”指本地保存结果与原始运行器/协议的一致性；不是新一轮独立模型复现。旧 PDF 未逐页视觉复核，因此不声称完成三份 PDF 的全部视觉审阅。

## 1. 先给判断：有遗漏，但最值得取回的不是最大的倍率

当前 v9 的三判断 EL/AU/SUP 适合 DSN；它缺少一个短而有实际后果的桥梁：**为什么当前输入/版本正确，仍不能替代原始可信内容选择？**

本次发现的最佳现成答案是 M 的 **current readset × coherent return**：当前 readset 允许 OCC 正常通过，但错误返回真的写入 SQLite、被下一次模型读取，使答案由 clean 14/16 正确变成 0/16；内容选择正常的三个公平对照都恢复 14/16。另加的 content-only 控制去除了 JSON 格式变化这一替代解释。它比“RAF 最大153”更直接地把 AU 与用户任务后果连接起来。

这不是要求改回旧稿的“数值可靠推理”主线。建议主线仍是 trusted feedback revision 下的有效进展保留，**用一个小段落说明 AU 的存在理由**；将更广的旧因果和失效数据放附录/证据地图。否则从稳定保留转到攻击、数值认证、Agent 质量三条主线，反而削弱单一中心论点。

## 2. 证据分层和采用次序

|优先级|已有证据|回答的问题|v9 用法|不能替代的证据|
|---|---|---|---|---|
|A|M content-only 64 validation episodes + 原320矩阵|版本/出处正确为什么还需要内容选择？实际下游是否受害？|AU动机/小型跨应用验证；最值得有选择取回|不是 native StreamCorrect 上的同合同效果，也不是自然发生率|
|A−|64 role-limited Qwen operator cases|校验和、当前父状态、可信 Render 为什么不等于选择？|AU机制之后的受控失效见证；与M二选一主文，其余附录|不是完整Standard漏洞；不是对失陷Authority的保护|
|B|Whisper R5 16个来源/192 GPU calls|被替换的历史真的进入decoder并影响后续输出吗？|artifact/边界段，回应“只改显示不改模型输入”|不是线上WER/服务完整移植|
|B|Oct6 两家族240剂量干预|反馈是可复现的因果通道，是否每次都传播？|简短跨家族机制支持，优于只挑最大RAF|不替代自然数值差异；不证明native需要精度分工|
|B−|旧21 legal output pairs, ON8/OFF0, 最大累计RAF153|合法执行形态产生的差异是否能经反馈边传播？|历史动机2–3句或附录，明确adapter/estimand|不是21个有效不同反馈状态，也不是普遍153倍危害|
|边界|R6 batch预处理523/524 effective IDs、输出全同|冻结“完整输入”为什么要覆盖实际processor状态？|EL/适配要求的一句反例或附录|不是GPU SDC，更不是已观察输出损害|

## 3. 旧21对与 RAF153：真实、但口径必须保留

### 3.1 实际材料链

- 冻结配置：[configs/revtrace_phase4b_whisper_feedback_gate.json](D:/VLA_QWEN/RevTrace/configs/revtrace_phase4b_whisper_feedback_gate.json:2)，ID `REVTRACE-P4B-WHISPER-FEEDBACK-COUNTERFACTUAL`；tiny.en/base.en，execution shapes1/8/16，每模型100个不复用源样本的90s会话，固定未来音频，禁手工token/logit编辑。
- 运行器：[scripts/remote/run_whisper_feedback_gate.py](D:/VLA_QWEN/RevTrace/scripts/remote/run_whisper_feedback_gate.py:240)；先singleton/repeat，再b8/b16寻找实际差异，然后固定未来音频把两条输出分别通过同一singleton executor继续运行；OFF不传历史。
- 实际launch：[scripts/remote/run_phase4b_whisper_expanded.sh](D:/VLA_QWEN/RevTrace/scripts/remote/run_phase4b_whisper_expanded.sh:1)，模型、manifest、输出均在8TB盘；100candidate、target20、future2、maxnew96。
- 保存结果：`results/phase4/whisper_feedback_expanded/{whisper-base-en,whisper-tiny-en}.json`。本次重核SHA256分别为 `8b1b28870b0b3bace3d702d7fb99665c64b2196bded63889ba404711e065fca7`、`3d1882f1927a1767de23367fb13cc25ef5df4cf6d721acb1fa117e85dae475bd`，与Oct4重审索引一致。
- 语义重审：[docs/reports/dsn_review_20261004/causal_reaudit.json](D:/VLA_QWEN/RevTrace/docs/reports/dsn_review_20261004/causal_reaudit.json:2)，`PASS_CAUSAL_INPUT_AND_CUMULATIVE_RAF_REAUDIT`；重审代码 `scripts/audit_dsn_causal_pairs.py`。
- 已有纠正：[docs/CLAIM_BOUNDARIES.md](D:/VLA_QWEN/RevTrace/docs/CLAIM_BOUNDARIES.md:131)。旧稿现行TeX已采用修正口径：[Paper_TC/sections/02_model.tex](D:/VLA_QWEN/RevTrace/Paper_TC/sections/02_model.tex:53)。因此这不是新发现的正结果，是曾被认真界定、在新稿被移出的证据。

### 3.2 分母与负控

1. **21是选出的execution-output discrepancy pairs**，不是21种不同有效反馈状态。9对decoded prompt_text相同；12对不同。9对同prompt均不传播。
2. ON有8/21在至少一个未来窗口不同；OFF为0/21；6/21在两个未来窗口后仍不同。两模型singleton重复差异均为0。
3. 原始结果base有16对、tiny有5对；两者分别扫描100个窗口。**每模型target20均未达到**，原JSON分别保留 `PHASE4B_INSUFFICIENT_NATURAL_EXECUTION_SHAPE_PAIRS`。合并21对可作现有因果描述，但不能回写为每模型完成20对或把每模型gate失败抹掉。
4. 这些是“先找差异再干预”的发现事件。16/100和5/100也不是随机生产发生率：输入构造、重复音频batch及目标搜索形态都特定。
5. `observed_application_catastrophes=0`；不能把传播/持续写成已观察灾难、已预防幻觉。

### 3.3 RAF到底算什么

运行器315行：`sum(D[k])/max(1,D[0])`。D是**生成token序列编辑距离**，包含差异发现窗与两个未来窗；不是WER、字符损失、service failure或正确性退化。

最大案例是base.en、pair hash `0a2f833cfd13a22c2db95d5802a95e8e672fd90fe6d644541c2f9b11d2a16122`，D=[1,64,88]，OFF=[0,0]：[causal_reaudit.json](D:/VLA_QWEN/RevTrace/docs/reports/dsn_review_20261004/causal_reaudit.json:180)。累计153=(1+64+88)/1，终窗距离比88。最大值不能称“系统将错误放大153倍”；准确写“one selected legal-shape discrepancy accumulated153 token edits across the measured three-window response”。

### 3.4 身份完整度与适用性

重审保存runner SHA `1e6fd8d7e348c5dc4eb50ddfd7e7790660c375ef4759f94bae02d9dde4a368e5`。这批legacy JSON含实际路径和配置，但本次未在其自身找到完整execution commit/environment/model哈希集合；不能借当前HEAD或Oct28/Nov1 source manifest补标签。若进入主文，需由总证据索引补齐历史source bundle与模型环境对应，或者明确历史证据身份弱于后来全manifest活动。

## 4. 为什么它不能推出“必须 FP16 Private + FP32 Authority”

- 原运行器87、104行均使用 **FP16**，batch和singleton相同dtype；未来两分支也都在同一FP16 singleton executor继续执行。它隔离的是execution-shape产生的输出差异与feedback edge，不是FP16vsFP32这个处理因子。
- `prompt_text[-800:] → get_prompt_ids` 是旧decoded-text状态合同（166–168行）；不是后期R9 raw-token历史，更不是native StreamCorrect的完整state。
- 当前v9 native实验使用两个完整原框架worker、FP32，[05_native_retention.tex](D:/VLA_QWEN/RevTrace/Paper_DSN/revisions/20261101_dsn2027_release_v9/sections/05_native_retention.tex:7)。AU是原始recognizer–corrector选择与owned call确认；不等价于“高精度模型天然正确”。
- 旧V100证据还显式观察FP32 batch/singleton差异：[Paper/sections/06_evaluation.tex](D:/VLA_QWEN/RevTrace/Paper/sections/06_evaluation.tex:324)。不能把FP32写成普适数值等价证明。

**可保留论证**：临时输出若被当作下一调用的实际输入，就不只是UI问题。**不可推出**：所有native部署都需要独立高精度certifier、所有扰动都会放大、当前协调协议自行防范任意坏worker。

## 5. Oct6剂量干预：比“153×”更完整的机制证据

### 方法、结果及身份

- ID `DSN-FEEDBACK-DOSE-20261005`；Qwen3-ASR0.6B、Whispertiny.en；同40个30s声学上下文、40speakers、182源文件，无文件复用；每模型1/4/12普通token替换，共240对。两模型共享音频，所以80模型上下文不是80独立音频。
- 固定未来音频、执行和解码；ON/OFF/repeat；实际conditioning无alias审计各120对通过。报告入口：[DSN_STRENGTH_RESULTS_20261006.md](D:/VLA_QWEN/RevTrace/docs/reports/DSN_STRENGTH_RESULTS_20261006.md:33)。
- 独立聚合：`results/dsn_strength_20261005/FINAL_REAUDIT_V4.json`，本次重核SHA=`8ad371ad1329c5b06a9cdc6656d3bd81ac3a1116574de34c9db6e7a3621fd1ac`。dose中逐对保留initial distance、future distances、stable_controls、censored flags。
- Qwen源记录 `dose_qwen_v2/RUN.json:20` SHA=`b980c40b21a048d8f0f59e8e15795721dd204e797f778ef8394a2b5d738ee091`；Whisper `dose_whisper_v3/RUN.json:20` SHA=`78f4af7d3eae5d7a7f967cafa0c9705d2fbd963e8ff028dc8bc46fedc7e11c33`。RUN保留命令、模型哈希、manifest SHA=`a1d493fe021f8adfd68d78959aee5f3e8f1ae48fe2423d410c72d2381dc3d67b`、torch2.9.1/transformers4.57.6/qwen-asr0.0.6及3090。各版本resume来源不同，不能用一个源码SHA替代全部origin_source。

|模型|剂量1传播|剂量4传播|剂量12传播|OFF|
|---|---|---|---|---|
|Qwen0.6B|13/40|32/40|37/40|各剂量0/40|
|Whispertiny.en|12/40|22/40|32/40|各剂量0/40|

此表来自本次读取现有dose逐行聚合，与报告一致；不是新GPU结果。它支持本组群体剂量趋势，**不意味着每个上下文单调**。单token Whisper最大future两窗编辑和67=[29+38]，不含注入窗，和legacy153不是同estimand。

### 必留边界

- 这是人工投影替换，和前一节合法shape差异分开；不能把两者合称自然数值故障队列。
- 本轮指定HF/eager、FP16、singleton/b8自然扫描两家族均0个新增有效投影差异。应保留此不利结果；不能仅选legacy21对推断普遍风险。
- 各家族剂量12有1条budget-censored轨迹；已保留，不算完整终态。Whisper合法生成预算修复为min(256,448-prompt_len-2)，不截掉输入来美化响应。
- 已保存轨迹支持重新计算编辑距离；部分重复控制只保存运行时布尔，不声称重新读取不存在的完整控制轨迹。

采用建议：如果主文只留一句历史跨家族因果证据，用“single-token interventions changed later outputs in13/40 and12/40 contexts, with zero feedback-off differences”比153倍更稳。详表放artifact；不以此取代v9同合同retention服务证据。

## 6. M：最有价值的 AU / 实际后果遗漏证据

### 可核查链与冻结身份

- 冻结scope：[PROTOCOL.md](D:/VLA_QWEN/RevTrace/experiments/legal_progress_20261026/PROTOCOL.md:56)，ID `REVTRACE-LP1-20261026`，M是其中明确单独条件矩阵。
- 原矩阵execution commit=`e83983004b22f0e7b6081157260f9954f4cf2ff7`：[m_execution_v2_SOURCE.json](D:/VLA_QWEN/RevTrace/experiments/legal_progress_20261026/m_execution_v2_SOURCE.json:2)。分离的proposal/Authority pipes均Qwen2.5-1.5B FP32；不能套成FP16坏、FP32好。
- 内容控制execution commit=`ea9fc8999076aaf773e7618e170953fa1ccd1280`：[m_format_execution_v1_SOURCE.json](D:/VLA_QWEN/RevTrace/experiments/legal_progress_20261026/m_format_execution_v1_SOURCE.json:2)。
- 结论、raw与控制历史：[M_DECISION.md](D:/VLA_QWEN/RevTrace/experiments/legal_progress_20261026/M_DECISION.md:5)；`M_INDEPENDENT_AUDIT.json:2` status=`PASS_INDEPENDENT_SQLITE_RECEIPT_AND_ACTUAL_FUTURE_INPUT_AUDIT`；`M_FORMAT_AUDIT.json:2` status=`PASS_INDEPENDENT_CONTENT_ONLY_FORMAT_TOKEN_AND_FUTURE_INPUT_AUDIT`；`M_FORMAT_RAW_INDEX.json:3`有SQLite/result/job/power等逐文件哈希，包`M_FORMAT_RAW.tar.gz`可用于后续复核。本次未解压/重扫raw。
- 原320=64development+256validation；不是320独立任务。12构造任务前4开发、后8验证；每表格16episodes=8tasks×2timing repeats。原1132worker result messages中160是CPU编码，实际972GPU model operations；控制64episodes另有208GPU操作+64CPU编码。

### 为何它能增加论文重要性

current-clean各方法16/16正确内存、14/16正确答案。current-coherent时OCC-only安装16/16错误内存，答案0/16；trusted regenerate、Standard+Strict、RevTrace+Strict都16/16正确内存、14/16答案。全部future answer确实读取SQLite内存并编码进下一次模型输入，answer接口不能反写内存。

因此这里不是“输出不一样所以受害”的推断，而是当前版本通过→错误内容安装→后续真实消费→任务答案退化的完整链。**配对新增任务失败14/16，覆盖7/8任务；不能写16/16新受害**，因为clean已有2次失败。

stale条件OCC正确拒绝、16/16unfulfilled；三个protected方法通过实际付费重生成/Strict fallback恢复当前状态。这给DSN一个很好的成对观察：**阻止非法安装与不无谓失去合法服务是两个义务**。

### 内容控制为何关键

原320coherent替换也改JSON格式，0/64保留原格式；这不否定OCC坏内存，但不能将Strict拒绝全部归因于内容。补充64个current验证保留字面外所有bytes、token span外IDs及EOS；32个Strict拒绝均始于替换的CONTENT span。结果重复上述保护对照，16RevTrace admission均通过原核心重放。`M_FORMAT_AUDIT.json`本次SHA=`50f1b7576b501e0b9be79d9dbc3ffa1fb2f50aef1ff3f4c3c535e141dd8ebb9b`，与raw索引一致。

### 不能写什么

这不是原生LangGraph漏洞、自然攻击率、最优并发恢复调度、通用事实正确性。开发集protected仍有Authority选错ID，正确内存的validation仍2/16答案错。三protected同效，应该明写；贡献是应用状态的可执行义务与协调，不是独占checker。

**推荐位置**：§2 AU动机用2句，或评估加8–12行“Why authority remains separate”。只保留current-clean/current-content-only对照及下游答案，原320全表放artifact。若要与当前native成严格同合同结论，需新协议，不能拼接数值。

## 7. 64 role-limited operator：更贴近 ASR 的备选

冻结：[adversarial_frozen_v2/GPU_PROTOCOL_v2.md](D:/VLA_QWEN/RevTrace/experiments/dependability_protocol_20261025/adversarial_frozen_v2/GPU_PROTOCOL_v2.md:1)。core=`408d75624104e7e11af3f0f2832263c632b10ed8`，probe=`b08fa4262d1c3ab7e07137eea340d0bb92be200c`，baseharness=`f0eaae69323fbaa10b3892761a8ac2c149181013`：[ROLE_PROBE_SOURCE_MANIFEST_v2.json](D:/VLA_QWEN/RevTrace/experiments/dependability_protocol_20261025/ROLE_PROBE_SOURCE_MANIFEST_v2.json:2)。

4固定开发clips×4actualmethods×clean/coherent-proposer×2fresh repeats=64正式cases，两个8casepilot不计入。只改自身proposal六内容字段及一致的unkeyed transport checksum/BatchDrained manifest，不改job/parent/runtime/audio/Authority。预制音频全部offered后执行，非arrival serving。

实际summary：`role_formal_synthesis_v4/SUMMARY.json:2` status=`COMPLETE64_SAME_CONTRACT_OPERATOR_SOURCE_SELECTION_CONSUMER_WAL_COST_ASSETS`；`role_formal_primary_v2/SUMMARY.json`逐case数据；`ROLE_FORMAL_WAL_COST_AUDIT_v3.json:2`独立WAL/功耗clock复核；`role_formal_collected_v2/FORMAL_RAW_INDEX_v1.json`原始索引。

- 弱renderer-only 8corruptcases全部将marker传入后续Authority实际input；每repeat四源worderrors8/226→24/226，两repeat合并为16/452→48/452。三个protected保持16/452，排除Canonical后续marker。
- marker可进入所有protected的Private input并暂时显示；没有任何后续native Z重生成完整frozen substring。弱路径主要由adapter携带污染前缀，**不是新neural amplification**。
- fullsubstring最终8/8，但whole-word entity只4/8；不能拿不同detector混成攻击成功率。
- metadata-only只是弱trace的shadow，不是第5个GPU方法；fullStandard得到完整trustedselection并同效，不能称其脆弱。
- 同步WAL能正确保存错误内容，Render能正确解释错误候选，版本能是当前值：三者仍不提供原内容选择。这是“EL/current不等于AU”的ASR证据。

采用建议：M偏真实任务损害；role偏同ASR语义与完整selection。主文选一个，另一个作为可审阅artifact支撑，不再开新贡献标题。当前v9故障模型排除Byzantine代码，若写此受控message污染必须明确是不同历史stress合同，不能将它说成当前native定理已覆盖的敌手能力。

## 8. R5、R6与恢复：可用的补充，而非堆规模

PhaseD原根不在当前顶层，但完整历史镜像存在：`experiments/dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/`。以下锚点都指该历史版本，不假装当前执行源码。

- R5冻结：[R5_R6_DESIGN_FREEZE.md](D:/VLA_QWEN/RevTrace/experiments/dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/R5_R6_DESIGN_FREEZE.md:3)。Whisper-small.en；16个不同于原12源的新说话人；每音频3连续段、完整覆盖；首段FP32greedy、第二段correcthistoryFP32×2/FP16×2/donorhistoryFP16×2，实际decoder hook；第三段固定futureaudio。全部192GPUcalls。
- 结果：[FINAL_RESEARCH_REPORT.zh.md](D:/VLA_QWEN/RevTrace/experiments/dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/FINAL_RESEARCH_REPORT.zh.md:107)：16/16非空替换历史被消费；14/16target变；9/14 qualifying未来continuation仍变。169/770→260/770字错误（21.948%→33.766%）来自人工固定态分段协议，不是线上WER或16个natural faults。runtime=`2a4b56bc5d8dcbf3884f03f8213f9c39101f59f8`，probeV5=`4f3542c3911291e1a9435b4a77513315a5e27d45`，原索引`EVIDENCE_INDEX.json`。
- R6：[同报告115行](D:/VLA_QWEN/RevTrace/experiments/dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/FINAL_RESEARCH_REPORT.zh.md:115)：samewave/parent的chinese05 effectiveIDs523vs524随batchlayout变化，其他三个目标IDs相同；所有生成Z/P相同。它说明“冻结文本+wavefrontier”可能遗漏processor realization，但没有输出损害。适合EL完整输入动机，不能充数值污染案例。
- 同活动3次真实SIGKILL在durableinstall后、publication前：每次2个认证快照被新Consumer实际观察，WAL前缀保留、无重复准入；ledger23–64ms，但restart→firstcertifiedconsume31.16–31.68s，[报告117行](D:/VLA_QWEN/RevTrace/experiments/dependability_protocol_20261025/source_archive_v3/experiments/phase_d_20261021/FINAL_RESEARCH_REPORT.zh.md:117)。这是“durability不等于availability、恢复后需真实交付”的强历史见证，但当前native已有更相关故障证据，建议只用来说明恢复指标定义，不把全部kill数混为统一实验。
- Oct6的12次真实QwenSIGKILL/882 auditedcommits和84 Linux热缓存重放属于不同合同：[DSN_STRENGTH_RESULTS_20261006.md](D:/VLA_QWEN/RevTrace/docs/reports/DSN_STRENGTH_RESULTS_20261006.md:18)。882不是882次崩溃；8192commit/674.3ms只是在合成两token状态+热缓存生产WAL decoder的fixture，不是冷模型RTO。不要加进当前native成功率分母。

## 9. 建议的“选择性取回”动作

1. **最高收益、无需新实验**：给AU增一条“current-source资格与内容选择独立”的真实后果，取M content-only小表。把EL/AU/SUP从抽象标签变成有各自failure consequence的设计义务。已有160同target trusted selections与nativegeneration全Z匹配支持protected equivalence；普通组件可组合满足义务正是可部署性，不应当成原创新的否定。
2. **同样无需新实验**：artifact中建立一页causal evidence map，分合法shape差异、人工projection替换、coherentreturn、actualfutureconsumption、taskharm。用列展示干预点/可信边界/损害/分母，避免读者将所有数据压缩成“21次注入”或“很多安全检查”。
3. **正文空间紧时**：不恢复RAF153大图。保留当前firstpage continuity problem→机制→R×S主证据，M/role只承担AU动机。当前v9的675sameinputidenticaloutputs是其自身执行合同结果，与旧shape差异并不矛盾，勿将两者合并。
4. **若必须新增实验才值得做的方向**：仅考虑当前native合同内、预声明的coherent-result/selection-edge小干预，直接检验“EL通过、AU缺失时selectedhistory是否被改，完整AU是否保持原任务且是否仍保留合法服务”；原输入、完整state、原选择函数、同peerorder/FP32、真实Consumer/WAL都不变，OFF/clean/repeat/originalselection controls齐全。先证明现有接口真的存在合法低信任干预点；否则这是攻击模型扩展，不应为了旧卖点强加到v9。此项是建议，不是已执行或必做。
5. **不建议新增**：为做出更多自然flips而无限扩模型；把FP32当绝对oracle；继续追最大RAF；把历史进程恢复样本数合并成一条大N；用role/M保护同效结果声称RevTrace独占安全算法。

最终判断：**遗漏里确有DSN相关的重要证据，价值在“当前版本仍可承载错误状态并造成真实未来损害”，而不是单纯补回一个153×。** 最强组合是当前v9的合法进展协调，加一个边界清晰、任务后果完整的AU见证；它能同时提高问题重要性与设计必要性，而不改写整篇主线。

## 10. 尚未提升为已独立核对的候选

旧依赖协议candidate稿 `experiments/dependability_protocol_20261025/candidate_20261026/sections/05_evaluation.tex:55` 还列了E1的24个Qwen context（12源）：输出全变，worderrors15更坏/8同/1更好，正确context拒绝24，错误context margin可通过15/24，故意破坏可信Authority时24/24被准入。本次定位到PhaseN的历史索引和后续完整验证替代，但未逐一解析该E1原始bundle/字段/源码身份，因此这里将其列为**候选证据、非本次完成原始记录复核的结果**。与已有M/role相比，它没有更高的主文优先级，不应仅从旧candidate段落复制数字后标为本次新核验。

## 11. Formal complement：取机制区分，不堆状态数

追加只读核对了实际完成receipt、theorem源码、named controls及code map，没有运行TLC/TLAPS、模型或trace reader。

**三个不同证据对象。** (1) `input_freeze_20261027/formal`的实际source=`996430d24d110facb242b352ba69c2f42f26e69c`；`formal_results/full_v5/GATE.json:2`为`PASS_SCOPED_FORMAL`，`tlaps-ProtocolProofs/RESULT.json:2`exit0、20obligations，`SUMMARY.json`含21个TLC预期结果（10正向、11具体反例），不只是工具安装。`ProtocolProofs.tla`实际是10个参数化定理生成20个obligations；不能写20条native定理。(2) native refinement source=`deb3260655e2f3312499a34597cc0be6fc15484b`，`FORMAL_RESULTS_v3/SUMMARY.json:2`的6,231/14,074状态分别是2frontier无故障与1frontier至多1fault、都12events的手写有限规格，27命名控件；不是TLAPS，也不是Python/CUDA自动抽取。(3) checker=`c4dde9ea9c7abf80fae084bc2293e193262c71e6`，`TRACE_DEVELOPMENT_RESULTS_v2/SUMMARY.json:2`35synthetic controls；它们和实际6开发NN trial的102新durable事实、305Consumer应用、107whole-view links是分开的证据，见`SHORT_ACTUAL_TRACE_RESULTS_v2.zh.md:9`。不能写35真实故障、210独立控件或用历史TLAPS替native实现背书。

|可取的机制信息|实际源码/反例锚点|对v9最有价值的作用|
|---|---|---|
|**历史事实继续有效，不等于旧写者可重新授权。** 旧epoch不能append，但唯一durable receipt仍返回原记录，恢复不把它改签成当前owner。|`formal/source_v5/ProtocolProofs.tla:40`的`OldWriterCannotAppend`、47行`HistoricalReceiptReturnsUniqueOriginal`、54行`RecoveredPrefixPreservesOriginalFields`；native`source_snapshot_v3/test_model.py:185`与`trace_source_snapshot_v2/test_refinement_trace.py:113,161`分别测新owner重授旧job的反例与旧事实合法replay。|给“preserves accepted results across producer failure”一个清晰学术区分：authority to **create a new fact** 与 validity of **an existing fact**分离。v9现有proof已大体包含，建议把这一对判断压成一句可复述lesson，而不是加一组定理数量。历史receipt membership自身不能证明某个新输入合格。|
|**UNKNOWN不等于REFUTED；祖先失配不能直接取消未来完整输入。**|native`source_snapshot_v3/test_model.py:58`构造3frontier/4call再收敛；65行mutation=`ancestor_mismatch_cancels_unknown`被拒，72行单测unknown不可作为C-entry取消证明；`MODEL_DESIGN_AND_CODE_MAP_v1.zh.md:10`定义三态，19行映射`_reason/dependency_support_losses/_canonical_witnesses`。|这是本轮formal中对novelty最有帮助的机制点：说明朴素“祖先失效→整棵子树失效”的依赖撤销与**实际冻结输入资格**不同。可补§3 EL解释或proof后反例框；不要把symbolic构造当自然交错发生率。|
|**latest-safe可安全地丢掉有用进展；安全不等于选择完整。**|历史`formal/source_v5/LegalSelection.tla:51`的`latest-safe`只检查latest；59–60行区分`SafeChoice/SelectionCompleteness`；实际TLC`selection-latest-safe-negative`保留合法older-preview却返回Nil的反例。`ProtocolProofs.tla:65`只证明一般`MaximumLegalScanStep`，Eligible/Frontier是抽象谓词。|可把“不会非法保留”与“不会无谓丢掉合法结果”成对组织，这是DSN问题重要性的现成补强；对应v9 R/S组合和whole-view保留。普通完整scan/index可以实现该义务，不应包装索引算法原创。固定snapshot假设不覆盖parent/revocation竞态，仍须runtime串行与apply-time revalidation。|
|**恢复不能清空已接受输入债务，也不能重置原期限。**|历史`AdmissionLifecycle.tla:112`中`GuardDebtRecovery`保留`durableAccepted`，153行`InputDebtPreserved`；native`test_model.py:172`的reset-input-clocks反例；trace控件`test_refinement_trace.py:173,196`分别检测clock rebasing和accepted input消失。|最适合贯穿§4–§5的methodological obligation：恢复旧view/取消分支不等于完成新audio，故所有offered分母与原release clock必须保留。这支撑当前native故障结果的可信解释，比增加“零违规状态数”更有说服力。|

另一个有用负结论是`BoundedWait.tla:20`的`DeadlineAlwaysMet`确有反例：有限等待预算+weak fairness不推出wall-clock deadline。当前v9条件性继续服务段已经写准，宜保留，不把形式活性替代D2/C8实测。

**采用范围。** 当前v9`03_native_refinement_working.tex:56`已经列native规格状态数和范围。下一轮真正有增量的是突出上述前三种不等价、给每个对应一个小反例或一句lesson，而不是再把旧TLC/TLAPS数字堆入正文。历史TLAPS对GuardedAppend的归纳、receipt与scan的参数化证明可作为artifact中单独的“协议引理支持”；不能改写为native4f实现的端到端机器证明。实际6trial中compatible-ahead应用、policy-local-rejection、重启后复用非canonical-born closed buffer均0，不能用35控件填补这些真实覆盖分母；后续正式bank要另据真实checker结果说明。

## 12. 再扩检 recovery / retirement / input-freeze / trusted-render：可立即利用的正面增量

继续阅读了`context_recovery_20261028`、`trusted_render_dependency_20261028`、`final_evidence_integration_20261028`、`physical_retirement_20261028`、`dsn_joint_retention_exit_20261028`、`evidence_retirement_20261026`的协议、终态记录/独立GATE/有界CSV，以及根`docs/reports`的Phase5/6/7、DSN_PRIORITY、DSN_SEMANTICS、long_horizon等历史报告。没有运行重计器、GPU、原生推理或重新扫描远端raw；没有改稿。

### 12.1 最值得增加的一幅图：可信旧事实的可见恢复，不必等完整推理栈

**这是v9少呈现的真实正结果。** `trusted_render_dependency_20261028/RECOVERY_RESULTS.md:3`记录同一c4/rho3、同workers-first、同logical fault cut、相同native/light允许合同下的四个真实冷进程/模型重启：

|方法/Owner renderer|全部旧事实实际可见RTO|首个新事实RTO|原已接受债务清空|
|---|---:|---:|---:|
|RevTrace/native|15.592s|19.714s|21.688s|
|RevTrace/light|2.471s|20.272s|22.292s|
|完整Standard/native|15.807s|19.041s|20.844s|
|完整Standard/light|2.515s|20.162s|21.990s|

实际runtime=`040fcc95f4cd3bbc4d918bc1dd4502b0b768990c`；`cold_records_v1/cold_program_v1/GATE.json`保留原pilot pending-independent状态；随后`cold_native_audit_v1/GATE.json:2`的analysis=`539a1ef6be5f6db8d21744b46e1e46ef5f47d8fa`实际4cell PASS，再由`postcheck_records_v1/cold_postcheck_v1/GATE.json:2` source=`88d068b470660c7288d390633c19911a2ecfc2aa`得到`PASS_DECLARED_RENDERER_REAL_COLD_AND_NATIVE_REPLAY`。不是只引用最初pilot gate。

独立native oracle重建185个same-job行、87个完整batch实际frontend输入、56个durable text绑定，并从Consumer实际记录重算三时钟。全部保留18.51s precrash accepted debt、最终覆盖1、每格14unique transitions、WER6.0606%相等；没有借旧fact replay冒充新推理。核心解释是**将重新验证/渲染既有事实所需的可信依赖，从恢复新推理所需的完整模型栈中抽离**。两种方法旧事实RTO改善13.121/13.292s（约84%），而新事实/债务和能耗稍退；这种分离本身正是DSN式故障服务对象的明确化。

它不是“信任cached text”：仍逐fact重新Render并核对全部绑定。`CPU_RESULTS.md:10`及`cpu_component_records_v1/component_v2/GATE.json:2`确认native tokenizer程序/同Rust引擎与parser依赖切片，268个实际观测、151705词表IDs、4096随机token/Unicode控制、7个失配依赖fail-closed；source=`973d4c66e2f4d8227ec5546f86da310e38151846`。fresh light进程在旧事实publication前未加载torch/transformers/qwen_asr/librosa；`SERVING_DECLARATION_v1.json:2`在prefix产生前就声明共享allowlist。程序导出/可信准备是新合同前提，不能将旧WAL静默重标或将有限conformance叫任意Rust/Python证明。

**图的现成设计**：横轴从真实kill开始，四行对应上述四臂，每行只放三个有类型的事件glyph（old visible/new fact/debt cleared）及细线；两组native/light配对，以饱和色仅突出old-visible移动。用三事件符号而非堆文字，视觉上立即看出“恢复哪种服务”。图注标明old core Qwen contract、四个单次开发试验，和当前native fault bank分面且不合并统计。主文页数紧时，保留§4中两句及artifact图即可。**共享优化可作为设计成熟度证据，不需要虚构RevTrace独占算法。**

### 12.2 把K从一串数字变成“容量如何变为有用服务”的真实泳道

v9`05_execution_only.tex:5`已列K24摘要，因此不是遗漏实验；遗漏的是易理解的机制图。后续冻结K24优于更早16格作为主图来源：`dsn_joint_retention_exit_20261028/RESULTS_FINDINGS.zh.md:47`和`DIAGNOSTICS_v1/SYNC_FOLLOWING_BATCH_ROWS.csv`已有完整行证据，execution=`f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`，analysis=`6eb02d6ecceacb1810e247cdbe2ba72013eddcea`，逐前沿诊断=`c25b06555634a37ecaa8cde7f77b915a303f2732`。

**可画一个已有r1/R1真实case**：covered请求→22.196ms后ACK→再13.359ms真实drain→下一批同16行开算提前577ms→Consumer首次获得早456.5–573.0ms；6行从deadline miss到hit，10行本来即可由Canonical等视图按时服务。这样读者看到request、ACK、physical release、execution、actual delivery五个不同事件，并看到受益者是其他合法工作。不要把16个obsolete proposals全部画成16次用户期限失败。

K0/K1中675个严格同processed tensor/prompt/audio/peer-order对全部完整输出相同；六个sync后继批96行均实际消费。补充`same_F_support_v1/RESULTS_FINDINGS.zh.md:3`与`RESULTS_v1/ALL24_SUPPORT_PARTITIONS.json`/固定96行表确认，96/96未改prompt、完整原文与future-selected严格同F Canon相同。三次R1新增期限行6/6/1不是仅进度条增长，而有完整文本支持。身份：primary support=`fde6272b494db43a66eebea7444d7c9d1037e687`，96行补充=`5d1de66a31fb0921206da33256a93f5d29552e58`。

更有解释力的共同场景事实也尚可强化：同24格中358个decode跨Canonical且目标未覆盖事件，242完整输入兼容、116不兼容；242兼容行均实际Consumer完整应用（`RESULTS_FINDINGS.zh.md:72`、`detail/LEGAL_PRESSURE_CONSUMER.json`）。它证明应保留的正常计算与应退出的无用计算确实共存，不只是两个独立demo。正常行最多17newtokens、1.2919s，因此不夸称合法超长压力或watchdog一定误杀。两相位K交互仍mixed，图只承担测量因果链，不取代全部配对端点。

### 12.3 一个很强的技术难点图：少做35行，为什么模型工作仍增加？

`final_evidence_integration_20261028/PAID_WORK_RESULTS.md:19`以及`records_v2/cost_v2/BATCH_PAID_WORK.csv`有已经独立闭合的批次账本：同c16错峰开发负载，Immediate执行102个Private rows/14batches，Fixed只67rows却17batches；GPU0 synchronized model-wall从20.692s变为20.854s，GPU0 lease22.677→21.926s。原六臂都保持135Canonical历史、14/687WER、810Authority rows；181个physical batches全收费，GPU0/GPU1时钟不相加为运行墙钟。

原运行runtime=`ffaa7ab41dd8d6099efd0eb9abe2334951dc5932`；一次开发重复。重构source=`ca5e04bbb513b703f9aa46d03c6f6fcd08315909`，`records_v2/cost_v2/GATE.json:2`为`PASS_RECEIPT_PHYSICAL_AND_COMPONENT_RECOUNT`；另一独立实现`53246842be8f51dcf4dc1aba488dda40a004bbc0`在`independent_check_v2/GATE.json`得到`PASS_SECOND_IMPLEMENTATION_RAW_RECOUNT`。

这是一个正面的**测量与系统解释机会**：行级discard/非使用不是physical resource saving，batch形态与同步边界决定工作。建议在执行图旁做小型三列glyph（rows、batches、model seconds），让“102→67但14→17且20.692→20.854”一眼可读，用来解释为什么本设计严格按BatchDrained/实际paid work收费。无需展示六个失利控制器的完整性能目录，也无需把等待算法包装成功。混有obsolete行的batch paid time仍非该行可避免成本；原表0个entirelyobsolete batch支持这个限定。

### 12.4 完整输入不只是正确性标签，也会改变真实神经工作量

`context_recovery_20261028/PAID_INPUT_RESULT.md:3`及`publication_update_v5/paid_wait_operator_v9_v1/SUMMARY.json:2`保存两例×old/new完整输入×2repeat，共8paid batches；execution=`591c462317d61eda036668abf626fc90133eb9cd`，GATE=`PASS_BOUNDED_REPRODUCTION`。声学tensor与原peer顺序固定，完整Z/P/text/EOS重复一致，newinput输出匹配原实际服务receipt。

- 单行case，prompt padded width351→337却newtokens7→21，owner lease0.461/0.455→1.353/1.204s；两边均EOS，非触顶。
- 六行case，paddedwidth139不变，目标tokens20→12，wholebatch lease1.534/1.552→1.276/1.223s；两板能量均值250.27→201.23J。

**值得采用的论点**：反馈改变的不是一个可以随意换标签的version bit；同音频下的完整实际输入同时影响结果、计算时间与batch共享资源。这让EL/冻结输入的技术意义更具体。两个方向同时出现，恰好解释为什么不能用“更新父状态一定更便宜”或token计数预测调度收益。建议§2/Discussion两句或附录双箭头小图；不能作为新调度器提速，oldinput只在付费operator中执行，从未安装/发给Consumer。lease端点未逐项export，现有值是原source实际测量scalar，不假称重新构造端点。

### 12.5 历史root证据的回收：可以丢掉归档，不能丢掉未来合法性

`evidence_retirement_20261026/RETIREMENT_OBLIGATIONS.md:15`给出live closure应包含实际applied roots、pending publication/ticket、尚有权限jobs、输入义务及物理结果身份；endpoint+path hash不足以支持未来可能match的中间cut。`screen_v3/RETIREMENT_SCREEN.json`本次按method读取：24构造场景中eager endpoint contraction仅6等价/18失去合法迟到进展；fullhistory、indexedfull、activeroots、checkpointACKepoch、exactrepair均24/24等价。包保存`EXECUTION_v3.json:2`的`6270a811822c9c4c7b38f4a4b3fdf453c6b0f622`与`EXECUTION_v4.json:2`的`b4a4502dfcf796b3c509b81ecb93312bcace51e2`；终态`ACTIVE_STATE.json:13`指v4并指最新screen_v3，screen本身没有逐run execution commit，因此不能从包最新指针补称该screen已有独立完整source冻结。纯CPU synthetic，非新GPU证据；作为条件性设计见证合适，若进入主文量化结论应先补原run身份映射。

同包`CHECKPOINT_PROCESS_CUTS_v1.json:2`的27次真实CPU `os._exit` cuts，在write前、半帧、fsync、rename、archive及tail边界对三种策略验证相同observations、accepted debt和physical lease义务；Windows不能据此声称目录fsync/断电耐久。这些是设计支持：**保存的是未来决策所需依赖闭包，而不是一味保存所有历史或只留最新root**。可给v9 §4 control-history补一句充分条件解释，不加GC算法贡献。与当前longstream最多64个unpinned diagnostic windows的实测相配时，应分清liveclosure、cumulative model/application state与archive storage，避免看起来只会“永远保留”或只靠有限sample清理。

### 12.6 根docs/reports还能补什么：保证的成本可改进，而非只能放松保证

`DSN_PRIORITY_RESULTS_AND_STRENGTH_20261005.md:15`保留single-WAL不利CPU结果；同GPU活动真实group-ready只合并已合法ready的不同会话、无额外收集窗口、fsync后才install/ACK。c16中0.6B同步次数98→9、摊销append+fsync10.670→1.767ms/commit；1.7B98→8、11.247→1.626ms；相应共同frontier commitP99也略降（23–24行）。这能以一句话说明持久性没有通过提前ACK换速度，优化的是already-ready事实的同步，而非安全谓词。它是常规技术的良好实现与成本证据，不是独立贡献。

`results/dsn_crash_20261004/multi_session_campaign_v4/summary.json:2`另保存64scenarios×3进程退出=192CPUdeaths、每scenario8sessions/64unique commits、ackhistoryloss0/duplicateapplication0；四类cut各16scenarios，含tornwrite、fsynced-before-apply、applied-before-ACK、acknowledged及sameID conflict/retry。`RUN.json`标记历史codecommit=`7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f`并有实际script/source hashes，不能用此HEAD假定全部dirtysource干净冻结；若取回必须保留它的hash-based身份边界。更适合作为artifact故障矩阵的历史CPU层，回答“只有一次SIGKILL吗”，不把192加入currentnative的8worker/36trial分母。已有native实际同源故障应继续主导正文。

这些旧报告中有不少好看的riskcontroller/reshape/Whisper速度数，但属于统计风险、不同adapter或不同保障模式；本次没有发现它们比上述四个机制对象更值得挤占v9主文。反而`phase5_system_hardening_report.md:61`的ON保护后性能收敛、`phase7_reviewer_defense_report.md:105`全offered排队延迟，提示可沿用**为哪一种可观察服务付出成本**这一写作组织法，不必把所有历史数字重新带回。

### 12.7 简明取舍

若只能再加一项：优先**AU的M content-only后果段**（§6）。若可加一幅额外系统图：优先**trusted-render三时钟恢复图**（§12.1），明确历史core合同。若希望现有图更具技术含量而不添新实验：把当前K摘要画成**request/ACK/drain/同工作/实际消费**的真实泳道（§12.2）。paidbatch反例与双向输入成本各留一句/附图，liveclosure条件补§4短句；这些都能增强问题—技术难点—机制的连接，而不增加主贡献数量。

# RevTrace DSN 2027 — Phase D：认证滞后、可见状态一致性与系统泛化（Codex 正式执行目标）

**目标性质**：面向 DSN Research Track 的机制研究与实证强化。优先级按科学价值与可证伪性排序，不因截稿时间削弱实验真实性；本阶段不重写正文、摘要、题目，不处理匿名，不预设新机制必须提高数字。

**唯一研究问题（One Ping）**：在异步、不同粒度的有状态生成服务中，可信认证落后于暂时显示时，如何把**持久化认证事实**、**可撤回显示**和**可继续消费的状态**协调起来，并以可证明的安全语义与可测的端到端代价实现？

**核心假设（不是已证实定律）**：增加 Authority 调用频率不一定减少可见回撤；当认证计算需求、同会话父状态串行、跨会话容量与全量快照发布相互作用时，较细粒度的认证可能增加回撤频率和面积。必须通过事件级分析、同口径归一化和控制实验分离原因。

## 0. 固定真实基线，禁止混用源码身份

1. 使用 GitHub `zhouz4884-coder/RevTrace` 的 `experiments/phase_n_20261021/`，以其中 `runtime/` 和实际 T1 v4/T3 frozen_source manifests 为主实验代码源，不能把 repo 根目录旧 `src/` 当成测量版。
2. 先读 `AGENTS.md`、`FINAL_DECISION.md`、`PROPERTIES_ABC.md`、`T1_FACTORIAL_AND_BLOCKING.md`、`T3_HOLD_SENSITIVITY.md`、`V0_ALIGNMENT.md`、`V1_VERIFICATION_AND_COST.md`、`CLAIM_EVIDENCE_MATRIX.md`、`EVIDENCE_INDEX.json`、`SOURCE_AND_PROTOCOL_AUDIT.md`、实际实现和测试。
3. 保持双 3090、FP16 Proposer/FP32 Authority、Qwen3-ASR-1.7B、fine 2s、rho 1/3、真实 group-ready WAL 的可比主轴。任何新增 rho/分段、客户端协议、仪表或调度改动必须单独版本标记。
4. 第一阶段必须核查所有最终报告表数值与其 `tables/`、原始 trace 哈希和代码身份；不把单个重复音频的多个 slot 当作独立样本；不合并 Fake-CPU、真实 GPU、故障注入与自然行为。
5. 新实验独立目录、冻结协议、源哈希、种子、环境、Raw JSONL/CSV、逐项失败记录、清晰 GO/NO-GO；不得用选择性样本或事后调参调整主结论。正式实验前可进行诊断 scouts，但必须明确分层。

## R0：先排除错误解释（只读审计 + 最小 CPU 探针）

**R0-1：回撤定义与计数审计。** 从 T1 v4 `events.jsonl`、真实 `canonical-display`、`display`、`commit`、`install-ack` 和 `VISIBILITY_AND_RETIRED_WORK.csv` 重建每次回撤的原因与前后事件。验证 Fine-D 77/61/77 与 Coarse-D 2/2/15 的确切事件定义。每个 Canonical Commit 统计：pre-commit visible frontier、new committed frontier、Private generation/root、pre/post text、已提交/已显示时刻、previous/next authority model-call、WAL 与纠正事件。

**指标必须区分**：
- `arrival_lag(t) = max(0, audio_released_frontier(t) - F_commit(t))`：认证相对于已到达音频的滞后；
- `speculative_lead(t) = max(0, visible_tentative_frontier(t) - F_commit(t))`：推测展示相对于认证前沿的领先；
- `rollback_audio_k = max(0, visible_frontier(t_k^-) - F_new_k)`；
- `rollback_event_rate = rollback_events / canonical_publications`，并报告每 audio-minute、每 source/session 的频率；
- `rollback_depth` 的 P50/P95/P99/最大，`rollback_audio_seconds_sum`、时间积分与恢复至先前可见前沿的时长；
- `erased_characters`、合法文本修订次数、现有 `withdrawn_audio_wall_area`，注意文本字符删除不等于音频回撤或语义错误。

**R0-2：消除混杂。** 依 source、session slot、repeat、English/Chinese、rho、每次 commit、batch size、authority service demand、Private lead 条件分组。必须报告 Fine 有约 279 而 Coarse 约 98 Authority opportunities 的分母差异，及 Coarse r2=15 的运行间变异；rho 改变 segmentation、条件输入和真实文本，不将所有差异归为延迟。先按事件时间解析再决定是否可以主张“认证滞后介导了回撤”。

**R0-3：文本来源及边界审计。** 当前 `live_qwen.py:_finish_commit` 把 `result['text']` 写入 WAL、设置 `s.text` 并发布 canonical snapshot；`tc_live_worker.py` 从选定 `token_ids`、rollback prefix、`parse_asr_output` 构造 text/state tokens。核查 `result['text']` 究竟是累计转录还是区间输出、是否可在可信 Coordinator 中从 Z+parent+adapter 逐字节稳定重建。不得仅因 hash 了一个未经独立校验的 Worker 字段就称“可信渲染”。用只篡改 `text`、不改 `Z/P` 的 CPU 注入证明当前边界是否能 fail closed。检查英/中、EOS/Cap、Unicode、带/不带特殊 token 和重启恢复后文本一致性。

**R0 输出**：`R0_MECHANISM_AUDIT.md`、`ROLLBACK_EVENT_CASES.csv`、`ROLLBACK_NORMALIZED.csv`、`TEXT_BINDING_GAP.md`，明确支持、反驳、未知，并给出是否可进入 R1 的理由。

## R1：验证认证滞后 → 回撤的因果机制（不能把相关性包装成定律）

**R1-A：历史联合轨迹。** 选择相同 source/repeat 下的 Fine-D、Coarse-D、Barrier，绘制 `audio released / committed / provisional visible / ever displayed` 四条前沿及每个 commit 的撤回箭头；标出计算/排队/WAL 区间。报告 worker service 46.104 s 与 22.814 s 对 40.295 s 到达窗口的有限窗口比较，但不得称为稳态 U>1 证明或纯状态锁因果归因。

**R1-B：隔离发布与计算。** 先使用冻结服务器 `display/canonical-display` 真实文本及顺序做纯 CPU publisher replay（只改变消费/呈现策略，不改 Canonical Decisions），得出回撤能由发布策略消除的理论空间；该 CPU replay 不作为 GPU serving 性能/自然发生率。再用相同 rho、音频、种子、Worker 配置的真实 GPU 最小受控实验：适度改变 authority result delivery 的完成时刻或负载强度，记录 canonical 全历史是否相同、lag 是否改变、回撤是否随之变化。所有注入在计算后不伪造 GPU model-call 时间。不要凭自然 rho 对比直接宣称因果。

**R1-C：分类回撤。** 将发布回撤至少分为 (i) stale/superseded private 已应退休；(ii) 提交内容修订造成的必要文本撤销；(iii) 当前全量快照覆盖超前 Private 显示产生的潜在可避免撤销。第 (iii) 类在没有新的祖先兼容性证明前只能叫“潜在可避免”，不能直接宣称可无损保留。若真实事件无法可靠分类，输出不可识别性与证据缺口，不编造原因。

**R1 Gate**：只有当事件级证据证明回撤与阶段滞后及版本覆盖有稳定关系，才将其作为 DSN 核心机制洞察；否则视为当前 adapter/发布接口条件下的经验现象，不命名为普遍定律。

## R2：Property D——认证状态到显示消费的一致性，先证明能做什么

**D0（已实现安全基线）**：当前 A/B/C + WAL 成功后版本化 full canonical snapshot，允许合法文本及当前可见前沿回撤；确保存储前不 publish。先完整复算 D0 的行为，不能因为它回撤就把它标成错误。

**D1（必要改造，可信文本绑定）**：审计 `Render_χ(Z_v,H_{v-1})` 的可实现性及字节一致性。若可信 Coordinator 可独立重建，采用可信重建并检查 `result['text']`；若确实需要 Processor/Tokenizer，分离其实际运行成本并保证输入配置匹配。若不能确定性独立重建，只能在可信 Authority 选择路径中明确绑定被选择的 canonical text 摘要，陈述相应更窄的信任假设。不得为了通过测试改变原 `Z/P` 表示。文本 tamper、Unicode、错误文本、错 EOS、WAL 失败和重启必须 fail closed 或报告为什么超出保证。

**D2（机制选择，不预设安全拼接）**：比较三条路线：
1. `Full Snapshot Replace`：D0，安全完整，不抹平可见回撤；
2. `Two-lane Certified/Provisional View`：保留稳定认证通道和显式标注的临时通道，在新的 canonical parent 到来时，失效 tentative 的状态必须展示为失效/待重新校验，不能充当有效认证后缀；
3. `Proof-carrying Eligible Suffix`：只有能够证明新 Canonical Parent 下生成祖先兼容、可确切拆分 audio/token 对齐或通过可信目标复验的 suffix 才可并入 view。若现有 Qwen adapter 无可靠 token–audio 边界，先做 oracle/CPU 可行性上界；不能仅凭 `b>F`、`generation` 或字符串最长公共前缀无损拼接。

**安全负控**：故意使用 naive longest-common-prefix splice、latest-audio-frontier-wins、blind full-text append，记录其会在怎样的语言/祖先冲突中破坏正确输出；只作为不安全消融，不作为真实工业基线。加入强 ASR display stabilization：LocalAgreement(2/3) 和固定稳定等待（相同经过保护的 Canonical Engine），报告它们的 flicker/timeliness 权衡；不要将一般 ASR 字符稳定化称为新发明。

**Property D 候选保证**：
- `D-Canonical`: 每个下游接受的 certified snapshot 映射到 WAL 中已安装的 `(session, epoch, version, transaction, F, Z, P)`，文本与可信 Render/绑定来源一致；
- `D-Ordering`: canonical version 不可被旧 private snapshot 覆盖；旧 generation/private 父状态可以继续独立推测，但不能未经兼容性核验拼到更新 canonical prefix；
- `D-Recovery`: 进程重新启动后最新认证快照可重新发布并恢复被认证消费视图。首先检验可靠 FIFO 本地队列；乱序/重复/断连可作为边界扩展，但不以“重新发明 TCP/可靠消息”作为贡献；
- `D-Liveness`: 在 Worker 最终返回/超时、owner 公平运行、有限输入等前提下，已提交 Canonical Snapshot 最终可被消费端观察，且不因过期 private 阻塞。

**注意**：没有 Token–Audio 对齐时，不能承诺任意推测后缀准确划分；音频认证前沿单调 `F`、曾显示前沿 `D_ever` 单调，不意味着当前 `D_visible` 或字符字符串单调。若 D2 无法在保证正确的前提下降低误回撤，只保留 D1/更窄的 Property D，不宣称“全部消除回撤”。

**R2 测量**：合法 commit/provisional 的 end-to-end CPU/online publish costs、`rollback_event_rate`、depth/area、字符擦除、连续可见覆盖时间、certified view age、correction-to-visible lag、双时限 Goodput、WER/CER、canonical/history 一致率、WAL 重启/恢复。增加真正的实时消费端而非仅 server event；禁止把 client render 等同于 network/browser 体验。对于不改变 GPU 的 render-only 策略先 CPU 回放；存在真实可行新机制后再做 3090 配对 GPU。

## R3：强竞争基线 X1——区分系统贡献和自己修的 Bug

在同 GPU/模型/输入释放/认证契约/WAL/显示事件 schema 下，至少比较：
- `Sync Barrier + OCC/WAL`：保守可靠的双阶段架构；
- `Naive FIFO/Latest-Wins Async`：仅作为明显不完整协调的消融，不能称作所有工业框架的代表；
- `Standard Safe Async + Versioned Snapshot`：具有真实过期取消、canonical precedence、最简版本/epoch fence 的最佳常规安全异步组合；允许它实现相同 A/B/C/D 语义，若结果相同则明确是方法等价/独立重实现，不隐去；
- `RevTrace A/B/C + D0/D1/D2`（只有被 R2 正确性批准的配置才能入正式组）；
- `LocalAgreement/stabilization display`：用于识别 ASR 既有显示稳定化手段与因果可信状态协议的作用差异。

所有相同 rho 的方法需固定相同 authority canonical 内容历史与独立 WAL replay；不同 rho 改变声学切分，单独报告识别质量。衡量 Quality/Goodput/Stability/CPU/IO/GPU，不能只用错误的 Legacy 来证明自己先进。源码中若常规安全组合实现了相同的所有调度规则，承认协议可复现，转而明确贡献在规格、证据与机制条件；严禁宣称“传统技术不能组合”。

## R4：现实流量可用容量 X2——不预设必过 2 s/8 s SLO

双 RTX3090 先做带完整音频覆盖、合法 canonical display 的 **scout**，选取 `c2,c4,c8,c12,c16`，同步脉冲和预先冻结的 uniform-stagger arrivals 两种模式；Poisson 到达若另做须单独定义，不把均匀错峰写成 Poisson。所有音频必须按音频时间点真实释放，不能提前消费音频。选出靠近 SLO 临界点的负载，再用 `Fine/Coarse × Barrier/Decoupled` 以及已通过 R2 的 D 与 X1 强基线进行 ≥3 次 fresh repeat。也可以追加 burst/heterogeneous-duration workloads。输入源不同于初始 12-source 开发池，并以 speaker/source 为统计聚类。

联合 SLO 第一层：同一 2s + 实际末端 frontier 的合法首次显示、持久 commit 期限同时达标的音频秒数 / wall time；第二层：整个运行（包括未完成项）的 display P99 与 commit P99 同时过线的最大可达音频容量，两个不可混淆。报告 `2 s/8 s` 等预先声明网格，但**不得预设 c4–c12 一定可达**。若全部未达标，保留 Pareto 前沿，调整源/负载范围前需单独新协议而非改历史阈值。可见性（当前版、ever、撤销面积）与 WER/CER 作为并列指标，不能为了减少回撤而降低显示频率隐藏信息却不计延迟。

## R5：跨家族与真实失效 X3（先小规模诊断，扩大证据而非凑数）

Whisper-small.en 的 F2 要确保实际 Processor/Decoder 消费了替换的历史 Token/Prompt；前文中没有消费 Prompt 的 cold-start 是合法负控，不能算有效故障。冻结 ≥16 条新独立语音/说话人和有效非空历史，按顺序记录实际输入前后 digest、canonical/cheap-check/authority、未来传播 WER 与持续时间；如果 ASR adapter 不能合法迁移 R2，记录接口差异，不强行宣称通用。保留一小时 Whisper 非 EOS/循环的独立历史结论，不虚构 Quarantine 修复。

## R6：V0/V1 NO-GO 证据位置与 Realized-input 小型验证

保留既有：C2 原生完整候选在所测 Coarse 执行中 0/98 及时可用；付费 C3 0–1/98 及时且参考一致；C1/C3 fixed-state 精确验证合法，而线上全成本门槛失败。把它写为 `candidate unit × intended context × runtime readiness` 的边界实验，不能声称任何 speculative verification 都不可能。**不启动 V2、不开发 KV-reuse fallback。**

对 `chinese-05` 523 vs 524 / `<|audio_pad|>` 进行多 batch/长度/语言独立复现，区分合法 padding、真实 effective input、后续 Token/Projection 改变；先解决实现链等价判断，再考虑能否构成单独贡献；不要把一个 CPU 可重复预处理差异推断为自然 GPU SDC 或质量故障。

## 正式交付与停止条件

每阶段至少交付 `DESIGN_FREEZE.md`、`SOURCE_MANIFEST.json`、`RUN_MATRIX.csv`、`AUDIT_REPORT.md`、关键 CSV/JSON 与完整原始证据索引、失败/重跑历史、CPU 和 GPU 证据分层、GO/NO-GO。最终给出 `CLAIM_EVIDENCE_MATRIX.md` 和 `DSN_NOVELTY_DECISION.zh.md`，对每一条主张写清：源文件/执行协议/反例/竞争方法/收益/条件/反解释；标记可写进正文、仅讨论、禁止主张。

**停止/降级**：
- 如果无独立文本重建或可信记录，D1 不得给“published bytes certified”强保证；
- 如果无法获得合法 suffix/ancestry 兼容性，D2 的安全拼接 NO-GO，只报告上界/条件；
- 如果回撤主要来自声学文本纠正而非迟到认证，不能称 retraction storm 因果机制；
- 如果强安全组合和 RevTrace 等效，诚实报告；
- 如果 SLA 扫描无双 P99 通过点，不调阈值挑结果；
- 如果 Whisper 故障未真正被消费，不计入有效 F2；
- 所有 GPU 实验前先审实际模型、硬件负载、文件散列、时间戳、仪表 overhead，再运行；不允许改正文“救结果”。

**执行顺序**：R0 → R1 → R2（先可信文本 D1、再 suffix/overlay feasibility）→ R3/X1 → R4/X2 → R5/X3；R6 是并行轻量核查。允许根据前阶段证据合理收缩，而非机械完成所有格子；每次启动额外 GPU 矩阵必须明确新增哪个可证伪的科学结论。

**最终科学目标**：证明或否定：`safe admission alone` 不保证有用且连续的下游可见状态；真正的创新若成立，应是 `authority-selected state + causal dual-clock execution + demonstrably correct consumption/render/recovery` 的统一、有边界的可执行契约，而不是一个额外判断阈值、新 verifier 或未经证据支持的“必然降低回撤”定律。

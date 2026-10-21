# Codex 执行任务：RevTrace–DSN Phase N（2026-10-20）

## 一、总目标和不变约束

围绕“可信上下文绑定的状态准入 + 两条时间线的因果协调 + Durable Canonical Display”验证 RevTrace 在 DSN 2027 的系统贡献。**先查现行代码与实验协议，再改实现，再进行受控复测；实验结果决定论文叙事，不反过来。** 本阶段重点完成 T1、性质 A/B/C、V0/V1，T3 为有界补测，V2 在线验证器为条件触发，不自动实施。不得为了制造正结果改动实验定义。

先阅读仓库当前 `AGENTS.md`、`RESULTS_REPORT.zh.md`、`E0_invariant_audit_20261015.md`、`EVIDENCE_INDEX.json`、原 DSN 文稿及最新源码：`src/revtrace/live_qwen.py`、`src/revtrace/dgft.py`、`src/revtrace/durable_journal.py`、`scripts/tc_live_worker.py`、相关 runner/auditor/tests。**以现行工作树为准**：2026-10-15 审计 ZIP 是历史快照，2026-10-20 E1/E2 已有改动。先生成文件哈希、Git 状态/差异、测试基线与 Source→Claim→Trace 对照，保留用户工作树，不进行 destructive reset，不混入另一篇论文的改动。若关键原始证据只在远程设备，先按已授权路径读取；没有登录权限则列为 BLOCKED，不猜数据。

固定主环境：Qwen3-ASR-1.7B；2×RTX3090；FP16 Proposer、FP32 Authority；Fine 2s、Coarse rho=3；同一音频池/负载槽/来源去重、到达轨迹、microbatch、生成预算、WAL、序列化和重复次序。GPU 结果与 CPU fixture、离线估算分别标记；所有实验依 `AGENTS.md` 使用实验 ID、冻结配置/种子、源码与环境哈希、原始文件路径、独立复算、GO/NO-GO 决策。

## 二、T1：修复后 2×2 Factorial + Enqueue 前等待归因（P0）

1. **先审计再埋点**：检查 `LiveQwenScheduler._ready/_dispatch/_receive/_commit_ready/_finish_commit`、Executor 批处理和 WAL 同步代码。`s.auth_busy` 仅表示同会话已派发未接收，不自动等于 GPU 正在执行；Worker 占用可能与本会话自依赖同时成立。`auth_result != None` 不自动等于 Barrier 阻塞。不可用 `_ready()` 短路结果直接推断“纯父状态阻塞”。
2. **双口径记录等待**：对已到达、尚未发行对应合法 Authority Job 的会话记录原始位图 `{self_inflight, self_exec_on_gpu, commit_pending, barrier_hold, candidate_missing, worker_capacity_occupied, other_session_jobs_on_worker, coordinator_wal_sync, scheduler_delay}`，附 job ID、batch members、当前 committed frontier/version、音频可用时刻、状态进入/退出时刻。可另导出互斥的 *descriptive partition*，但重叠时长不得重复相加，优先级归类不得被说成因果贡献；若不能区分，用 `mixed/unknown`。用事件驱动区间累计，不做扰动调度的高频重采样。
3. **完整生命周期时间戳**：`audio_release/ready → eligible → enqueue → GPU started → GPU completed → coordinator received → certificate → WAL fsync → installed/ACK`。对 WAL 阻塞整个事件循环的时间单列。报告 P50/P95/P99、条件占用比例、分组置信区间与实际 Batch/Worker 数；区分 Ready-to-Enqueue 与 Enqueue-to-Start。相同音频采样前沿 q（2s 与实际末端）比较，不用不同 rho 的 Job 中位数之比宣称“状态锁加速 18×”。
4. **匹配 GPU 设计**：Fine/Coarse × Barrier/Decoupled-Lazy、c16、hold=0、每单元 3 次独立重复，计 12 GPU cell。统一 Canonical Display 口径，报告有效显示 P99、提交 P99、双 SLO Goodput、xRT、GPU J/audio-s、音频前沿滞后、WER/CER、过期发布、任务数量、等待原因。保持同 rho 内的 Canonical Output/WAL 等价；不同 rho 改变声学切分，不要求跨 rho Token 完全一致。新增埋点前后同输入成本对照，检查是否显著改变调度。
5. **因果归因检查**：若 Self-Dependency 与 Worker Busy 同时存在，保留 BOTH；用安全 Barrier/Decoupled、Fine/Coarse 配对及有界 CPU 调度反事实区分解释，绝不单凭位图把所有 pre-enqueue wait 算成 state-dependency HoL。

验收：所有现有性质与独立 WAL 审计通过；同 rho 三重复的 Canonical 结果匹配；完整等待阶段可复算；实测解释 Fine/Coarse 的 pre-enqueue 差异（可以是混合原因）。若发现真实实现 bug，先最小修复/单元回归，再按冻结协议重测受影响 cell，报告修复前后而非修改结论。

## 三、性质 A/B/C：因果协调与真实 Canonical Display 语义（P0，与 T1 联动）

- **A：Obsolete Proposal Non-publication**。Proposal 结果发布时必须属于当前有效 generation，目标音频前沿严格超出已持久化 Committed Frontier；旧 Parent 本身不自动非法。过期或已撤销结果显式 retired/skipped，不能覆盖较新的 Canonical Display。记录被退休任务已消耗的 GPU 时间，未分发跳过的任务单列。
- **B：Bounded Reconciliation**。在单会话一个 in-flight Proposal、Single-owner 和公平调度/任务最终返回等前提下，已覆盖的 Proposal 在有限调度轮次内被退休或跳过，下一次可分发任务从合法父状态和音频前沿继续。对不会再有 Private 任务的情况显式退出，不制造永久等待。
- **C：Canonical Display Coverage**。WAL 确认并成功安装 Canonical Transition 后，应由真实对外显示事件发布可信 `Z`/实际转录文本、音频覆盖、Canonical Version/事务 ID（不是把反馈 `state_tokens=P` 当成给用户看的文本）。即使已有更远的 Provisional Display，也必须执行版本化 Canonical Correction 或显式失效处理；不要只在 `D < F` 时发布。所有已认证音频前沿 q 在 drain 完成后都有真实 Canonical Display 覆盖。区别 `F(t)`（已提交前沿）、`D_ever(t)`（曾经有效显示的最大覆盖前沿）和当前可见文本版本；**音频覆盖单调不等于字幕字符不回撤**。如果没有 Token↔音频的可靠对齐，不得声称能无损 patch 保留未来字幕，改用带版本的完整快照/撤销协议并报告回撤/闪烁。
- 在 CPU 确定性交错下测试：Proposal 快/Authority 慢、Authority 快/Proposal 慢、Commit 时已有更远 Private Display、末端 Proposal 被跳过、旧 generation 迟到、WAL 失败、恢复/相同请求重试。检验无 Canonical 污染、无过期新发布、提交事件与真正显示事件映射、已确认版本不被旧结果覆盖、无覆盖缺口；精确区分不发事件与发出后被修订。
- 产出可复核的性质定义、状态转移表、实现级对应和正式回归测试。不要把“修了一个 if”描述成不可能性定理，也不要未经证明声称文本永不回撤。

## 四、V0/V1：Candidate–Authority Alignment & Readiness（P0；V2 暂缓）

1. **先复核实现**：旧版 `tc_live_worker.py:verify_tokens` 中 `verification_tokens=64` 是把候选宽度补齐到 64 的倍数，而非直接把所有候选截到 64；需对照最新版确认。原 `matched==len(candidate)` 缺乏完整 Stop/EOS/上限认证；不得先声称有 64-token 截断 Bug。
2. **统一实际模型输入**：记录 `source_id`、`audio_end_sample`、真正 wav/特征摘要、`job.prompt_tokens`、`chunk_id`、Rollback Prefix 最终文本、`processor.input_ids/attention_mask` 与音频特征摘要、language、dtype、batch/pad、max_new_tokens、停止 Token 与 Adapter、生成随机性和开始/完成时刻。音频前缀相同只在 source/end/处理链相同时成立；因 `chunk_id>=2` 会触发回滚前缀转换，C2-C3 不能预设只有 prompt_tokens 一项差异。
3. **三组正式对照**：C1=2s 同父/同目标 Fine Candidate 与可信 Fine Authority（须实际检查同父）；C2=6s 原生 Private Chain 最后候选对正确 6s Coarse Authority；C3=额外生成的 H0 根对齐 6s FP16 Draft 对同一个 Coarse Authority。C3 新 Draft 的时间/能耗必须计入；若要单独隔离 Prompt 影响，可用同一候选在两种可信上下文重评分作辅助对照（不是独立生成结果）。探索与冻结正式来源分开。
4. **检查三维**：Ancestry Alignment（处理后的真实输入）、Coverage/Termination Alignment（覆盖区间、EOS 或合法 token-cap 等价、`Phi_chi`）、Temporal Readiness（在 Authority 合法可运行/可分发的时刻，候选是否已就绪，不得后见性地将晚到候选算作提前就绪）。报告 eligible fraction、ready fraction、Clean Accept、Wrong Reject、精确 FP32 Greedy Token/Projection 等价率、首分歧位置、fallback 比例。
5. **V1 完整正确性**：针对真实候选的 1..m 所有 Token 检查目标 FP32 条件 Argmax，正确处理 prompt/candidate 位置偏移、EOS/合法 stop、提前停止、达到生成上限未 EOS、padding、不同批形态、原始 adapter 的解码和反馈投影。FP16 的 Margin 只能作为诊断门槛，不可直接声称 FP32 Canonical Equivalence。所有 accepted 候选须与独立 FP32 Authority Oracle 的完整 Token 序列和状态投影一致；同输入复跑。拒绝候选走完整 FP32 Fallback 并计全成本。
6. **成本与尾延迟**：分别计 Draft（含额外 Root Draft）、Verify、Reject/Fallback、Worker 容量占用、Commit P99 预期风险。已有 `use_cache=False` 不存在可直接复用的 Prefix KV；不实现新 KV-reuse Fallback，除非另立独立等价性与内存成本协议。不能用离线 1.347s 与 7.801s 推算线上加速。必须分析候选等待重新耦合 Authority 的问题。
7. **V2 GO/NO-GO**：只有 V0 证明有足够数量的同契约且按时就绪候选、V1 证明接受无 Canonical 偏差，并且包含 Draft/验证/完整 Fallback/队列尾成本的收益模型显示有实质空间，才请求启动小规模 Online Selector。若启动，只允许非阻塞机会主义路线：Authority 可运行时无候选就直接独立生成；绝不等待 Proposal 或用 Deadline 绕过可信认证。正式 GPU c16 比较必须实测 Commit P99，不因均值降低就宣称服务收益。否则明确 NO_GO_ONLINE_SELECTOR，保留负面结果作为机制边界。

## 五、T3：交付延迟敏感性（P1，前三部分通过后执行）

基于当前 c16 工作负载，只增加：持续 Hold=1.5s、3.0s，以及固定种子的稀疏 6s 毛刺（例如事先指定每 6 个 Fine Window 的 1 个），Legacy/Lazy/Barrier 三个策略；先每配置 1 次 scout 查合法性，再冻结并各跑 3 次独立重复。Hold 限于真实 GPU 计算完成后的结果交付环节，不伪造 GPU kernel 时间。需要同配置无 Hold 对照；若新增仪表或显示协议使旧实验不可直接比较，就复跑必要的 0/6s anchor。报告正常、持续阻塞和稀疏阻塞条件下的有效 Display/Commit P99、联合 Goodput、过时发布、retired/skipped/inflight、GPU J/audio-s、WER/CER 和最终 Canonical 状态。不能把人工注入频率称为自然故障率，也不能预设存在“相变点”。

## 六、质量红线、停止条件与交付

- 代码更改通过当前仓库完整测试集、E0 交错、E1 错上下文/Authority 隔离、E2 lazy/Barrier、WAL 重放审计，并补新 A/B/C、EOS/cap、阻塞归因测试；最终审计须独立于生产调度代码，从原始 Trace/WAL/Power 复算。
- 对同 rho/同声学切分、匹配输入，Canonical State 与 WAL 不得退化；跨 rho 的输出差异应独立报告 WER/CER，不能默认为 bug。保留 legitimate oracle 和重复运行。
- 每个指标明确分母：c16 是负载槽，12 源不是 16 个独立样本；三次重复、复用音频、CPU fixture 均不能混为独立声学来源。按匹配重复计算吞吐比，报告中位数、范围、异常和下降尝试；缺少可观测字段时用 `UNKNOWN` 而不是推算填补。
- 若 T1 发现 pre-enqueue 主要是 Worker Capacity，不要改写成 State HoL；若 V0/V1 候选不合法、太晚或收益为负，不继续 V2；若 Lazy 只在注入压力下加速，要明确边界。任何门槛不通过先审源码与实验协议、做同输入 Oracle，再修原因与复测，不靠改写论文结论解决。
- **本轮不修改正文、标题、摘要或随意新增创新模块**，只交付证据后再决定写法。不能提前声称 impossibility triangle、18× 纯状态锁下降、100% ancestry effect、零文本回撤、零故障率或线上 verifier 加速。

交付目录包含：`SOURCE_AND_PROTOCOL_AUDIT.md`、`PROPERTIES_ABC.md`、`T1_FACTORIAL_AND_BLOCKING.md`、`V0_ALIGNMENT.md`、`V1_VERIFICATION_AND_COST.md`、可选 `T3_HOLD_SENSITIVITY.md`、`EVIDENCE_INDEX.json`、`CLAIM_EVIDENCE_MATRIX.md`、`FINAL_DECISION.md`，以及必要的独立审计脚本、CPU 回归、原始 Trace/CSV/Power/WAL 的索引与哈希。`FINAL_DECISION.md` 必须给出确定性的 GO/NO-GO、拒绝的假设与替代解释、是否值得开展 V2、对 DSN 主贡献的可主张范围，并标出尚未验证事项。大型模型、音频、日志留在指定实验盘，仓库仅保留有界证明材料。

执行顺序：**代码/协议审计 → 性质 A/B/C + T1 阻塞埋点与 CPU 测试 → 修复后 2×2 GPU → V0 → V1 有界 GPU → 条件 T3 → 独立复算和结项**。在没有新证据前，既不按预期挑样本，也不重写结论。

# v16 形式化与同故障恢复：已验证证据和下一步

日期：2026-11-11。范围：既有冻结规格、当前 NN4f 源码和既有 8TB 故障原日志的只读审计。没有启动新形式化/神经实验，没有修改旧源码、v15 或 CURRENT。新增 `formal_source_dev` 是尚未运行的新 CPU 检查器设计。

## 1. 最值得补回的既有强证据

1. **27 个 controls 不只是“27 项通过”。** 它们把 EL、AU、SUP 的错误替代物变为可观测反例：同文字不同完整 cut、只确认输入却要求自己的预测正确、未知未来输入被祖先失配误取消、typed ASR projection 冒充完整 C/U、未同步安装、兼容 view 被 snapshot Consumer 清除、批量提交复用最终 root、旧 epoch 重授予权限、未观察物理退出便复用槽、恢复重置原输入时钟。这比单独展示状态总数更有解释力。
2. **规格已明确包含 durable-before-install 的合法不相等状态。** `source_v3/model.py:231–252` 将 sync 和 install 分开，`check:346–352` 要求 installed Canonical 是 durable prefix 的某个 cut。`test_model.py:163–170` 明确覆盖 sync 后、install 前崩溃与原 fact 重放。不能采用审稿意见例子里的“durable 最后一个 fact 恒等于 Owner installed parent”；那个式子会把真实故障注入点判为非法。
3. **Owner-after-durable 的劣化能够定位到加载阶段。** 同 repeat 的两策略 settings 字典逐字段完全相同；第一条恢复后原 C/U 都从 32,000→40,000 samples 开始，真实模型调用仅 0.582–0.632 s。17.38/17.91 s 的新认证劣化中，97.52%/98.25% 落在新 Owner 启动至 neural-ready 阶段。该阶段结束后只需 0.678–0.740 s 得到真实新认证结果。不是一分钟的 Consumer 等待，也不是大量恢复后重算。
4. **故障能耗负面结果可以按阶段归因。** 两板原始 power 独立积分严格复现原 whole-service 能耗，新增 phase 能耗使“慢在哪里、多耗在哪里”可以复核；不能用跨故障条件 64.61–108.08 s 范围遮住同条件劣化。

## 2. 形式规格的真实元数据

入口：`experiments/dsn_native_refinement_20261030/FORMAL_MODEL_RESULTS_v3.zh.md`，其结果根为 `FORMAL_RESULTS_v3/`。

| 项目 | 已验证内容 |
|---|---|
| 实验 ID | `REVTRACE_FULLSPEC_REFINEMENT_FINITE_SPEC_V3` |
| 实际执行 commit | `deb3260655e2f3312499a34597cc0be6fc15484b` |
| 完整 source manifest SHA256 | `e2ceaad9d1a6e5f4051689a71b158a75244840be3fa2ccca8829b95a7c39d497` |
| 规格语言/工具 | 手写 Python：frozen dataclass、显式 action、`deque` 广度优先状态探索；`unittest` 命名 controls |
| 待验性质 | 每个探索状态和启用边后的状态执行 `check`：原 C/U fact 链、原 job/epoch/incarnation、不变冻结输入、durable prefix、Consumer 不认证非 fact、完整连续 view 路径、物理 lease、原输入义务与时钟 |
| 抽象 | 一个 bit 表示完整不透明反馈状态的等/不等；同 frontier 可有同文字但不同状态；原 C/U 是允许两种选择的非确定关系 |
| 正常 profile | 2 frontier，至多 3 issued，深度 12，无故障：6,231 states / 11,142 edges / 2,144 depth cutoffs / 16 terminal states |
| 故障 profile | 1 frontier，至多 2 issued，深度 12，至多 1 次 Owner/worker/session fence：14,074 / 25,799 / 2,828 cutoffs / 2,196 terminal states |
| cap 与约简 | 150,000 cap 未触及；没有显式对称约简；`seen` 对完整状态去重，不等于对称约简 |
| 覆盖比例 | 声明深度内显式生成的可达状态/边全部检查；深度边界有未展开后继，未知无限可达总数，不能给“全状态覆盖率” |
| controls | 27/27，0 skip；包含合法进展和非法变体，既不是 27 个独立故障类，也不是自然发生率 |
| 环境 | Python 3.12.13，Linux 5.15，CPU，0 model/GPU calls；完整 config/env/hash/raw/summary/gate 在 RUN_RECORD 中 |
| 不覆盖 | 未机械抽取 Python/CUDA/OS；非无限活性/全局单调性证明；非任意 GPU 数值一致性；非 Byzantine/掉电保证 |

原 raw：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_refinement_20261030/formal_model_v3`。与当前运行源码 NN4f `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47` 分开记录，不能把形式规格 commit 当神经实现 commit。

## 3. 相位正确的归纳不变量

令 `D=(d1,…,dn)` 是已成功同步的原 fact 序列；`P0` 为 genesis，`Pi=di.end`。令 `k` 是 Owner 已安装位置，`c` 为幸存 Consumer 已认证的位置。

* **I_fact**：每个 `di.start=P(i−1)`；`di` 引用一个已实际拥有、完整执行原 C/U 的原 job，其完整冻结输入等于 `di.start`，其输出等于 `di.end`；原 job、epoch、incarnation、selected IDs 不重命名；每个 job 至多贡献一个 distinct fact。
* **I_install**：`0≤k≤n` 且 Owner installed cut=`Pk`。可写 Owner 的 idle/prepared 相位有 `k=n`；成功 sync、尚未 install 时有 `k=n−1`，pending transaction 精确绑定 `dn`。崩溃态允许此 gap 继续存在；恢复从同一个 D 重建 `Pn`，不新建 C/U 边。
* **I_consume**：Consumer 认证只能推进 D 的无缺口前缀；私有 view 只改变 provisional channel。恢复重放已存在 fact 不改变 D；已消费 fact 的重复 delivery 是 stuttering。
* **I_EL**：每个未终结 job 保留完整冻结输入。只有同一 frontier 的真实完整 cut 能把输入从 UNKNOWN 变为 CONFIRMED/REFUTED；CONFIRMED 只建立输入资格，不认可该 job 的预测后继。未来 UNKNOWN job 不因为更早祖先失配自动变为 REFUTED。
* **I_SUP**：每次合法 Consumer 应用独立检查整条支持路径；compatible-and-ahead 应用保留此前完整 ahead view；必要的不兼容撤销及明确授权撤权分别记录。该性质不是全会话文字单调。
* **I_lease/input**：逻辑取消不等于物理退出；只有匹配原物理 lease 的完整 terminal 或已确认退出才能复用槽。幸存接受输入账本与原时钟跨恢复保持。

归纳必须按下表的动作建立这些前提，然后才能把“删除 stuttering 动作后的 D 是原程序允许执行”作为推论。不能把 I_fact 全部当成黑盒前提再称机制证明完成。

## 4. 动作 → 不变量 → 实际守卫 → 已有反例矩阵

表内 `M`=`dsn_native_refinement_20261030/source_v3/model.py`；`T`=同目录 `test_model.py`；`N`=`dsn_native_resilience_20261030/source_v2/`。行号来自本次现有文件。

| 协议动作 | 必须保持/建立的归纳项 | NN4f 实际守卫 | 既有规格控制或实际实现控制 |
|---|---|---|---|
| Dispatch | I_fact 不变；建立不可变完整输入和独占物理身份 | `N/fullspec_policy.py:105–117` 限定原 full worker、cadence/target、完整依赖链、唯一 job；`resilience_policy.py:134–148` 验 Owner serial/incarnation；`resilience_inbound.py:117` 绑定物理通道 | T `owner_namespace_session_epoch_and_worker_incarnation_are_separate`；`worker_exit_must_be_observed_before_slot_reuse`；实际 `test_resilience_policy.py:187,194,251` |
| ASR/Receive projection | 不扩展 D；预测不授予 AU/认证 | `N/fullspec_policy.py:119–121` 经 Stage 原完整 binding；`candidate_bridge.py:28–36` 标明 typed projection、原 C/U 未完成；Consumer private 路径不改 processed | T `original_projection_cannot_be_promoted_as_C_U`、`provisional_application_never_advances_certification` |
| EL / cancel | 仅真实同 F 完整 witness 可 refute；不以文本/祖先代替 | `N/fullspec_policy.py:29–46,48–72`；`abandon:188` 需要原 issued proof；`stage_worker.py:47–58` 在 C-entry 校验 hint、同步清 cache 后才给 abandoned terminal | T `same_frontier_mismatch_refutes_not_text_equality`、`unknown_input_is_not_a_C_entry_cancel_proof`、`unknown_future_input_survives_ancestor_loss_then_converges` |
| Receive complete / buffer | 完整结果与实际 start/end/C/IDs/通道绑定；未知 parent 只 buffer；D 不变 | `N/fullspec_policy.py:151–167` 完整 input/output/path checks；`resilience_policy.py:221` 经 inbound 分类；`_replace_conditional_node:123–137` 不重签后继 | T `future_complete_result_buffers_until_parent`、`complete_before_confirmation_and_confirmation_before_complete`、`confirmed_input_does_not_require_own_prediction_correct`、`incompatible_completed_full_is_discarded` |
| AU / Prepare | 独占串行接纳；job input=真实 installed parent；前一 durable 已安装 | `N/resilience_policy.py:150–179` append 前确认 input/epoch，回调返回再确认 parent 未变；`fullspec_policy.py:139–149,169–183` 串行按实际父状态 pop | T `mutation_unconfirmed_prepare_has_counterexample`、`old_epoch_complete_cannot_be_reauthorized_under_identical_root`；M:223–229 |
| Durable append/sync | D 只扩展一个原 full-call edge；Owner 可暂落后一个 fact | `N/resilience_storage.py:71–81` 完整原调用和前一 store root；`:82–97` 完整写循环、flush/fsync 成功才发 receipt；异常冻结；`resilience_owner.py:34–41` 可在 durable 后 install 前故障 | T `illegal_install_before_sync_has_counterexample`；实际 `test_resilience_storage.py:87,103,114,159,244` 分别测同步顺序、fsync失败、partial write、旧parent、合法checksum非法语义 |
| Owner install / publish | 仅安装该已同步 fact；每次 commit 自己的 view/root 快照 | `N/resilience_policy.py:181–185` hook 后才 `super._commit`；`fullspec_policy.py:139–149` 逐安装 snapshot；`resilience_owner.py:43–50` 发布原 receipt | T `each_queued_commit_has_its_own_root_snapshot`、`final_root_alias_mutation_breaks_first_commit_snapshot`；M:243–252 |
| Actual Consumer apply | I_consume+I_SUP；单独验 WAL receipt、无缺口 prefix、完整 view 路径 | `N/resilience_consumer.py:26–42` 验原 durable frame/parent/sequence/role后install；`:48–76` 验Owner namespace、FIFO与整路径；`feedback_contract.py/Reconciler.install` 保留compatible suffix | T `compatible_application_keeps_whole_ahead_view`、`snapshot_consumer_mutation_is_observably_false`、`incompatible_application_withdraws_needed_view`；实际 `test_resilience_consumer.py:62,71,158,167,188,205` |
| Worker fail/observe exit/restart | 完整已拥有 buffer 可留原 incarnation；在途 lease 不重用 | `N/resilience_owner.py:73–83` 先实际exit/CUDA release，再封存通道完整帧，再 fence/inc++；`resilience_policy.py:274–332`；`resilience_transport.py:85–99` | T `full_buffer_remains_usable_after_worker_only_restart`、`worker_exit_must_be_observed_before_slot_reuse`；实际 `test_resilience_policy.py:263` |
| Owner Crash / Recover / replay | I_fact 不变；允许 durable-install gap；新 Owner 从原 D 重建；Consumer replay不新建神经边；输入时钟不重置 | `N/resilience_trial.py:85–101` 先死亡确认、begin_owner、scan原WAL/Consumer replay、再spawn；`resilience_storage.py:51–70` 重建 store；`resilience_owner.py:101–114` 从原 roots 初始化 coordinator | T `owner_crash_before_sync_does_not_create_a_fact`、`post_sync_preinstall_recovery_replays_old_fact_not_new_work`、`recovery_keeps_supervisor_consumer_certified_facts_and_original_clocks`、`new_legal_work_finishes_after_fail_stop_and_recovery` |
| Duplicate/stale/local reject | 不变状态、不能释放另一新任务lease，合法后继继续 | `N/resilience_inbound.py:117–209`；`resilience_consumer.py:22–25,49–61`；`resilience_policy.py:195–219` 验原fenced terminal完整绑定 | T `expected_duplicate_is_local_idempotent_rejection`；实际 `test_resilience_policy.py:137–218` 和 `test_resilience_consumer.py:103–152` |

## 5. 哪些是呈现问题，哪些确实需要新检查

**可直接使用既有证据解决：** 补规格语言/算法、原 commit、profile bounds、cap、depth-cutoff、27 named controls 的确切含义；明确 refinement 的 alphabet、原 C/U 允许关系及投影；用动作矩阵解释实现如何建立证明前提。这些不需要扩 GPU 或假造新状态计数。

**新增 CPU 检查有实质意义：** 在原有不变 transition system 的每条边显式验证“只有 Sync 扩 D；Install 只消费精确 pending fact；Crash/Recover 不新建 D/神经结果”；验证 phase-aware installed-index gap；保留“durable-tail=installed-parent”在合法 gap 上为假的正反控制。`formal_source_dev` 已复制原 model 与原 27 controls（字节不变），新增 8 个 focused controls 和 action checker；尚未冻结/运行，不能写 PASS。

**仍不能仅靠该新 checker 解决：**

* 旧规格 `recover:306–317` 明确清 provisional steps；真实 `SurvivorConsumer.begin_owner:13–15` 保留当前 view。旧报告已诚实注明这个范围差异。要把恢复后 SUP 纳入同一规格，需新恢复动作/模式和 compatible replay、incompatible replay、已消费 replay、旧 publication fence 的成对控制；不能只改 theorem 文字。现有实际 Consumer 测试已有对应正负例，下一步可以先独立执行它们并做 actual-trace 对应。
* spec `sync_record` 成功/未成功二分没有展开真实 short write / uncertain fsync / 完整 checksum corruption；这由现有实际 storage CPU controls 与故障 raw 支持，不能称规格覆盖了任意存储失败。
* 原完整 cut 的状态声明完备性、忠实 GPU 计算、操作系统/存储前提仍是显式前提；增加深度不解除它们。

## 6. 同故障点恢复成本：真实阶段结果

原 cells 共同前缀：`SC_FORMAL_SHORT28_v1_BAC009S0908W0369_`。全部在原 8TB `.../dsn_native_resilience_20261030/formal_short28_v1/cells/`。本次按每个文件 SHA/行号只读复核 supervisor、Consumer、power。新证据：`FORMAL_RECOVERY_RAW_PHASES_v1.json`、`FORMAL_RECOVERY_PHASE_ENERGY_v1.json`。

| after-durable repeat | Conservative | RevTrace | RevTrace−Conservative |
|---|---:|---:|---:|
| r0 fault→new certified (s) | 87.054169 | 104.439023 | +17.384853 (+19.97%) |
| r1 fault→new certified (s) | 83.898384 | 101.804797 | +17.906413 (+21.34%) |
| r0 Owner-start→ready (s) | 84.846765 | 101.799782 | +16.953017 |
| r1 Owner-start→ready (s) | 81.782306 | 99.374963 | +17.592658 |
| r0 ready→new certified (s) | 0.678417 | 0.740254 | +0.061837 |
| r1 ready→new certified (s) | 0.695415 | 0.699446 | +0.004031 |
| r0 whole-service GPU J | 24,200.103 | 27,171.137 | +2,971.034 (+12.28%) |
| r1 whole-service GPU J | 22,414.987 | 26,482.680 | +4,067.693 (+18.15%) |
| r0 fault→new certified GPU J | 18,605.245 | 21,176.401 | +2,571.156 |
| r1 fault→new certified GPU J | 16,828.362 | 20,808.645 | +3,980.282 |
| r0 Owner-start→ready GPU J | 17,944.895 | 20,375.094 | +2,430.199 |
| r1 Owner-start→ready GPU J | 16,227.257 | 20,039.814 | +3,812.556 |

两板能耗包含原 origin 到最终模型物理 drain 和 Consumer 应用，排除初始 cold load；包含 origin 后的故障 reload。新增积分使用原 `Power.energy` 的相同分段线性梯形算法；whole-service 与原 summary 差 <1e−6 J。这是 GPU board 能耗，不含 CPU，不是反事实算法能效。

| after-durable | 重启两 worker 原 `model_load_seconds` (s) | 原 full-load+warmup (s) |
|---|---:|---:|
| Conservative r0 | 73.494050–73.494829 | 78.574241–78.599248 |
| Conservative r1 | 69.857919–69.859117 | 75.985320–75.987888 |
| RevTrace r0 | 87.706690–87.707632 | 94.896998–94.936784 |
| RevTrace r1 | 87.050568–87.050717 | 93.209493–93.227847 |

`stage_worker.py:16` 的 load timer 围住整个 `CandidateBridge` constructor；原 `stage_worker.py:19,25` 单列 full-load+warmup 和 neural warmup。当前日志不能把 constructor 拆成 ASR权重读取、GPU搬运、Ultravox、Llama backbone、adapter、动态import，不能把观察到的长load直接命名为磁盘/页缓存/锁/温度原因。

恢复两个 ready 的发送差仅 r0 25.260/39.560 ms、r1 0.389/3.037 ms；第二个发送→Owner ready 3.036–4.844 ms。关闭第二worker屏障在这四条历史执行上没有十几秒的可观测剩余空间。Owner 接收每个 ready 的精确时间未落日志，不能把 sent 当 received。

恢复前原 Owner exit/CUDA release 真正确认；新 ready 内 PID 与各自 e1 `worker_started` 一致；新模型开始都在 ready 之后。原停顿是 after-durable-before-install-and-consume，旧 fact 在 1.356844–1.810038 s 真正重放到 Consumer；它不是新神经结果。Consumer 原先已可见 frontier 在四格观测到的 deficit均为0，不能把 100s 新事实RTO写成100s旧视图全黑。

**源级因果位置：** `resilience_owner.py:101–114` 先重建 FactStore、启动两worker、验合同/genesis，直到 ready 后才在 :113 构造策略 coordinator。`stage_worker.py:16–25` 两策略采用完全相同 settings、constructor 与 warmup。故现有证据将主要劣化定位到**共同加载路径的运行差异**，尚不能归因为 RevTrace 选择算法。反向控制也保留：before-durable r1 RevTrace load55.46–55.58 s、new64.612 s，Conservative load73.65–73.66 s、new86.425 s；加载差异可以反转，不能用 after-durable 两次下结论普遍较慢。

## 7. 可修与尚未证明可修的具体机会

| 优先级 | 机会/假设 | 现在证据与限制 | 下一次区分性检查 / repair gate |
|---|---|---|---|
| P0 | 给原加载路径补 phase telemetry，并重跑相同故障点配对 | 已定位约70–88s constructor，尚无内部时钟；`NativeBridge.__init__:118–143` 包含原ASR、corrector interface、AutoModel、Peft | 同输入、同source/weights/FP32/warmup/原clock/fault target，随机交叉次序且交换GPU；每臂至少重复2次；逐phase墙钟、CPU、/proc io、RSS、GPU memory，原consumer/fact trace checker；保持全部reload成本 |
| P0 | 动作级归纳 checker | 现有27控件够强但正文未展示建立前提；合法sync/install gap容易误写 | 先冻结 `formal_source_dev` 并在8TB CPU运行；旧profile计数须不变，35控件（原27+新8）无skip，额外每边义务通过；不冒充新神经/无限证明 |
| P1 | 真正重复加载/权重转换能否消除 | 源码只明确同一worker依次构造ASR、Ultravox/Llama与adapter；Ultravox嵌套backbone是原权重结构所需，不能见两次from_pretrained就称bug | 计数每个file-open/权重tensor创建/搬运/转换、核对参数存储；若同worker重复初始化同权重确实占主导，做共享substrate修复给两臂；完整参数逐tensor equality、同输入重复运行+合法原loader oracle后重跑故障配对 |
| P1 | 减少两个进程同时读相同资产的争用 | 两worker timer近乎同步；这兼容共有资源争用，但也兼容正常并行，不证明锁/IO根因 | 先profile原并发load，再同合同限流/错峰load控制；不可省warmup或replica身份校验；只有真实E2E RTO/能耗净改善、无selected-trace/视图回退才保留 |
| P1 | 合同不变的准备后快照/预转换资产 | reload分钟级留下强E2E机会；目前无测量证明 | 若phase显示可避免的格式转换/CPU state dict materialization，可预生成审计资产放8TB；记录官方源tensor→新资产映射和hash；不得改模型/精度/原C/U，给Conservative同能力 |
| P2 | Consumer/WAL重放重复扫描 | Supervisor scan→Consumer逐fact verify→Owner FactStore再scan的代码确有重复读取；这里恢复WAL很小，death→ownerstart仅0.077–0.117s | 仅在长流profile发现累计fact数导致明显RTO增长再索引/增量验证；保持完整checksum/sequence/parent校验，不能从此四格声称能省17s |
| P2 | 单worker优先或去除ready屏障 | 已观测两ready几乎同时发；预计本组≤40ms可见空间，不支持作为主repair | 不删合同/genesis校验；仅在新增profile测到真实大straggler再做独立反事实配对。不要据旧窗口直接宣布全局NO-GO |
| P2 | 恢复后重算/等待优化 | first call32k→40k仅0.582–0.632s，ready后总≤0.740s，不能解释17s | 保留完整post-ready dispatch/model/commit/consume时序；若新运行观察到不同bottleneck再修，现阶段不先改取消/调度语义 |

这里没有证据支持一个具体的加载优化已经成功，也没有足够证据冻结整个恢复方向的 NO-GO。**可执行选择是先做窄加载诊断和同故障配对；定位到真实重复/转换/争用后再改共同实现，并做同输入、重复和合法原实现 oracle 控制。** 旧两次失败和能耗劣化原样保留在新结果中。

## 8. 本次新增文件与后续交接

* `review/FORMAL_RECOVERY_RAW_PHASES_v1.json`：8格原时间、原summary、原SHA/物理行、ready/warmup与真实新Consumer fact。
* `review/FORMAL_RECOVERY_PHASE_ENERGY_v1.json`：8格独立phase积分、PID/死亡证明、原模型首两调用；小型原custom model源码摘录+SHA。
* `review/FORMAL_RECOVERY_readonly.py`、`FORMAL_RECOVERY_energy_readonly.py`：可审计只读读取方法，无signal/模型调用/远端写入。
* `formal_source_dev/{model.py,test_model.py}`：原冻结规格与27 controls字节复制；`invariants.py,test_invariants.py,run_checks.py,README.md` 是新CPU审计候选，尚未运行。

原控制全名及行号、raw路径/hash均在JSON/本报告对应条目。新实验必须由root另建独立冻结 commit/manifest、config、environment、RUN_RECORD及8TB raw/summary/gate；本次只读复核结果不能替代它。

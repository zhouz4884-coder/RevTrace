# 完整条件结果跨 producer 退出与 Owner 恢复屏障：源码设计及只读核查

日期：2026-10-31。状态：**设计完成；未启动新模型/GPU；未实施 fixture；未修改 CURRENT、NN 冻结源码或正文。**

## 1. 裁决与执行身份

完整 buffer 跨退出的正负控可行。推荐一个独立、冻结的 timing fixture，包装现有 Worker 发送器，在真实 ASR 回包后暂停父调用，在真实完整回包后暂停 child；外部 controller 对 child 做真实 SIGKILL，等待原 Owner 的 OS/CUDA/channel/fence 路径完成，随后释放父调用。NN4f 的接收、资格、持久化、安装和实际 Consumer 路径都继续运行，不新增结果接受路径。

单靠外部看到 ASR 日志后 SIGSTOP 父 Worker 可做机会性尝试，但不能保证正确交错；父调用可能已越过 C 的入口甚至完成，不能把这种竞争失败改标成 buffer 见证。不要暂停 Owner。

本次核对的 NN checkout 为 `experiments/dsn_native_resilience_20261030/source_v2`：HEAD `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，`git status --porcelain` 为空。冻结 manifest SHA256 为 `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457`，59 文件。上述 manifest 身份取自 `RUNTIME_FREEZE_v2.json` 和 `FINAL_EXECUTION_AUDIT_GATE_v1.json`；本设计没有替代运行前的完整字节 manifest/source/environment gate。

fixture 是有效执行的一部分。未来 RUN_RECORD 同时记录 fixture 实际 commit/manifest、导入 NN4f commit/manifest、环境 hash、配置 hash、原始结果路径、汇总和 gate 路径。不能因 NN59 文件未改，就把含有 timing 包装的运行称为“自然执行的纯 NN4f”。fixture 必须单独 clean、提交、冻结并验证；不能沿用 NN4f commit 为新增代码背书。模型侧 `source_commit=NN4f` 的输入合同不应被新 fixture commit 冒充，二者在执行身份中显式分列。

## 2. 已有证据与目标对象

原 36 格的 3976 次 Canonical 安装中，3622 从当前 Canonical 出发，354 为在飞条件调用提升后安装。实际 completed-full-buffer 安装为 0，跨 dead/fenced producer 的 buffer 安装消费为 0。已有 4 个 ASR whole-view 跨 producer death 驻留直到合法修订；它们不是完整 C/U buffer 的安装见证。见 `EXISTING36_EVENT_WITNESS_DECISION_v1.zh.md` 及原 census。

本轮目标对象是已经完成原 full C/U、被 Owner 正常接收并放入 `completed_full` 的 immutable item。必须仍然使用它原来的 `job_id`、`birth_canonical_sha`、`dispatch_epoch`、`worker_incarnation`、完整 start、target end、完整 end 和 record。重算得到相同文本、重放一个旧 ASR 视图、或者 kill 后替换 Worker 的新 job 均不能计入。

源码支持点（相对 `source_v2`，当前 1-based 行）：

| 路径 | 含义 |
|---|---|
| `fullspec_policy.py:151-164` | 完整回包先做真实 start/end/record/role 检查；start 尚未成为当前 Canonical 才放入 `completed_full` |
| `fullspec_policy.py:29-46` | 当前完整输入相等可用；相同 frontier 的实际 Canonical 不相等才构成拒绝证据；祖先失配不能替代当前输入判定 |
| `fullspec_policy.py:166-178` | buffer 在父输入实际确认后安装；出现实际不等 witness 则 discarded，不能安装 |
| `resilience_policy.py:worker_lost` | 只退休该 incarnation 的 live jobs；保留已接收 `completed_full` 与已有 view，不改 Canonical/输入义务 |
| `resilience_owner.py:73-83` | 原 `lose` 路径依次真实退出、CUDA release、closed-channel drain、`worker_lost`/fence、incarnation 递增与替换启动 |
| `resilience_owner.py:43-49` + `stage_policy.py:106-108` | 原 buffer outcome 发出正常 view；step 的 `actual_original_full_conditional_closed_node`/`actual_full_C_U_completed=True` 可从外部观察 |
| `resilience_policy.py:_commit` | 完整父输入确认、durable-before-install、原 job 和完整 record 的绑定仍是必需条件 |
| `test_resilience_policy.py:test_worker_loss_retains_already_accepted_complete_future` | 仅 CPU 路径支持；不能代替本轮真实 NN/OS/CUDA 见证 |

## 3. 预定正负边界：使用旧原始日志选择，不改神经输出

已只读检查旧正常格 `SC_FORMAL_SHORT28_v1_BAC009S0908W0369_none_fullcall_r0` 的 `owner_e0/worker_results.jsonl`。真实原始文件为：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_resilience_20261030/formal_short28_v1/cells/SC_FORMAL_SHORT28_v1_BAC009S0908W0369_none_fullcall_r0/owner_e0/worker_results.jsonl`

字节数 `1042486`，SHA256 `d37ed1b1e16f48d5c612c4acfad8bb6a4d0aa0126c6e0a6c9e4c0406f98bf5e8`。逐 JSONL 行匹配原 job 的 ASR projection end 与 complete end 全状态，未调用模型、未写远端文件。

| 用途 | 父 start→end（frames） | child start→end | 旧父 job/ASR 行/complete 行 | 旧实际结果 |
|---|---|---|---|---|
| 正控候选 | 16000→24000 | 24000→32000 | `e0-j000000003` / 6 / 7 | projection 与实际 complete end 完全相等；selected_correction 存在 |
| 负控候选 | 24000→32000 | 32000→40000 | `e0-j000000004` / 8 / 9 | projection 与实际 complete end 不相等；selected_correction 存在 |

正控候选完整状态 SHA：projection/actual 均为 `264652c8230cb0f5fe873170975b170f3a82de7f003dc3baac853a9f86ba3169`。负控候选 projection 为 `d25f4c1b78a3dbf8603e3184a5073ac5ef464f17e536d47ce8445ba33ad53e17`，actual 为 `951d27d89c334b8d15689a4ecb0f033a589feaee6a7a2352054cd6ef8b778827`。

这是提前定位受控注入点，不是自然率估计。新运行仍必须检查自己的完整 `FeedbackCut.same()` 字节相等，不以旧 SHA 替代当前事实。若新运行目标未出现、正控输入未确认或负控没有实际失配，记 `TARGET_NOT_EXERCISED`/对应负结果；不改输出来满足预期，也不在同一冻结配置中悄悄换边界。job serial、slot/PID 不作跨运行固定假设；按 source、start/end、epoch 预定逻辑位置，运行时绑定实际 job 与物理身份。

## 4. 最小 fixture：只在外部传输边界控制时序

### 4.1 保持原 NN59 文件字节不变的装配办法

新 fixture 模块提供可 pickle 的 `timed_owner_entry` 和 `timed_worker_entry`。Owner wrapper 导入冻结的 `resilience_transport`，将它的 Worker entry target 绑定为 fixture 模块中可导入的 wrapper，再调用原 `resilience_owner.owner_main`。原 `start_worker` 仍创建/拥有 Pipes、Process、FramedReaders、PID/start_ticks。Worker wrapper 用原 `stage_worker.worker_main`、原 CommandReceiver/HintReceiver，唯一替换是 `FramedSender` 的子类或透明包装器。

包装器对**原事件**先调用原 `FramedSender.put(event)`，完成原 header+body 发送，随后仅在预先冻结的一次目标匹配时阻塞当前 Worker 的回调返回：

1. 父：匹配真实 `asr_early`、source 和父 target，在发送结束后写 fixture-ready marker，等待 controller 的 release。
2. child：匹配真实 `completed`、source 和 child start/end，在发送结束后写 fixture-ready marker，等待真实 kill；超时应异常结束并留下失败 gate，不能静默放行。
3. 其他消息完全走原发送器；不得改变 event 内容、投影、record、C/U、错误提示、runtime_identity 或输入资格。原 `fault.kind=none`，不用旧 30 秒后必报错的 `worker_after_asr` pause 冒充可恢复屏障。

门控可以使用经 spawn 正确传递的 multiprocessing Event/Pipe，或8TB盘上唯一运行目录内的原子创建 marker/release 文件。若采用文件，记录运行 nonce、experiment ID、PID/start_ticks、slot/inc、job、source、start/end、event semantic hash 和 `perf_counter`；禁止复用旧 release。配置只存可序列化的 frozen fixture 规则，不能把同步对象混进 CONFIG.json。

不需要替换 `receive_event` 或修改 Owner 接收路径：原 view publication 已经能提供 Owner 完成接收的后置见证。若包装方案因 spawn/import 语义不成立，应明确以新 fixture commit 改装 entry，不动 `candidate_bridge`、`native_bridge`、`fullspec_policy`、`resilience_policy`、storage 或 Consumer；不能靠调用私有安装方法绕过原事件循环。运行前 CPU smoke 要实际覆盖 spawn 后 wrapper 生效，不能仅验证父进程 monkeypatch 名称存在。

### 4.2 正控完整时序

1. 使用相同原始语音、双卡 FP32 模型、原 warmup、完整源/模型/环境校验；冻结 `parent_end=24000, child_end=32000`。真实 ingress 依原 cadence 继续接收；不能先人为抬 accepted frontier。
2. 父原调用产生并正常发送 ASR projection。父 sender 在 callback 返回之前进入屏障。此时原神经 C/U 未被 fixture 执行、跳过或替换；实际 Owner/Consumer/ingress 仍运行。
3. 原 Owner 正常接收该 early view，随后在真实 accepted 输入足够时正常派发 child。child 原 start 必须等于父 projection 的完整 state；child 必须在与父不同的实际 GPU 上执行原完整 full_step。
4. child 完成原 C/U 并发送真实完整结果，sender 阻塞。原 Owner 正常接收，`complete()` 返回 `buffered_full`，原 view publication 的该 job step 标成 full conditional closed node，而它的 start 仍不同于当时 Canonical。controller 等这个**接收后的原 publication**，不能把 `worker_results` 已写一行当成接收成功：原代码在 strict validation 之前写 resultslog。
5. controller 核对 child dispatch 与 Worker 启动 PID/start_ticks，发送真实 SIGKILL。父继续处于屏障，Owner 不停。按原 failure detector 走 EOF/非零 exit → `lose()`；记录原 Process join/exitcode、CUDA owner消失/对应板显存阈值、两个 reader join、old-channel drain、`worker_lost` 和 higher incarnation 启动。
6. 原 policy worker-loss audit 的 `preserved_completed_jobs` 必须含原 child UID；`retained_view_jobs` 不能代替此项。Owner 的 `worker_death_confirmed` 在 `worker_lost` 返回后发出；再核 higher-inc `worker_started`，可确定旧 incarnation 已 fence。无需等替换模型 ready。
7. controller 仅在上述原路径完成后释放父。父继续调用原 C/U。原父输出确认完整 child start，父的 durable/install/actual consume 正常进行。随后原 `pop_ready_commits()` 选中原 buffer，完整父状态 equality 检查通过，按原 WAL/store/Consumer 安装和消费。
8. 继续到全部已接收义务处理完并真实物理 drain；不以第一条见证提前截断。

必须验证的严格偏序为：

`Owner buffered receipt < kill_requested <= confirmed_exit <= CUDA_release <= sealed_channel_validation <= old_incarnation_fence < parent_gate_release <= actual_parent_confirm < child_durable/install <= actual_child_consume`。

同一 `perf_counter` 单机时钟下记录偏序；若有不同 clock domain 只能使用消息/门控因果关系，不能直接减时钟。允许持久化与 publication/Consumer 的正常不同步；不得把安装与消费合并成一个点。

child 完成回调屏障不能阻止 Owner 随后给同 slot 排队另一个 job。若出现，须完整记录并由原 worker_lost 正常退休这个**新的 live job**；旧 completed UID仍要保留。这不会取消目标见证，但不能把新 live job 的 retirement、原 child buffer 和替换 job 混为一体。需要禁止额外模型执行时，用 child 发送后屏障即可；不要阻塞 Owner 的 command send 来伪造更干净的日志。

### 4.3 负控完整时序

除预定 `parent_end=32000, child_end=40000` 外，使用同样 fixture、原接收/退出/CUDA/fence 条件。child 完整结果先被 Owner buffer，producer 真实死亡后再释放父。父实际输出在 child start.frontier 处给出不相等的完整状态；原 `_reason` 必须产生 `actual_canonical_disagrees_with_complete_start`，原 `pop_ready_commits()` 把 child 放入 discarded audit。

负控必须同时证明：原 child UID无 durable record/Canonical install/实际 certified consume；原真正父输出继续成为 Canonical；从实际 Canonical 出发的必要工作最后完成，已接收义务未丢。负控不是“没安装所以成功”：若未登记buffer、没实际kill、没经过fence、父未确认、全服务超时或Owner崩溃，则该负控没有检验目标条件。

## 5. SIGSTOP 与死亡判定风险

| 风险 | 具体原因 | 本设计处理 |
|---|---|---|
| Cskip/快速 C 的竞争 | 外部观察到 ASR 消息时，Worker 可能已经返回 sender、执行原 C/U、发出 complete。某些路径根本不发 early；一些不调用神经纠正的路径很快闭合 | 只在真实 early callback 的原发送后/返回前设屏障；正控选择旧日志中真正 selected_correction 存在的边界；新运行仍核神经记录，缺 early记未命中 |
| 暂停仍物理占卡 | SIGSTOP/Event wait 不销毁 CUDA context；已有异步核也可能继续运行，显存不释放 | 父卡始终算占用；不从停住推断 released/paid-work节省；只要求 child 的不同卡走原CUDA release gate |
| SIGSTOP 不等于 death | stopped 进程的 `is_alive()` 仍为真，Pipes未EOF，无exitcode | 父只是时序屏障；producer只有实际SIGKILL+join+exitcode+channel closure才计故障 |
| 暂停 Owner 使验证停摆 | 接收、失效检测、CUDA检查、channel封存和Canon安装都在Owner事件循环 | Owner/Consumer/ingress保持运行 |
| 停父后等“两卡全部释放” | 父还活着且占另一板，会把真实恢复条件做成不可满足 | 原 `wait_cuda_release(child_gpu,child_pid)` 只检查退出producer及其板的阈值，保持原函数不改 |
| 外部kill与PID复用 | 日志里的旧PID不能单独授权signal | controller与原 `stop_worker`均验证start_ticks；slot/inc/job在证据中完整绑定 |
| 旧内置fault pause不可释放 | 原worker_after_asr发送后sleep(30)，随后必raise | 不复用其故障标签；新fixture独立可释放hold，并记录其有效源身份 |

外部 SIGSTOP 只可作为额外诊断；若确需使用，应先用上述 callback 屏障确认安全位置，再SIGSTOP/验证`/proc`状态，最后SIGCONT并release。这样不比Event/Pipe屏障更小，也不产生额外服务结论。

## 6. 故障后下一请求的最小持续性见证

优先把正控 run 延伸为一次固定后继请求，而不是另开多会话资源算法。原 Owner 已支持多个 source/独立 reconciler；外部 supervisor 可事前声明两个独立 request/source ID：A为故障请求，B为固定后继短请求。B的 accepted值保持0，A达到EOS、全部已接收义务认证且实际Consumer完成后，按冻结条件正式接收B；随后按B的真实到达 cadence释放其frontiers。

这样只替换外部 ingress编排；原 Owner在B未完成时不会因“全部sources完成”退出。B由原initial_for/source contract的独立状态开始，继续使用同一Owner epoch/PID和存活模型Worker；故障producer的替换过程保留真实身份。原 `resilience_trial.run_trial` 的ingest会同时释放所有sources，**不能原样拿它当顺序请求harness**；需要新外部supervisor入口，但不改NN59的Owner/worker/policy/storage/Consumer。

检查A/B request identity、每个accepted obligation、不同source的根/epoch绑定、B完整EOS与实际certified consume、Owner/模型进程连续性。必须预先声明B，不按A结果选择语音。若只保持driver存活而每请求重启全部Owner/模型，只能叫“driver连续”，不达成此见证。

这是一个固定两请求的故障后继续服务见证，不能推成无界持续服务、自然长流质量、多会话公平性、或新的资源准入算法。若给B计算延迟，必须以B真实接收时钟为分母，独立记录；不能把先前全局origin或人为hold成本隐藏后再借原D2/C8主张。此次窄见证可只报告最终完整服务与安全偏序，不需要新增性能成功主张。

## 7. 独立验收与失败分类

拟定两个主cell：`SC_BUFFER_DEAD_PRODUCER_MATCH_20261031_v1`、`SC_BUFFER_DEAD_PRODUCER_MISMATCH_20261031_v1`；正控内带固定后继请求B。配置冻结匹配规则、源/模型SHA、FP32/TF32、gate超时、原服务上限、request顺序、expectation与全部结果路径。另先做CPU wiring smoke，标签明确为CPU。

独立checker只读原 raw与fixture ledger，至少输出：

1. 原事件整帧/语义指纹、注册job与完整start/end的绑定；Owner full conditional publication在kill之前存在。
2. 原 worker_death proof、CUDA release、封存通道证据、inbox fence/higher inc；每项缺标保持unknown。
3. `worker_lost.preserved_completed_jobs` 含目标UID，身份未重写；buffer job不是started_on_canonical，也不是在飞promotion。
4. 父门释放在fence之后；父实际完整cut与child start的bytes比较；正控相等、负控不等。
5. 正控原UID的事实记录、durable receipt、canonical install、真实Consumer消费与完整refinement；不以相同文本代替状态相等。
6. 负控同frontier失配proof、discard与原UID零certified安装/消费；随后真实Canonical分支继续完成。
7. A全部真实输入义务和B完整服务/进程连续性；原模型输出没有被fixture替换，所有配置/代码/环境/输入raw哈希可重查。

偏序/物理exit/fixture触发失败属于控制或实现问题，不是输入资格机制被证伪；正控父实际输入不相等属于未达到预定语义前提；出现同输入不同输出时，先做同输入/重复运行和合法原程序对照，保留有限精度/模型机制的不确定性。只有在实际前提均满足时错误安装/拒绝，才是目标安全/进展路径失败。任何失败原样保留，不靠改C/U、放松资格、变更deadline或篡改神经结果修复。

## 8. 旧 Owner 恢复的免费原日志剖分

### 8.1 已核实可得与不可得的标记

本次通过既有Windows credential helper只读8TB上的8格`supervisor.jsonl`，零模型调用、零远端写、没有发signal。普通沙箱无法访问Credential Manager，随后同一只读读取在授权隔离外执行；未读取/打印/保存密码。远端使用`python3`流式JSONL解析和SHA256，回传有界字段。

原 `owner_ready` payload包含两个Worker原`ready`事件；各有`sent_perf`、`model_load_seconds`、`full_load_warmup_seconds`。因此能取得**各Worker组装/发送ready的时间**及后续Owner总ready标记；`resilience_owner.py:103-106`在初次两Worker ready接收时没有把FramedReader `received_perf`写入ready日志，所以**Owner精确第一次/第二次接收ready时间不可得**。不能把sent改称received，也不能据此测出调度反事实收益。

Supervisor还有实际fault、Owner组进程/CUDA全释放、WAL前缀恢复、重启、总neural-ready等时间。`kill_owner_group`的原proof把无执行成员与CUDA owners全释放合并为一个标记，旧日志不能再拆成“最后一个OS进程退出”和“最后一个CUDA释放”两个准确独立点。原after-durable格有旧事实实际Consumer replay；before-durable没有新的旧事实可重放，不能填零秒。

### 8.2 原8格结果

下列cell前缀均为`SC_FORMAL_SHORT28_v1_BAC009S0908W0369_`。`first/second sent`按两个Worker的`sent_perf`数值排序，单位秒；`new certified`来自原SUMMARY中“fault后真实新模型完成并实际认证消费”字段，未用旧事实replay代替。

| cell suffix | fault→组exit/CUDA确认 | fault→first sent | fault→second sent | ready发送差 | second sent→Owner ready | fault→new certified |
|---|---:|---:|---:|---:|---:|---:|
| owner_after_durable_conservative_r0 | 1.451535 | 86.347019 | 86.372279 | 0.025260 | 0.003473 | 87.054169 |
| owner_after_durable_conservative_r1 | 1.315427 | 83.197737 | 83.198125 | 0.000389 | 0.004844 | 83.898384 |
| owner_after_durable_fullcall_r0 | 1.781949 | 103.655862 | 103.695422 | 0.039560 | 0.003347 | 104.439023 |
| owner_after_durable_fullcall_r1 | 1.653427 | 101.099278 | 101.102316 | 0.003037 | 0.003036 | 101.804797 |
| owner_before_durable_conservative_r0 | 1.710627 | 107.354403 | 107.355098 | 0.000695 | 0.013354 | 108.080530 |
| owner_before_durable_conservative_r1 | 1.706031 | 85.732867 | 85.747395 | 0.014528 | 0.005918 | 86.424749 |
| owner_before_durable_fullcall_r0 | 1.679580 | 106.352031 | 106.368573 | 0.016542 | 0.003144 | 107.090671 |
| owner_before_durable_fullcall_r1 | 1.798478 | 63.925619 | 63.930905 | 0.005285 | 0.003208 | 64.612193 |

两个ready发送相差仅0.389–39.560毫秒，第二个发送到Owner总ready约3.036–13.354毫秒。Worker自身完整load+warmup约59.182–97.697秒，和重启到ready的长等待同量级。**这些已观测格不支持把64.61–108.08秒的新认证RTO主要归因于第二个Worker落后，更不支持为本文改“单Worker优先恢复”能获得秒级收益。** 这是对既有时序的剖分；不是单Worker恢复实现的反事实测量。两Replica的contract/genesis比较也是当前启动合同的一部分，不能为了提前派发而省略它又声称故障与认证前提不变。

### 8.3 原日志绑定与行索引

原目录共同前缀：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_resilience_20261030/formal_short28_v1/cells/`

每行文件为`<prefix><cell>/supervisor.jsonl`。以下是本次完整流读取的字节SHA与1-based物理行：

| cell suffix | bytes | SHA256 | fault / exit / prefix-ready / Owner restart / e1 worker-starts / e1 Owner ready |
|---|---:|---|---|
| owner_after_durable_conservative_r0 | 809831 | `373960b4bd1c89bd09b102357cbdc24b8f110391b76db2bc12c7d476918be958` | 17 / 18 / 20 / 22 / 25,26 / 27 |
| owner_after_durable_conservative_r1 | 809880 | `3081f3a95a0e953b8295235ef7f74367f0ad7d37db36c202eb1bdca58dae39af` | 17 / 18 / 20 / 22 / 25,26 / 27 |
| owner_after_durable_fullcall_r0 | 861323 | `54c3bd041b8a7cd6da2b67b8dc3326814111e636a68436512ce2b10413ca0af8` | 17 / 18 / 20 / 22 / 25,26 / 27 |
| owner_after_durable_fullcall_r1 | 861430 | `302790cd01709af1774e4038ecaed6c3899097e9138a8646c753a8f3e4e519d7` | 17 / 18 / 20 / 22 / 25,26 / 27 |
| owner_before_durable_conservative_r0 | 844353 | `3fca307b1ba5b62b3e23bc5915e672468e4da121e54c17b1d3056639a7f6ceb1` | 17 / 18 / 19 / 21 / 24,25 / 26 |
| owner_before_durable_conservative_r1 | 844403 | `701eb3ae87861d1351b1c247d396bde0e7e0e883dcf59e0268e09cb8bb236e77` | 17 / 18 / 19 / 21 / 24,25 / 26 |
| owner_before_durable_fullcall_r0 | 895900 | `be1dab3c3982a63f7e9809c479946bc168cb37b195d7c9d36364f3c1d825d484` | 17 / 18 / 19 / 21 / 24,25 / 26 |
| owner_before_durable_fullcall_r1 | 895910 | `d00361cea06ae989b3134c3407e128a15995f2a643567b2171bf2e639c0cb356` | 17 / 18 / 19 / 21 / 24,25 / 26 |

after-durable的实际旧事实replay在各自第19行；before-durable第19行是prefix-ready，`newly_applied_facts=0`。更细的磁盘扫描CPU耗时、单Workerready接收延迟、包传输延迟、OS与CUDA释放分别独立时刻均没有旧精确标记，不补造。

## 9. 工时与本轮边界

推荐实现路径约2–4小时（fixture entry/spawn/门控、独立checker、CPU wiring）；两主cell及固定后继请求、结果收集与独立审计另约1–3小时，受模型加载/真实边界是否复现影响。此为估计，不是任务已完成或队列已开始。

源码级预研结论：**GO，实施一个外部受控timing fixture补目标正负交错；NO-GO，把旧ready屏障当作当前一分钟恢复的主要瓶颈而开展Owner恢复改造。** 新实验结果出来前，完整buffer跨death的实机计数仍然是0；旧长流质量NO-GO、旧版本身份和自然率边界全部保留。

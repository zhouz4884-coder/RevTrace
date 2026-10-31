# bdfa / 4f 配对正常态与常驻独立请求：源码裁决及事前实验设计

日期：2026-10-31。本文只读核对了已冻结实现、配置、环境与有界结果；没有启动 GPU、修改 CURRENT、修改任一冻结源码，也没有把设计写成实验结果。

## 1. 当前裁决

1. 历史 bdfa 四新说话人 Full-call 的 8/8，与 4f 上 S0908 的 1/2，**不是同条件的版本对照，不能宣布已确认回归**。另一方面，不能把旧 8/8 直接赋给最终 4f 实现。
2. 两个版本的神经模型、原 ASR/C/U、完整输入资格判断和基础状态表示有很强的源码一致性证据；执行编排、持久化、传输、Consumer 和遥测确实不同。这些不同足以形成应当测量的真实端到端开销。
3. 在同一对 GPU 上保持模型/Owner 驻留、按预注册次序释放有限个独立 sid，是现有 Owner 的 accepted frontier 门可以支持的编排。**4f 的原 trial 不支持 arrival offset，原 metrics 也硬编码全局 origin**，因此不能仅填一个配置字段便宣称已经支持常驻请求。需要新冻结的外层 ingress / clock harness，核心资格和提交协议不变。
4. 有限预注册 sid 的见证不证明任意动态请求注册、无界在线服务或总内存常数；也不能覆盖旧无 VAD、无中途 EOS/reset 长流的负结果。

## 2. 源码身份与逐项差异

2026-10-31 本地只读检查：两棵树 Git status 均空、HEAD 均为完整目标 commit、跟踪文件集合与 manifest 完全相等、每个文件长度和 SHA256 完全匹配。

| 项 | bdfa 历史正常态 | 4f 最终可靠性实现 | 配对处理 |
|---|---|---|---|
| 执行 commit | `bdfa3b1307d267a5a4caf6484e1ad465c39a592e` | `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47` | 各自独立干净 checkout；不把 archive commit 当执行 commit |
| source | `dsn_streamcorrect_stage_handoff_20261029/source_v3` | `dsn_native_resilience_20261030/source_v2` | 不修改两树 |
| manifest | `packages/SOURCE_v3_LOCAL_PREFLIGHT.json` | `packages/SOURCE_v2.json` | 各自完整校验 |
| manifest SHA256 | `5524cac28e1ae9f85a4c7c9b6cca0938b40411c8da346adbba4605998b0edc40` | `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457` | 38 / 59 个完整跟踪文件 |
| 神经路径 | `CandidateBridge -> NativeBridge` | 同文件逐字节相同 | 不换模型、C/U、量化或精度 |
| 状态及资格 | `feedback_contract.py`, `fullspec_policy.py`, `stage_policy.py`, `stage_packet.py` | 同文件逐字节相同；新增 Resilient 包装器 | 比较完整 cut、selected C、token IDs；仅静态 source marker 映射 |
| 其它共同文件 | 35 个共同 Python 文件中，仅 `stage_worker.py` 不同 | 其余 34 个共同 Python 文件逐字节相同 | `stage_service.py` 在 4f 内仍与 bdfa 相同，但不是 4f 故障 trial 的入口 |
| 主入口 | `stage_service.py` | `resilience_trial.py -> resilience_owner.py` | 各跑自己真正的部署路径；不能只让 4f 改跑旧 entry 然后声称最终实现无回归 |
| Owner / workers | 同 Owner 内 Queue；轮换 worker / source 顺序 | Supervisor + 独立 Owner；有 incarnation 的校验 Pipe；固定 worker 后 sid 顺序 | 单 sid 正常态能避免多会话顺序混杂；保留各自真实路径 |
| Canonical 持久化 | `canonical_wal.jsonl` 同步写状态 | 校验链 FactStore 同步完整 parent/state/C/U/job 后安装 | 这是测量对象；不得关闭权威持久化换取好数字 |
| Consumer | 后台线程 StageConsumer；观察日志 flush | Supervisor 同步 SurvivorConsumer；逐次验证 durable receipt；观察日志 fsync；ACK/pin | 完整视图与真实消费时钟语义相同，故障/重放/完整性机制不同，开销不能假设相同 |
| 日志 | 普通日志与权威 WAL 区分 | ingress/publications/supervisor/Consumer 多处同步日志，另有 Owner audit | 首轮保留真实设置；实际确认回归后按时间戳定位 |
| Worker 变更 | 原 invalidation hint 队列 | 逐 job 清空旧 hint、只收本 job hint；记录 allocator；可选 NativeStateObserver | 原神经计算与输出函数未改；遥测/取消管理有变化 |
| 遥测 | 无 `record_state_telemetry` | 正式格为 `True` | 主对照保留 4f 真正正式设置；单独停遥测仅能作归因诊断 |
| Python/env | Python 3.12.13；torch 2.9.1；transformers 4.57.6；numpy 2.2.6；peft 0.18.0；soundfile 0.14.0；torchaudio 2.9.1 | 同解释器路径、同包版本、同模型资产清单 | 发车前活体验证；历史记录不是当前 GPU 健康证明 |
| 环境记录 | 基础环境 SHA `96a0679d34741743de1a1b6d784c0e518cbdcf7b76a23cae3d95c12d20a6fae8` | v2 SHA `bd09660f15b61bc173ddab57cea2d03fccc9ebd8eb97ddb485d6132cae90733d`，明确绑定 allocator | 新配对同时显式冻结同 allocator；不把环境 SHA 不同误当包版本不同 |
| allocator | 旧 config 没有显式 allocator，旧 READY 无该字段，不能反推当时进程环境 | `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`，alias `PYTORCH_ALLOC_CONF` 必须不存在 | 两版本都用 4f 已有明确条件；历史默认/继承状态仍记 unknown |
| precision / 随机性 | corrector FP32；TF32 / autocast 关闭；seed 1701 | 相同 worker 设置 | READY 验实参 dtype、环境，不能只看 config |
| 模型及 warmup | 原 author commit `bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3`；固定 S0764 Canon1.5s→2.0s 神经 C；丢弃 warm 输出、恢复 genesis | 相同 backend/warmup 对象 | 模型资产清单 SHA `8dde505d1dd6f5e9cc7b85722466e1b9725bc915a4d5f8d7bda82cc4c7c117fd` |
| preload | 旧独立确认 model_sources 为 warmup+全部四新来源，共 5 | 相同 S0908 正式格为 warmup+当前 source，共 2 | 新配对两边统一每格 warmup+当前 source 2；这是新冻结条件，不冒充旧配置重跑 |
| deadlines / cadence | 500 ms / 8000 samples；D=2、C=8；EOS 全计 | 相同 | max-ahead=32000；同音频 bytes / frames / reference；不过滤 EOS |
| service cap | 180 s | 240 s | 新配对双方统一 240 s；超时/不完整不从分母删去 |
| 能量终点 | service origin 到 Consumer drain；worker shutdown 在主 ended 时间之后 | service origin 到最终物理 drain + Consumer 应用 | 主要 D/C 同定义；跨版本能量须另作共同终点重算，否则只比较版本内两策略，不混成跨版本总能耗优势 |

同 S0908 r0 的两个实际 config 递归比较：`backend`、`warmup`、`sources` 完全相同；settings 差异仅 source_commit、model_sources 长度、4f 新增 record_state_telemetry。外层有新故障、参考、环境绑定及 service cap，不应遗漏。

精确参照文件：

- `experiments/dsn_streamcorrect_independent_20261029/service_v1_configs/SC_FINAL_INDEPENDENT_V1_two_full_spec_early_BAC009S0908W0369_r0.json`
- `experiments/dsn_native_resilience_20261030/formal_short28_v1_configs/SC_FORMAL_SHORT28_v1_BAC009S0908W0369_none_fullcall_r0.json`
- `experiments/dsn_native_resilience_20261030/FROZEN_ENVIRONMENT_v2.json`

### 现有数字的正确分母

bdfa 旧四新说话人的 Full-call D99 为 0.837–1.663 s，8/8 原 D2/C8 整场通过。4f 的 S0908 两次为 D99=1.798 / 2.053 s，对应 1/2；同版本 conservative 为 4.069 / 4.170 s。后者提示 Full-call 仍有较大正常态机会，但不能由此估出纯版本效应。

当前 28 格内另有两个无故障 Full-call：S0905 r0 通过，开发 S0764 r0 不通过。因此，所有这些正式无故障 Full-call 合计为 2/4；顾问 1/2 指 S0908 重复子集，既不能漏记另两格，也不能把这个混合来源的 2/4 叫作四新说话人确认。

## 3. 最小有区分力的 GPU 配对计划

### 冻结全队列，再做阻断 smoke

推荐总队列 32 格：**历史已冻结的四新来源 × 两版本 × 两策略 × 两次 fresh-process 重复**。四来源固定为 S0905/W0246、S0908/W0369、S0913/W0313、S0916/W0463；来自既有 metadata 规则，不重新按表现挑选。

策略映射：bdfa `two_full_early` ↔ 4f `conservative`；bdfa `two_full_spec_early` ↔ 4f `fullcall`。双方两个完整 FP32 replica，两个物理 GPU，同一完整 warmup，同一 immutable source、逐次 offer、max-ahead=32000。两版本分别保留自己的真实 Owner/Consumer/WAL 路径。

先跑预定 S0908 的 8 格（2版本×2策略×2重复），用于阻断语义错误、启动异常和明显端到端退化。全部 32 格、顺序、停止分支须在看到新结果前冻结。S0908 先跑是因为它是已有两实现的共同诊断来源，不因为本次结果好。没有阻断问题则执行其余 24 格。**8 格 smoke 不是四来源结论**。若终止，则原队列未运行格列为未运行，不用少数成功格替代全部队列。

每个 source/repeat 是一个四格 block；固定 seed `2026103101` 打乱 block 顺序，S0908 两 block 固定置前作为 smoke。预写 r0 四格顺序并在 r1 反转；primary_gpu r0=0、r1=1。无并行模型运行、重 CPU/IO；每格冷进程启动，暖模型后才开始原 service clock。不得在相同长驻模型中跑一版本、重载另一版本却称 fresh pair。

每格必须有 experiment ID、config hash、actual source full commit + complete manifest hash、environment hash、READY dtype/allocator、指定 8TB raw path、summary/gate path。外层 launcher 若新增，必须单独有 commit/manifest；不得声称外层改动属于旧 bdfa/4f。root 的 CURRENT 选择与 no-argument preflight 由 root 串行执行，不能由并行 agent 交错改指针。

### 验证与预写决策

最先检验语义：完整 source、父 cut、子 cut、每一 selected C、token IDs、EOS 步数、真实 Consumer、全部原输入义务、失败/超时保留。允许的跨版本静态映射仅 `contract.stage_execution.source_commit`，须同时绑定实际两 commit；不删除其余 contract、context、state 或 token 字段。旧 offline original references 是合法语义 oracle，不能充作实时结果。

主要结果按每格报告：原 all-offered D99/C99、完整整场 D2/C8 是否通过、双期限 audio credit/总 audio、EOS/nonEOS misses、真实最后新结果/Consumer 完成时间。8 对 Full-call 与 8 对 conservative 均给出原始配对差，不把 32 次当独立说话人数。

**分支 A：没有可重复的版本退化。** 报告本次共同条件下两实现各自原 D2/C8 与完整 paired table。只有最终版本实际得到 8/8，才写“最终冻结实现上四新来源八次均通过”。若 bdfa 和 4f 都偶有边界失败，则如实缩小历史“8/8”的稳定性主张；不能用“不显著”宣称性能等价。保留旧不同条件结果的独立身份。

**分支 B：实际配对提示退化。** 将以下记为定位触发器而非已证明因果：两重复同方向的 D99/C99 增加且 final 新增原 gate miss；或 Full-call 总双期限 credit 下降。立即用同一来源、同一完整输入 cut 的 repeated-run + legal-original-reference 检查，区分：

1. C/U/token/state 变了：语义/数值/模型机制问题，不能先当日志慢。
2. 状态/输出一致，service latency 增加：测 Owner 收取、worker restore/export、IPC、durable sync、Consumer 应用/ACK 的实际关键路径；不能把并行 worker 的时间相加冒充 wall time。
3. bdfa 与 4f 同时漂移：先查硬件/环境/到达/allocator/缓存/竞争，不归罪版本。

如果确有可定位的非权威诊断开销，允许在**新源码、新 commit、新 manifest**中做一次局部修复；对同来源完整重跑，保留原负结果。不得关 FactStore 的 durable-before-install、accepted obligations 的持久化、资格校验、原 C/U、或只删不利来源。

**强端到端机会门。** 修复动机必须来自相同资源下 Final Full-call 对 Final conservative 的真实 D/C、双期限 credit 或完整服务时间机会，并保留全部语义 gate。现有 S0908 约 1.8–2.1 vs 4.1 s D99 说明值得做这次小范围归因；它不能替代新 paired 结果。若局部修复仍不能继承正常态核心收益，或只能靠削弱义务/精度/持久化才能过门，则冻结最终实现的 evidenced NO-GO / 有界结论，停止新增机制与阈值搜索。没有事前功效分析的少量重复不输出统计等价或普遍非劣结论。

## 4. 常驻、原带 EOS 的独立请求：可以做的最小范围

### 为什么是编排可行，而不是现成支持

`resilience_owner.owner_main` 初始化全部 sid 的独立 genesis、FactStore roots 与 Consumer state。调度只会派发 `end <= accepted[sid]` 的 job，所有完整输入 cut 带 source_sha；每个 `full_step` 都经 `restore_cut` 重建完整原 state、清干净 KV/attention/beam，再执行原调用。最后不足 500ms 的请求尾仍通过 `is_last=end==len(audio)` 走真实 EOS。给未来 sid 保持 accepted=0，并不需要改变资格判定、C/U 或提交协议。

但 `resilience_trial.ingest()` 现将全部 source 按同一 origin 并发到达；`resilience_metrics.analyze_trial()` 校验 `offer == origin + F/16000`，`cell_metrics/content_endpoints` 也据此算等待。因此，新请求 offset 不是一个已被消费的字段。直接外设 offset 而沿用旧 aggregate 会把“下一请求到达前的空闲”误计为等待，或通过重置全局 clock 隐藏债务。

原作者 `refresh_segment(complete=True)` 会初始化 tokens/context/language 与 FTL；现有受控应用的原始 genus 由 `NativeBridge.initial_for()` 给出。最小 harness 使用**各个独立请求既有的完整 genesis**，请求间不拼接 context、不按识别好坏 reset。`first_token_generated/latency` 属现有候选桥已识别的遥测字段；不拿 FTL 作为原 D/C 结果，不新增神经状态改动来迎合该辅助指标。

### 最小 harness 合同

- 只做一个预注册、有限的 4-source 序列，仍使用同四来源音频，不复制/拼接波形、不读文本决定端点。独立 source 的文件 EOS 是明确声明的请求结束事件，不称作在线 VAD。
- 全部 sid 在启动前已登记；两个模型和 Owner 连续驻留直到最后请求完成。固定次序由 metadata ID / 事前 seed 决定；两策略完全相同。不能动态增删 Owner sources，也不能改 Canonical/epoch 协议。
- 请求 i 的释放必须是预先冻结的 schedule，或明确冻结的 closed-loop 客户端合同。最小推荐 **closed-loop**：上一请求的 EOS durable fact 已被真实 Consumer 消费后，下一请求立刻开始，记录真实 request origin；这是单 outstanding 客户端，不称固定到达率/并发容量。文件/顺序选择不依赖结果。
- future sid accepted=0；当前 request 仍按自己的 `request_origin + F/16000` 逐 8000 samples 放行，EOS 按实际 frames；记录 ingress fsync 完成时间与原 offer，沿用 accepted 共享值。所有原 offered 包括 EOS 计分，迟到保留。
- 更新范围只允许新外层 Supervisor ingress 编排、每请求 clock 账本、独立结果分析适配器。`resilience_owner.py`、`resilience_policy.py`、`resilience_inbound.py`、`resilience_consumer.py`、`resilience_storage.py`、`stage_worker.py`、bridge、原 C/U 的 bytes 保持 4f。新外层必须完整冻结，不能改已冻结文件。若把核心原样复制入包含新 harness 的独立源码树，则整个新树必须有新 commit/manifest，actual source marker 使用新 commit；结果身份为“新 harness + 字节相同的 4f 核心”，不能冒充原 4f commit 原生已有的运行格。
- 每个 request 完成仍是本 sid frontier==frames 且 Consumer certified_frontier==frames；模型不退出、不重新 warmup、不借旧请求 worker 的未收尾结果作为新 sid 的输入。独立 sid、source hash 和 genesis 是隔离边界；这仅验证已注册有限请求，不宣称生产环境 session 创建/销毁/无界 GC。
- 每请求单独调用原 endpoint 算法，使用该请求实际 origin/该 sid 的全部原 Consumer rows；只在派生副本平移时间用于复用算法，原日志与绝对 observed/offer 不改。独立审计 `offer == request_origin + F/16000`。整序列另外报告 wall、全程双板能量、请求切换间隔、PID/model-load 次数、owner/history/RSS/CUDA 指标；不能把加载摊销说成单请求冷启动改善。

最小实机 smoke 为 2 格：Final conservative / Final Full-call 各一个四请求 resident 序列，仍是新实验合同；不足以给一般吞吐/高负载结论。若须独立重复则预冻结第二对；不能看到单对坏后才改变来源或 inter-request gap。

### resident 的事前硬门

1. 源码 diff 证明所有核心协议/原模型文件逐字节不变；仅新 ingress 与 clock 适配。如果必须修改 Owner/session lifecycle /资格语义才能继续，本文窗口 resident NO-GO。
2. CPU 编排负控：下一 sid 尚未 admitted 时 accepted=0；任一旧 epoch/source 不能伪造新 request 输入；EOS 始终在分母；下一请求 origin 账本单调且因果上晚于上一真实 EOS 消费。CPU gate 是 harness 验证，不是实机性能。
3. 实机每请求 C/U/full state/IDs 与同来源原合法参考一致；同 sid 的全部原义务 eventually processed；模型 load=每 slot 一次、PID 跨无故障请求保持；没有偷偷 fresh process/reset 掩盖前一请求。
4. 第一对 smoke 必须同时显示可用服务和仍有短链 Full-call 的实质端到端机会。否则不扩增 resident；保留失败，论文最多在限制中陈述未获得 resident 证据。
5. 后续故障—下一请求见证沿用同一合同、固定预注册故障位点；须显示故障后 **新请求的第一实际 full C/U / 新 Consumer 结果**，旧事实 replay 时间不代替新服务恢复。若故障在当前请求造成 backlog，closed-loop 下一请求因此延后是该合同的观测结果，不能写成 fixed-arrival SLO 已被保护。

## 5. 当前结果和未完成工作

本稿完成了只读源码、配置、环境身份和有界结果核对，给出了可复查的 paired/resident 计划。没有新 GPU 性能数字、没有新 source freeze、没有 resident smoke、没有新可靠性 gate。真正发车须由 root 执行干净源/完整 manifest/no-arg preflight、环境与 GPU 活验、8TB 原始路径和事前 RUN_RECORD，并由独立分析核对结果后才更新正文/GitHub。

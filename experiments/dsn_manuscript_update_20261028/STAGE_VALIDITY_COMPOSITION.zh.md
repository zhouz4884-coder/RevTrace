# Protected ASR 阶段交接的条件性授权组合

状态：本地源码推导备忘录；不是 GPU 结果或服务收益报告。2026-10-29 读取的独立开发源为 `experiments/dsn_streamcorrect_stage_handoff_20261029/source_v1`，实际 clean HEAD 为 `c7e403b4313ed1283dfea2af043116643e01a0f7`。源码随后变化时须重新核对。本备忘录未修改 runtime、论文或远端文件。

后续实测补充：c7 神经门因裁剪 class 编译 oracle 的 co_code 误拒绝而失败，失败保留。完整原 module 编译 oracle 的窄修复位于新 `99e83a466fee7f1d16830b640cc99e0040d2f147`，严格源码/方法检查未放宽；该版本实际 native CPU 75/75 无 skip。四来源神经门现已全 69 PASS：65 个实际 packet C/U 与完整反馈、两条 identity 投影均等价，4 个原 early-return 保留，13 个预测终点不同而当前 packet 仍有效。同输入门 gate SHA `41221280007d94581a640ec329bf5634ccb6012efbc44ab60fca302c51c6849d`。另由独立 `64ba03e` CPU 重计确认全部 69 原 full 调用与旧 v8 起点、终点、完整 C、IDs/text 相同，唯一允许投影是新增 `contract.stage_execution`；raw hash 0/69 直接相同。两层证据都没有在线 serving cell。下文条件推导与“当时尚无新 stage service”的源码观察保留其原时间范围；不能把未来服务的授权外层据此视为已验证。

## 1. 主张与问题边界

**把真实运行、受到明确保护的 ASR 前段，与当前 Root 下原样执行的可信纠错及反馈尾部组合，可以构成一个允许的完整反馈转移；许可依据是完整输入、阶段来源和尾部依赖完整，而不是预测终点碰巧等于未来 Canon。**

这个组合有两个不同产物：阶段 packet 是尚未执行真实 C/U 的 open 中间结果；独立 identity 投影只是用于临时显示的完整反馈状态预测。二者均不能单凭类型名称、校验和或与当前 Root 相等而获得 certified 权限。真正的 C/U 完成、闭合状态检查及 owner 的顺序安装共同完成授权。

这里的“允许”指符合预先声明的 protected composed execution 合同。它不等于“同一输入在任意 GPU、调度和浮点执行中必定产生完全相同的 from-scratch 结果”。也不能用旧核心协议的 1154 状态搜索来声称本阶段运行时已经全机检查。

## 2. 分解实际原生调用

将作者原来的调用表示为：

`I=(r,x,f,last,lambda) -> A -> (B,M,ell) -> C -> z -> U -> q`。

- `r` 是调用前的完整、已清理反馈 cut；`x` 是本次新接收的 float32 音频；`f/last` 是目标 frontier 与原调用终止标志。
- `lambda` 包含固定作者程序、实际 checkpoint/tokenizer/processor、ASR 配置、精度和阶段执行 source 等合同身份。
- `A` 是真实原 `infer` 到 C 调用边界的执行。`B` 是完整、有序、四行的 `current_tokens`，包括原前缀，不是第一候选的字符串。`M` 是 A 结束后的持续状态，包括已经 trim 的 context、buffer/tokens、alignment cursor 等。`ell` 是 C/U 仍会读取的 caller locals。
- `C` 是原 `_run_SpeechLM_error_corrector`：使用实际音频、全部候选、原前缀、固定提示构造和真实 learned selector，返回原始选择对象 `z`。
- `U` 是原 `infer` 从 `use_error_corrector=False` 至 return 的尾部中，C 之后的 retokenize、选择/原 fallback、append 以及 `_clean_cache`/decoder reset。`native_tail` 机械抽取整个 C/U suffix，保留 `@torch.no_grad()`，没有手写另一套 U。

不能只传 B。原 A 会执行 `trim_context()`、可能改变 `last_attend_frame`、token beam 布局和音频缓冲；即使 C 恰好选择相同文字，U 必须接在实际 M 上。反过来，**当前 packet 不依赖 private identity U 预测出的 q**：它是在真实 C 选择前捕获的 `(B,M,ell)`。

## 3. 条件命题

设当前 Authority owner 的规范根为 `R`，本次准备执行的调用输入为 `I_R`；已有 packet `p`。若以下条件同时成立，则 `C/U(restore(p), I_R)` 是 `I_R` 下一个允许的 protected composed transition。输出通过真实 C/U 完成并按原 owner 顺序安装后，可以成为该 Root 的下一 Canon。

1. **输入绑定。** `p` 的输入 key 与当前重新生成的 `key(I_R)` 完全相等。key 包含完整起点 cut 的所有状态、immutable source 身份、本次 added-audio bytes、target frontier、`is_last` 和 runtime identity。仅 transcript、frontier、版本号或预测根 hash 相等均不替代这条。
2. **真实、受保护的生产。** p 的 B/M/ell 确实是声明角色 `protected_asr_stage` 在这个输入上执行固定 A 的结果。保护范围覆盖 A、packet capture、序列化及授权通道；包不能来自任意不可信 private computation。接收方绑定真实 worker、已派发 job、source 和其出生输入，不靠 payload 自报角色建立信任。
3. **依赖完整。** packet 保留 C/U 会读取的全部语义数据，恢复后的配置、context/tokenizer roundtrip、输入音频与 buffer 检查通过；未携带的量对该固定 C/U 的读集确实没有影响。
4. **C/U 保持原样。** Authority 注入当前固定的真实 C 模型/processor；原 infer、选中的 C 方法和 clean 方法身份通过；C 输入不被预测选择替换；原 C 返回对象、retokenize、None/empty/fallback 和 reset 路径保留。
5. **顺序与权限。** owner 在消费和安装时仍满足当前 Root/任务授权关系，完成输出不能跨越已改变的输入默默安装。只有 C/U 正常结束、完整闭合 cut 通过、Canon 日志/安装完成之后才授予 certified 权限；失败、过期或没有完成的 packet 不获得该权限。

简短推导：条件 1–2 给出当前允许输入上的真实 A 前段；条件 3 恢复后缀所需的语义状态；条件 4 把同一程序的合法后缀接回；条件 5 保证该允许执行被装到其授权的根上。串接点处程序计数位置和所有后续依赖保持，所以得到合法组合转移。这里不需要推出“另一 GPU 重新运行 A 时也会得到完全同一个 B”。后者是独立的神经数值等价检查目标，不能作为无条件定理。

## 4. 条件到代码字段的对应

| 条件 | 实际字段/检查 | 解释 |
|---|---|---|
| 完整起点与输入 | `stage_packet.input_key` 的 `complete_start_cut`, `source_sha256`, `target_frontier`, `is_last`, `added_audio_float32_sha256`, `runtime_identity` | 比较 canonical JSON 全 key。起点 cut 自含 buffer hashes、tokens、context、cursor、language、初始 tokens、contract、frontier、transcript。 |
| 运行身份 | `CandidateBridge.runtime_identity` 的 execution `source_commit`, `author_sha256`, `contract`, `asr_config`；`contract.stage_execution` 的 ASR/C dtype 与 source | 冻结 plan 中 contract 带模型/处理器等 asset inventory。字段绑定须配合启动前实际资源检查；仅写入 hash 标签不等于证明执行使用了该权重。 |
| open 类型 | `CandidatePacket.kind`, `open_state=True`, `closed_cut=False` | 明确不是已闭合的 FeedbackCut，更不是已认证反馈。 |
| B 与 caller live-ins | `current_tokens`、`token_len_before_decoding`、`input_segments`、`fire_detected`、`is_last`、完整 generation 各 key、`corrector_type` | 四 beam int64 全矩阵；prefix length 与 generation 对应，不能拿 top1 文本替代。 |
| M | `ENGINE_FIELDS` 的 `segments`, `tokens`, `last_attend_frame`, `detected_language`, `initial_tokens`, `initial_token_length`, `sot_index`, `decoder_type`, warmup/FTL 字段，加 `context.text/prefix_token_ids/token_ids` | 传的是 post-ASR 状态，而非消费进程上一次遗留状态。FTL clocks 是遥测，不参与反馈 cut 身份。 |
| 静态依赖/恢复 | `restore_open` 检查当前 `cfg_value` 全等、context token roundtrip、buffer bytes 与 captured C audio 相同 | tokenizer、model device、原方法及实际 C 权重由受保护运行时提供，不从 packet 反序列化任意对象。 |
| C/U 身份 | `compile_original_tail` 固定 SHA 与 Git blob；`run_tail` 检查 infer/C/clean 原方法 code 与类 descriptor，SpeechLM cached 对象绑定 Authority runtime | 作者 SHA `9f016f71...`，Git blob `02a2202a...`，机械 suffix 原行 1053–1138。 |
| 不注入选择 | packet 与两个 tail 入口拒绝已有 `generation.error_corrector` | 真正 C 选择之后的原对象、retokenized IDs 与原 generation 引用关系保留。 |
| 物理清理/闭合 | 原 `_clean_cache` 清 KV/attention，并 `token_decoder.reset()`；`export_cut`/`native_mutable_state` 检查 cleaned caches、beam survivors、language/config | open packet 格式验证不能代替这里的闭合检查。 |
| ready-only | `ReadyCache.take(key,dispatch_perf)` 仅选 receipt 不晚于 dispatch 的完整 packet | 这是服务策略：不等待未来包。它与组合本身的计算合法性是两层条件。 |

`payload_sha256`、`key_sha256` 证明传输字节的一致和绑定，不是数字签名或执行正确性证明。`producer_role='protected_asr_stage'` 是格式内的角色声明；其真实性来自预先保护的 worker/通道和派发关系。

## 5. 预测终点不同、旧出生身份与后继链

设 p 出生于旧 Canon generation `g0` 的一个 private/protected job，后来 owner 安装新根 R。**只要重新构造的完整调用 key 仍与 p 的真实出生输入完全相同，原 job 的 p 可以继续服务当前这一次 C/U。** admission 应新增“在 R 下检查并消费”的记录；原 producer worker/job ID、birth/start cut、生产与接收时间保持，不把 p 改写成 R 之后新生成的计算。

实际旧 `CandidatePacket` 只携带输入和 payload；`job_id/source_id/worker` 在 `stage_worker.emit` 产生的外层 event。当前 `ReadyCache` 保存 packet 与 receipt，**因此完整 service 必须在外层留存并检查出生和派发关联**。本次读到的 c7e403b 有 worker 与神经门，还没有新的在线 stage service；不能把这项外层协议说成已经在本 source 的新服务中验证。

private identity 投影得到 `q_hat`，真实 C/U 得到 `q`，二者可以不同。p 为当前 C/U 的合法输入，不要求 `q_hat=q`。但是预测后继 `p2` 的出生输入若包含 `q_hat`，在真实 q 之后必须另比较其完整 key：只有输入依赖相等才能留存/使用；当前 p 获准不自动给整个后继链通行权。

独立 `run_identity_tail` 限定 exact `native_bridge.identity_prediction`、inert sentinel 与无 processor，执行相同 U 产生可显示预测。`run_tail` 仍拒绝 identity 方法代替 Authority C。它们可以具有相同 FeedbackCut 数据结构，但其授权 provenance 和 certified 权限不同。

## 6. 为什么可省 KV，以及 Logits 的精确边界

packet 不携带 A 的 decoder KV、attention 张量和 beam-survivor 内部容器。理由仅限于固定作者后缀：真实 C 从音频、B、prefix、cfg/tokenizer 与独立 C 模型读取；原 U 不再调用 ASR decoder，也不读取这些张量数值。恢复前清掉无关资源，U 之后仍必须执行作者原 reset，随后只允许在原生 cleaned-cache 边界导出闭合 cut。

因此这是**后缀读集和强制 reset 支持的阶段边界**，不是“KV 不重要”或“可以用空 KV 替换任意在途推理”。一旦 C/U 改为读取 logits、重评分 ASR、继续 decoder 或复用 attention，此省略条件立即失效，须重新设计 packet。

Logits 只对 generation 的指定诊断节点作 type/shape/dtype 显式 elision；其原 key 与剩余 generation 数据保留，BeamTokens/Tokens 数值保留。机械 AST 的 generation payload 下标读取只有 `error_corrector`，原 C 不接收 generation；因此 Logits 数值不决定选文、回填或闭合反馈。**这不声称 full debug log 或 generation payload 的所有数值相等。** 真正需要相等的是 C 选择对象、返回 IDs、完整闭合反馈状态和用于消费的文本。刷新遥测 clocks 同样不能被拿来声称原 FTL 数值日志相等；服务延迟仍须由真实运行时钟测量。

## 7. 最小反例与当前 CPU 控件

| 去掉的条件 | 最小反例 | 已有有意义控件与剩余边界 |
|---|---|---|
| 完整输入一致 | 显示文本相同但起点 cursor/context 或追加音频不同，仍套用旧 B/M | `test_foreign_full_input_cannot_be_restored`；配置、context roundtrip、buffer/C audio 分别有拒绝测试。当前 foreign-key 控件改 target；不是对所有单字段扰动的穷举。 |
| 完整 B 与 prefix | 只传第一 beam，C 本来应选的第二候选丢失；或 prefix length 改变，回填片段边界错 | packet beam/prefix 拒绝；`test_original_C_receives_all_beams_and_selects_original_response` 确认四个有序候选和实际音频到原 C。四 beam 重新排序仍可能是格式合法数据，真实性由 protected producer 保证。 |
| post-ASR M | 恢复 B 却遗留接收方旧 context/last_attend_frame，眼前文本一致而下一调用输入不同 | 完整 packet roundtrip 与闭合-state 神经 oracle 会约束此项；目前没有逐个 M 字段的 mutation-fault CPU 全覆盖，不应写成已有穷举证明。 |
| 原 C 与原 U | 包自带 `error_corrector` 或将 identity prediction 当成 learned C；或直接 append 当前 ASR IDs，跳过原 retokenize/empty/None fallback | packet/tail 注入拒绝；Authority exact identity 拒绝；原 C 返回对象身份、retokenize、empty vs None、terminal/nonfinal fallback、prefix 与 original generation 保留等 CPU 控件。 |
| 原清理/闭合 | 返回后仍有旧 KV 或 survivor，后继恢复得到隐含旧状态 | 替换 clean 被拒绝；open engine `export_cut` 先失败，原 identity tail cleanup/reset 后 actual cut export 成功；beam reset/cache alias 控件。 |
| projection 隔离 | 临时 identity tail append/reset 了真正 A 的 tokens/context/cache，真实 C/U 接到已改状态 | `test_projection_does_not_mutate_live_asr_or_generation`，以及 packet/open projection 共享原 suffix 的控件。该 CPU isolation 测试使用替身 tail；真实原 suffix 的隔离仍需神经全状态对照。 |
| 真实角色与 job 绑定 | 不可信进程用正确 JSON 格式重算 SHA，自称 protected role | SHA/格式不会防住这个反例。它直接说明执行完整性/可信通道是命题前提；在线 service 需验证 worker/job/birth，另立外层 fault 控件。 |
| ready-only receipt | 包在 dispatch 后才到，却回填为已 ready 的服务命中 | `test_ready_only_never_waits_for_future_receipt`；完整运行还须记录真实 receipt/dispatch 与命中来源。 |
| 后继链独立检查 | 当前 p 完全合法，但下一 p2 基于错误 `q_hat`，仍沿用到不同的真实 q | `test_prediction_end_is_not_an_admission_input` 仅证明当前 p 不要求预测终点；**不能**代替未来 p2 完整起点拒绝控件。 |

本 memo 未新运行这些测试。此前 helper 开发期实际 30/30 CPU PASS 是有界开发控制；正式 CPU gate 须在完整 clean source/manifest 下独立记录，且不代替神经/在线门。

## 8. 新神经等价 oracle 的最少覆盖

`run_neural_equivalence.py` 已规划全部四个原来源、69 个原调用点；应保留全部 early-return 点，不只挑有 packet 的点。其每个有 packet 的输入需要以下对照同时成立：

1. protected A 的 packet 与独立 Authority 原 full infer 在真实 C 入口捕获的 packet，完整语义签名一致；明确排除 declared FTL clocks 与 Logits 数值，不能只比 top1 或 hash 布尔。
2. protected A 上隔离执行 identity suffix 的完整反馈投影，等于实际原 `NativeBridge(role=private)` full call 的完整输出节点和 IDs。
3. packet 经序列化、跨进程/设备恢复再做 identity projection，也等于这个实际 private full 节点；不是仅比较 packet 与它自己投影。
4. 原 Authority full 调用与消费恢复 packet 的真实 C/U：完整 C 选择对象、返回 IDs、完整 closed cut 全等。至少一次同输入重复消费，且 C 的 None/空结果和原 early-return 路径保留。
5. 如实际存在 `q_hat != q`，记录这类输入的数量和对应的 C/U 成功等价，不删掉它们。这才实证支持“当前 packet 合法不依赖预测终点相同”。若样本没有这类点，只报告未观察到，不能制造正例。
6. worker 环境记录实际 ASR/C 参数 dtype、autocast、TF32、固定权重/tokenizer 身份；原 C 确实执行，不把 placeholder 或 warmup 当主结果。完整 raw/来源/manifest/配置/门与失败保留。

即使以上神经门通过，所得结论仍是冻结实际输入上的同输入等价控制，尚无在线 serving credit。在线服务还要展示不等待命中、真实 Root 安装/Consumer 路径、完整 offered 分母、最终质量、能耗，以及强两完整副本基线。组合合法性和有用的端到端服务机会须各自成立。

## 9. 当前实质缺口与可直接执行的收口

当前 memo 的主命题在明确 protected-execution 前提下成立；不是要求再做一种复杂的输出认证器。最实质的工程收口是 **新 stage service 的外层授权记录**：保存原 producer/job/birth；核对实际通道与派发；在 dispatch 当下取已接收完整 packet；完成时重新确认 owner Root/顺序，再 WAL/install，Consumer 才能得到 certified 更新。旧 `native_service.py` 的完整 private-step 协调不是这个新阶段 packet 的实装证据。

已直接向 SC 说明上述 job/birth 保留和 role-label 边界，不修改其 ownership 文件。建议在其新的 service CPU 控件里加入三项小而有区分力的反例：正确 key 的错误 worker/job 包；当前 p 合法而其 p2 输入依赖不同；C/U 结束前 owner Root 改变时禁止安装。它们补的是本次新授权边界，不能由 packet 编解码测试或旧 1154 状态计数替代。

若神经门的 C/IDs/closed-state、语义 packet 或两条 identity 投影任一项失败，应保留失败并先分辨捕获/恢复缺字段、AST 调用语义、不同设备数值机制；不通过改 key、去掉 M 字段或只比较文本来过门。本文未预先断言神经门已经通过，也未预设服务收益。

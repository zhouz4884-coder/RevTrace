# 最终 4f 内容证据映射：直接复用与最小缺项

审计日期：2026-10-31。此文件保留首次写作审计的reuse/missing判断，并链接随后获得授权、已经完成的CPU缺项补算。首次审计只读本地有界包；后续正式补算只读8TB原raw。两阶段均没有运行新神经模型，没有把大raw复制到本地；CURRENT由Root统一选择和恢复。

**最新完成状态：** Root随后授权的唯一CPU缺项补算已用实际分析source `6eb6639478a87e6be971e23282bd2f31789f242f` 正式完成，20 trial /32 request-instance、330输入前后SHA守恒、15/15 Linux控制通过、新NN0。以下前半部分保留首次只读审计时的reuse/missing判断；目前缺项已闭合，正式数值、continuity分母与合同见 `FINAL4F_CONTENT_RECOUNT_REPORT.zh.md` 和 `CONTENT_CPU_V4_RESULTS/complete20/SUMMARY.json`。matched支持信用22.5→51.0秒守恒；resident新得24.0→50.2590625秒；continuity为matched无compatible机会、resident Full-call唯一非空机会1/1保留，观察区间0.816859620秒，不能当作物理可用率或避免的宕机。

## 决策

1. **reuse-existing：最终 4f matched16 的实际文字新增/撤回，以及 actual-first-G 同前沿全文事后支持。** 16 个 cell 的 SUMMARY 已经有结果；只需引用并加总已有字段，不需要重做这些分析。
2. **missing-smallCPUrecount：最终 4f matched16 的 compatible-view 持续可用性，以及 resident4/16 请求的文字与 first-G 内容指标。** 对应 raw 字节清单列出了需要的 Consumer、完整 durable fact、publication、dispatch、原回执和请求时钟。现成输出没有这些结果，应只做一次冻结的只读 CPU 补算；本次仅设计，不启动。
3. F 的旧 actual36 已有 **90/90 compatible-ahead 保存、1118 次必要不兼容撤回** 的完整状态/实际 Consumer 重放证据。它可支持同一机制在其声明轨迹上的正确性，但不能充当 E 的 matched16 或 resident4 的持续可用性测量，也不能把事件计数当作时间积分。

## 最终 matched16 可立即用于正文的数值

范围为 `PAIRED32_V2_RESULTS` 中 `version=final` 的 16 次运行：四条既有声学来源 × 两次重复 × 两臂。每臂 8 运行、136 个 offered 前沿、66.33975 秒 offered 音频；重复不是额外独立来源。原运行是完整 FP32 任务，原 500ms/EOS、D2/C8 和所有 offered 均保留。

| 已完成 SUMMARY 字段的加总 | Conservative 8 | Full-call 8 | 含义 |
| --- | ---: | ---: | --- |
| 原双期限前沿信用 / s | 30.0 | 65.821625 | 前沿音频权重，不是新增文字或文字正确率 |
| 实际 introduced code-point occurrences | 180 | 180 | 每次 LCP 后新增的 Unicode code-point 出现次数，重复文字可重复计数 |
| 实际 retracted code-point occurrences | 14 | 14 | 被后续实际 Consumer 更新撤去的出现次数 |
| 最后实际同源观察仍可见的 occurrences | 166 | 166 | 在该观察时刻右删失，不延伸到假定 UI 关闭时刻 |
| first-G 全文事后支持的原信用 / s | 22.5 | 51.0 | 该次首次满足 F 的实际显示行，整段文字与其实际 G 的选定 Canonical 全文相等 |
| first-G 全文事后失配的原信用 / s | 7.5 | 14.821625 | 同一整段比较失配，保留负结果 |
| first-G 全文事后未知的原信用 / s | 0 | 0 | 缺少相应 G 的选定文本时必须记 unknown；本批为零 |
| 全部 offered 前沿的 supported / mismatching | 106 / 30 | 104 / 32 | 分母各 136，未按是否及时筛选 |

raw 与 whitespace-stripped 两种文字处理的上述数值完全相同。逐 cell 数值及摘要 SHA 在 `content_evidence_analysis/COMPLETED_METADATA_CONTENT_INDEX.json`，该整理文件 SHA256 为 `f417c042d2de7ca3697fbd5d3c37aac9046b2b64b60976caedb89bed7ad6209d`。

因此，可写 **“最终实现将及时且事后全文受支持的前沿信用从 22.5 增至 51.0 秒；实际引入与撤回的字符出现次数相同。”** 不能写成字符量增加、临时文字人工正确率提高、所有显示都得到在线认证，或“51 秒连续正确文本”。全部前沿的全文支持计数没有提高；信用增长体现受支持进展的及时性。原整场期限通过仍为 0/8 对 6/8。

## 指标的准确端点和代码来源

### 实际文字

直接字段为 `SUMMARY.content.raw` 和 `.whitespace_stripped` 下的 `introduced_code_point_occurrences`、`LCP_erased_code_point_occurrences`、`retracted_occurrence_code_points`、`still_visible_occurrence_code_points`、`closed_occurrence_code_point_seconds` 等。输入是每条实际 `consumer.jsonl` 的 `observed`、`source_id`、`text`、`visible_frontier`、`certified_frontier`。使用 LCP 版本化出现次数，没有字符到音频或 token 的对齐。

实现为执行 source `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47` 的 `content_endpoints.py::analyze_cell`；该文件 SHA256 为 `07d16f211cbc4320b3df109049083285863d0ae709d8ac008c75eb78a2776b52`。最终 source 的 SUMMARY 直接包含该函数结果；未要求另有名为 CONTENT.json 的 sidecar。早期 bdfa cell 才另有 CONTENT/CONTENT_EVENTS/CONTENT_FRONTIERS/CONTENT_SPANS。

### actual-first-G 全文事后支持

`content_endpoints.py` 对每个原 offered 前沿 F 找第一条 `observed >= original_offer(F)` 且 `visible_frontier >= F` 的实际同源 Consumer 行；这条行自己的 `visible_frontier` 是 **G**。`resilience_metrics.py::posterior_support` 按 `(source_id, G)` 读取完整 durable Canonical 的 `next_state.transcript`，比较这一行的**整段** `text`，而不是只比较 F、最终输出、历史是否相同或低 CER。

直接字段为 `SUMMARY.posterior_whole_text_support.{raw,whitespace_stripped}.original_credit_{supported,mismatching,unknown}_seconds` 及 `all_offered_frontier_counts`。信用只对原 `original_dual_credit=true` 的 F 按原音频权重分桶；三个桶之和必须严格守恒到原信用。全部 offered 的状态计数单列。比较是事后选中轨迹上的全文相等，既不意味着 G 当时已获在线认证，也不意味着人工语义正确。

实现是同一 4f 的 `resilience_metrics.py`，文件 SHA256 为 `1e3f7fbf50d4f621d51700f44ef4fb80cc335e3439e6e43e190aca9275cf121e`。不能用“原任务保持/最终状态相同”替代此临时全文检查。本次正因为 SUMMARY 已保存逐次临时检查，才准许直接复用。

### compatible-view 持续可用性

这与 posterior text equality 是不同问题。需要在实际 Canonical application 前重建完整 private dependency chain，在同一边界比较**完整 cut**，识别 compatible 且 ahead 的更新，再核实际 Consumer 是否保留该依赖后缀和原可见成果；仅 `text` 相同或 `visible_frontier` 未倒退不足以证明 causal support。

已有可复用判据为 `dsn_native_refinement_20261030/trace_source_v2/refinement_trace.py` 的完整实际 Consumer replay：执行分析 commit `c4dde9ea9c7abf80fae084bc2293e193262c71e6`，manifest `packages/TRACE_SOURCE_v2.json` SHA256 `0741878971dcdfad577624945ff3bb249860225f1281cf6d833814829f0a3948`。它的 `counts.compatible_ahead_applications`、`compatible_ahead_preserved` 和 `incompatible_ahead_withdrawals` 是事件级正确性结果。现成 E 结果没有这些事件级分母及可见时间段；F 的 90/90 也没有给 E 的 wall-clock 连续可用性。

## resident4/16 请求的缺项

四 trial 每个包含四独立 EOS 请求，实际 NN source 同为 4f，controller 为 `a13fa0a335529dc188f7e738877a3acd027ce4a7`。`SUMMARY`/`cells/*/SUMMARY` 仅有 `primary`、`per_request`、energy/history、完整 reference 与 request clock 审计，没有 `content` 或 `posterior_whole_text_support`。RAW_INDEX 全部路径中也没有 CONTENT/support/availability 导出。

其现成 request 合同是 `closed_loop_single_outstanding_independent_EOS_v1`：前一请求实际 Consumer certified EOS 后才准入下一请求；每 trial 模型只加载一次，PID 跨请求保留。原期限结果为 Conservative 0/8、Full-call 7/8 请求通过。这不能表述为在线 VAD、开放到达容量、单条无 reset 长录音或物理服务连续可达。

补算必须逐 `source_id` 使用 `REQUEST_ORIGINS.json[sid]`；不能把 trial ORIGIN 当作后续请求时钟。`request_ledger.jsonl`、`ingress.jsonl` 与已保存 per_request endpoint 是时钟守恒检查点。可对每个 sid 单独调用原 `analyze_cell`，并把相应 durable facts 提交给原 `posterior_support`；四 source 共用一个 origin 会产生错误数字。

## provenance、哈希与审计覆盖

以下均为本次重新核对的**本地有界包**。所有 BOUNDED_INDEX 记录的本地文件长度和 SHA256 均通过；matched16 的 SUMMARY 还同时匹配 RAW_INDEX 与 campaign `summary_sha256`。没有重新读取/哈希全部远端 raw，因此 raw 完整性在本次只依据既有完整字节清单和既有执行/独立审计，实际补算前还必须再按清单逐输入核验。

| 证据 | SHA256 / 身份 |
| --- | --- |
| paired RAW_INDEX；880 文件、128297473 bytes | `31c3ed2d1a5f74065dbcb7252607592382e343f89e32404feacc7f1c85527f36` |
| paired BOUNDED_INDEX | `71b94514609a68b8dc5aebd310883fad462609cc2b7d6d8c06e0be280b5bdda3` |
| paired campaign SUMMARY | `6788a843fc45844952380cd16e733df95a294249411db57a25823b3e8d25ddf1` |
| resident RAW_INDEX；111 文件、88986159 bytes | `2e92562ac180f9565af280c4c17815902dbbbea8db43ced2ad598c7b72c77f59` |
| resident BOUNDED_INDEX | `5908089ec3cd0daaf1f9dd5b4a56ee224b0a7a917175a07ca0e109e9ba22a262` |
| resident campaign SUMMARY | `e8c22bae201af9889196f90392ab68cfe18a2ec49e44dde890e2365fc1043bc8` |
| 4f complete source manifest | `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457` |
| paired/resident controller source manifest | `8cadffbfe9ffcc1eb3efdf5e2702e7afbc2ec932158c12dd197d6f0bdc334934` |

paired campaign frozen config/environment SHA 分别为 `8aeb2aae2d080236191333a6101d9869978d10e1de9389acb15c430bc065781d` / `5901b460c3d278fb25d01c739fae2a7430962b6c48b37746ae23f3461f15cd5c`；resident 为 `623ef4d65ac7fbb2b701a2e7b6cde616ca143b6a6f784b2d85b8ea338c93fd9c` / `568920da732c072d56e104f4c527665985274ed5d3d01319b711e865e653d8a9`。每 cell 原 RUN_RECORD 保留自己的实际 execution commit、config/env hash、raw/summary/gate 路径；不能拿 controller 或 GitHub archive commit 代替 NN execution commit。

raw 固定在指定 8TB：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_20261031/{paired32_v2,resident4_v2}`。archive `4411513e6273e48f814b2e5a34f3dce38a6dd299` 是证据审查起点，不是上述 run 的执行 source。

本次 root no-argument preflight 重新通过：59 个完整 source 文件、4f commit、manifest hash 均匹配；有界回执为 `content_evidence_analysis/CURRENT4F_READONLY_PREFLIGHT.json`。它仅是 CPU/local source identity，`run_record_prelaunch_checked=false`，既不是本次正式补算启动许可记录，也不是 GPU 证据。

## 对正文和后续工作的约束

正文可立即使用 matched16 的 **22.5→51.0 s** 与 **180/14 对 180/14**，清楚标注 retrospective exact-G whole-text agreement、原音频前沿权重和 code-point occurrences。不要继承早期 bdfa 的 **29.0→51.518125 s**，也不要继承其 8/8 到最终 4f。

如正文需要 E 自己的连续可用性或 resident 内容行，唯一缺项操作见 `content_evidence_analysis/FINAL4F_SMALL_CPU_RECOUNT_DESIGN.zh.md`。该草案未冻结、未启动；它限定为现有 20 trial/32 request-instance、一次只读 CPU 汇总、零新 NN。保留全部原失败、原 EOS 和时钟；即使结果为零或未知也如实交付。没有增加来源、神经机制、调参、负载点或新故障矩阵。

## 任务继续后的实现状态（尚非正式结果）

Root 已采纳直接复用 matched16 的已有指标，并要求执行真正缺项的一次 CPU 补算。新 reader 已完成并冻结为独立 commit `c060985ba68caf4caf576dc6783a401c9cfeb91c`；20 个完整源文件 manifest SHA256 `d436ad9acb01a7a7c56968e6f8f027079d089f567154268e3e04fc97f42b4bfd`。`content_source_v1` 是干净执行源，`content_snapshot_v1` 是 plain snapshot，`content_packages_v1/CONTENT_SOURCE_v1.bundle` 是完整历史bundle。该 bundle 已 verify/import 到 root 的独立 execution ref，显式 source preflight 通过；CURRENT 未改。

开发控制为13/13、零skip，fixtures全在RAM；包含paired与resident完整adapter、actual G/F区分、unknown/mismatch、同text不同fullstate、实际错误保存、缺依赖和缺EOS反例。两个开发期fixture断言/Windows路径错误已保留在 `content_evidence_analysis/DEVELOPMENT_CONTROL_FAILURE_v{1,2}.json`。未修改12个byte-exact原依赖模块。

`content_evidence_analysis/build_frozen_content_config.py` 要求真实commit/manifest/environment/rootgate哈希后才能产生具体配置；330个输入（328候选raw加2个原完整RAW_INDEX）均在8TB，root/noarg、formal Linux CPU和完整20扫描仍由Root协调。这一状态不能当作已经完成缺项结果；正式结果后再更新正文数值和本映射。

当前实际冻结候选已更新为 **v2**：commit `f528f7450637f58cb70f3bf6da300e1e5e9a3c18`，完整20文件manifest SHA256 `60342efcc05397e12daa63a8fa5e44cacfbff8927509a16f29c4ca512715b1e4`，路径 `content_source_v2` / `content_packages_v2` / `content_snapshot_v2`。v1未正式启动。v2将空text但内部tip仍ahead的事件/区间与非空实际可见view分开，保留原c4总数，新增nonempty分母与实际visible frontier，防止把内部ahead状态保留误当作可见文字可用性。新增反例后RAM控制14/14通过；v2 bundle已verify/import，显式source预检通过20文件，CURRENT仍未改。详见 `content_evidence_analysis/SOURCE_FREEZE_v2.json`。

独立审查确认v2的内容/连续性方法无阻断，同时指出Root要求的config/environment前后哈希尚缺尾部检查。因此正式候选进一步更新为 **v3**：commit `3a176c417e1fa2372969a010f818d6841656f384`，manifest SHA256 `88be5154656b51c767582196af43644a8a025b6db5bfea0800499512c028ed1f`，路径 `content_source_v3` / `content_packages_v3` / `content_snapshot_v3`。只补了config/env/rootgate/manifest的显式before/after控制及漂移反例；科学reader与12个原依赖未改。RAM控制15/15、显式source预检20文件通过，bundle完整导入；正式执行采用v3，不能用较早候选身份 relabel。详见 `content_evidence_analysis/SOURCE_FREEZE_v3.json`。

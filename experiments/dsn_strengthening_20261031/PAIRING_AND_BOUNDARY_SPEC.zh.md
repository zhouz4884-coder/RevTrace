# 实际后继输入重配对与原长流首次边界规格

状态：2026-10-31 的分析规格；未执行新实验，未产生新的 GPU 证据。仅定义对既有原始日志的只读 CPU 复核。正式扫描前须由主任务冻结本分析代码及配置、记录真实 source commit / environment / config hash，运行根目录无参数 preflight，并将原始输出留在指定 8 TB 盘。不得改写旧实现、CURRENT 或旧结果。

## 1. 要回答的问题与不成立的替代量

问题 A：**每一个实际派发 job 的完整 frozen start，是否等于其实际 start frontier 最终被选择的 Canonical cut？** 问题 B：原无 VAD、无中途 EOS、无 reset 的两条拼接长流，在哪一个可观测边界首次出现重复、长度压力、计算需求超到达或输入确认率下降？

`409/457`、`333/416` 来自 `resilience_metrics.state_metrics`：对已成为 Canonical 的调用，比较该调用自己的 `asr_early.projection.end` 与该调用选定的 `next_state`。这是 **selected-edge own identity-end mismatch**，既不是所有派发后继的分母，也不判断后继实际用了哪个 start。不能写为调度器派发失败率。附件的 `354/366` 未经本规格核验，不继承该分母。

完整 36 格、3976 次 actual Canonical、354 次 conditional promoted-then-installed 是已有证据的计数背景；后者也不能反推未安装、被 kill 或尚无同 frontier 证人的 dispatch 有多少。新统计以原日志逐条重建为准。

## 2. 已核验的数据与源码入口

令 `F=experiments/dsn_native_resilience_20261030`，`B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_resilience_20261030`。

| 目的 | 当前可读材料 | 限制 |
| --- | --- | --- |
| 全部 case 及实际派发、完成、Canonical 数基准 | `F/FORMAL_ACTUAL36_TRACE_RESULTS_v1/cases/*/{CONFIG,SUMMARY,INPUT_MANIFEST}.json` | 只有摘要不能替代 job 级重配 |
| 长流结构、part 参考和样本边界 | `F/FORMAL_SUSTAINED8_V1_RESULTS_v1/cells/*/CONFIG.json` | 每 source 24 parts 有 start/end sample；没有字符/词级时间戳 |
| 完整有界边界序列 | `F/BOUNDED_FORMAL36_RESULTS_v3/cells/*/{native_boundaries,canonical_edges,frontiers,history,gpu_memory}.jsonl` | 此归档不含 dispatch、完整 frozen start、完整选定中间文本 |
| 实际 job、到达、提交、接收与死亡顺序 | `B/{formal_short28_v1,formal_sustained8_v1}/cells/*/owner_e*/{dispatch,worker_results,policy_audit,owner_events}.jsonl` 及 `facts.wal`、`consumer.jsonl`、`ORIGIN.json`、`SERVICE_END.json` | 正式分析须验证原始输入 hash；不得为读取而 repair/truncate WAL |
| 完整身份定义 | `F/source_v2/feedback_contract.py` 的 `FeedbackCut.same` | 比较完整 canonical JSON bytes；不是文本相等或 token 数相等 |
| 同 frontier 判反条件 | `F/source_v2/fullspec_policy.py` 的 `_reason`、`dependency_support_losses` | 较早 ancestor 不同仅为 support loss；未来完整输入仍可能收敛 |
| promotion 独立见证 | `F/source_v2/resilience_policy.py` 的 `_emit_audit` | promotion 带 `owned_job`、`actual_parent_state`，仅作交叉检查 |
| selected model work 定义 | `F/native_work_source_v1/native_work.py` | `model_seconds` 不是 kernel/decoder-forward 次数；selected sum 不是 total paid work |

正式扫描不增加 NN 调用，不把 continuous original / restored oracle 的时间列混进 serving work。原始 GPU 执行 source 为 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`；本轮分析 source commit 应另记，不取代原执行 source。

## 3. 冻结单位与证据索引

实际 dispatch 的稳定主键为 `(cell_id, owner_epoch, job_id)`；另保存 physical slot / incarnation、source_id、dispatch session epoch、request identity、audio_sha、完整 contract、birth Canonical SHA、start frontier、end frontier、start bytes/SHA、frozen dependencies、`started_on_canonical`、dispatch perf。

同一 job 的重复消息不新增 dispatch/complete 数。不同 owner 的 job 即使 serial 相同也不得合并。物理 incarnation、job birth、namespace 可用性与完整输入相等性分列；executor 退出不改变旧 job 的 immutable input。

原始单请求实验的逻辑请求身份由冻结 config、source_id、audio_sha、完整 contract 和该输入链确定。Owner 重启恢复同一个 WAL 链，不创造新请求；恢复后可能出现同样数值的 session epoch，不能只凭该数值跨请求拼接。若未来存在 reset，须增加明确 request/session lifetime ID；无法恢复该映射则 UNRESOLVED，禁止按 source_id 猜测。

从已验证 WAL genesis 与全部 Canonical `parent_state/next_state` 建立每个逻辑请求每个 frontier 的实际选定 cut 索引。多个记录可重复见证同一完整 cut；同一逻辑请求同 frontier 若出现两个不同选定 cut，视为输入证据矛盾并 FAIL，不能挑有利者。对 Owner 故障后恢复，保留事实连续性及原 commit/recovery 顺序。

## 4. 每个 dispatch 的三值结果

令 `S_j` 为 job 的完整 frozen start，`f_j` 为其 start frontier，`A(f_j)` 为同一逻辑请求在该 frontier 的实际选定 Canonical cut。

1. **CONFIRMED**：存在可信 `A(f_j)`，且 `canonical_bytes(S_j)==canonical_bytes(A(f_j))`。`started_on_canonical=true` 也必须通过此复核，另列为 current-root dispatch。确认可以晚于 job 完成、退出或 Owner 死亡；这只是 retrospective input equality，不自动赋予其后续在线安装权。
2. **REFUTED**：存在同 frontier 的可信 `A(f_j)`，但完整 bytes 不同。保存两边 SHA、首个不同字段、证人的 journal sequence/时间；必须真的是 start frontier，不是更早祖先。
3. **UNRESOLVED**：尚无同 frontier 实际选定 cut、epoch/request 映射不明、关键日志缺失、被截断或只有不可验证 hash。细分原因；`covered_by_actual_canonical`、kill、没有 promotion、没有 install、较早依赖失配都不能单独改成 REFUTED。

完整输入确认必须包括 audio segment identity、tokens、context、last_attend_frame、language/decoder、contract、frontier、transcript 等所有原 `STATE_FIELDS`。完全相同文本但 context/token/audio/contract 不同为 REFUTED。不得使用 source-commit 映射投影来确认实际运行的两份输入；旧版本正常回归的静态 source 映射是另一项研究。

另记录 `ancestor_support_loss`，它不覆盖三值结果。若 job 在 ancestor mismatch 后又在自身 start frontier 收敛，结果仍为 CONFIRMED。

## 5. 四种分母及生命周期交叉表

必须同时输出，不能互换：

| 指标 | 分母 | 分子/补充 |
| --- | --- | --- |
| actual dispatch input status | 全部 unique actual dispatch；另列 conditional-only | CONFIRMED、REFUTED、UNRESOLVED 三项和为 dispatch；同时给 resolved-only `C/(C+R)` 及 all-dispatch lower/upper `[C/N,(C+U)/N]` |
| canonical promotion | 全部 unique conditional dispatch；另列 live job promotion audit 总数 | 真实 `promotion` 事件，核对 audit 的 owned_job/actual_parent_state，不能以此代输入确认 |
| actual Canonical use/install | 全部 unique conditional dispatch；再列全部 selected Canonical transitions | WAL 选定 use、owner canonical_install、Consumer consume 三层分列。Owner-after-durable-before-install 应区分 persisted fact 与原 Owner install，并识别恢复后的 apply |
| own predicted-end correctness | 有可验证 own early projection 的 selected Canonical job | 自己的 `projection.end == own next_state`；missing prediction 单列，不补 false |

完整完成回执、abandon、discard、kill/unreturned、stale/fenced、namespace-loss、complete-but-never-used 另列；无回执不等于未计算。promotion 只在 live jobs 的 `_refresh_active` 中产生，已完成 buffered item 的合法 use 不应依赖 promotion audit 的存在，须保留 `installed_without_live_promotion_audit` 交叉单元，若为零也报告。

每个 lifecycle entry 带实际时间和 provenance pointer；不把“input 后来相同”写成“故障后可立即安装”。physical birth/slot/incarnation 永不改写。

## 6. 覆盖与时间轴

完整 36 case 每格都输出，短/长、arm、source、repeat、fault site 分层。长流 8 case 必须全部保留，不能只选最差或最好的 repeat。先逐 case 复核 c4 已有 dispatch / full receipts / selected Canonical 数；与已有计数不符先 FAIL，不静默换分母。

确认率有两种时间图，必须在文件名和列名区分：

- **dispatch-time cohort retrospective status**：按 `t_dispatch-origin` 10 秒 wall bin，以及 `start_frontier/16000` 10 秒 audio bin，对每个 bin 的实际派发 job 统计最终 C/R/U；最后不足一 bin 原样保留。没有 dispatch 的 bin 也保留 N=0、rate=null。
- **online knowledge over wall time**：用截至该时刻真正形成/可知的 Canonical witness 统计 pending/confirmed/refuted；这是当时可知状态，不偷用未来结果。缺少 witness 实际时间则不画该曲线。

时间以同机 perf_counter 与 ORIGIN 为准；audio frontier/16000 为输入位置，不能当 wall time。source/repeat 不拼成一条伪连续流。全量总体同时给 micro counts 与 case 分布，不将 case 平均伪称自然流发生率。

首个确认率下降信号采用预先冻结描述规则：先报首个 REFUTED conditional dispatch 的 audio/wall 位置；再报 20 个 conditional dispatch、stride=1 的滚动窗口中首次 resolved-only rate < 0.5 且 resolved>=10，unknown 另列。阈值仅为诊断标记，不是统计 change-point、控制器或部署阈值；无满足窗口报告 NONE，不事后改阈值。并附固定 10 秒 bins，避免只展示阈值命中的一点。

## 7. 长流首次边界

每一 case 分别给 all-worker 和 selected-Canonical 两层。将 native boundary row 按真实 job key 连接到 dispatch/selected job，不能拿一个 discarded 条件分支的最早事件代表实际选定历史。若 telemetry 少 owner epoch，以所属 owner_e* 路径补，禁止仅凭 job_id 连接。

### 7.1 文本重复与插入

优先从 WAL 读取每个选定完整 cut 的 transcript，再读其原 record top1 / selected text；只读长度归档不能恢复字符重复。保留 whitespace-only 原 CER normalization；同时导出原文 hash、长度和每步增长。

首个可重现**重复信号**：规范化文本内出现相邻重复块 `xx`，每个块至少 8 Unicode codepoints；先报 earliest selected frontier，再列 exact span/hash、block length 和是否已在前一步存在。另报每步新增字符数和历史 n-gram 再现。它是词形信号，不证明错误：原参考也可能合法重复。测试阈值预先冻结，不因看到结果更改。

**显著插入的首次真实时间目前不可直接识别。** CONFIG 只有完整 utterance reference 和 part 的音频边界，没有字符/词时间对齐；而 part 边界通常不落在 8000-sample 调用网格。将整个未到达 reference 按音频比例截字，或把首个 `F>=part.end_sample` 的整个累计 transcript 与完整 parts 的 reference 比，均会伪造 prefixCER（后者还可能把下一 part 已到达的合法文字算成插入）。

允许的报告：

- EOS 与完整已到达 reference 的真实 final CER / edit decomposition；Levenshtein 的 S/D/I 可能多解，冻结 tie-break 并声明其为一种最优对齐。
- 如果某个 selected frontier 恰好等于 part.end_sample，使用此前所有完整 parts 参考作 **offline exactly aligned utterance checkpoint**，不是在线 VAD，也不能反馈 reset。
- 其他 frontier 的重复/增长是 reference-free signal；“首次已证明 insertion”保留 UNRESOLVED，并给最后无信号—首个信号—EOS 的时间定位范围，不能以启发式替代 gold time。
- 若额外做全参考回溯对齐，单列为 offline oracle/annotation，不报告 online prefixCER、不用它筛选样本或控制运行。本任务不启动新的强制对齐 NN。

这使失败边界可刻画，同时保留目前无法证明“第几秒开始真正错误插入”的证据限制。

### 7.2 长度压力

从 `context_trim` 的 before/after 分别报告首次 `total_decoder_input_tokens>=428`（448-20 的原 trim 压力边界）、首次 `>=448`，以及首次 `after.context_trim_triggered=true`。实际 max_text_len 从 row 读，不将 448 硬写成通用模型常量。

`bound_still_exceeded` 依据 `context_token_count>max_context_tokens OR total>max_text_len-20`，并不等价于 `total>=448`；必须分别计数。`state_counts` 的 total 不包含 context prefix token count，逐记录保留该字段与定义。现 telemetry 观察 insert_audio/trim_context，并没有在 decoder guard 分支上打点，因此 `>=448 after trim` 只支持“长度门相关输入条件到达”，不能无条件宣称 actual decoder guard branch executed 或唯一退化原因。

### 7.3 累计模型工作与输入到达

两条量都以实际 source cadence 对齐、从 first job 开始，不含 cold load/warmup：

1. `selected_model_seconds_prefix(F)=sum(selected records with end<=F, model_seconds)`，与 `F/16000` 比较，报告首次大于的位置。这是选定调用的累计模型 wall demand；既不是总服务耗时，也不是 CUDA work 精确计量。
2. 对所有 unique complete/abandoned 回执中确实记录的 actual model interval，累积已知 `model_seconds`，另列 returned-but-rejected 与 selected。缺失 killed-unreturned work 保持 UNKNOWN，known sum 仅下界；不可把没有回执记成零。两卡汇总与每卡占用分列。若用 `known GPU-seconds/(2*audio seconds)>1` 作容量信号，明确它是双 worker 下界而非已测 kernel utilization。

另报告 first trusted progress wall lag、offered/accepted/certified frontier debt，以及原 D/C 不达标的位置；不能用工作量 crossing 单独断言调度器或模型原因。未完成/无模型时间的 row 单列，计时非有限/负数直接 FAIL。

## 8. 反例和质量门

最少反例覆盖：自己的 predicted end 错但实际 successor start 正确；自己的 predicted end 对但某 successor start 的 hidden context 错；较早 ancestor 不同而自身 start 收敛；先 kill 后同 frontier 确认但无在线 install 权；同 frontier 尚未出现；相同 text/不同 token state；重复 completion 不加分母；Owner 重启 job ID 碰撞不合并；已完成 buffered use 无 live promotion audit；未到达 part reference 不可算 prefixCER；428 压力与 448 门条件分开；zero-dispatch bin 保留 null。

输入归档 manifest、完整 WAL checksum/chain、全量 dispatch 唯一性、同 frontier 唯一选定 cut、job/source/cadence/epoch 绑定、输入 bytes hash、case/timebin 覆盖任一异常则 FAIL 并保留诊断。数据缺口不以 assert false 改成 mismatch，须明确 UNRESOLVED。最终 GATE 只裁决本 CPU 分析是否完备、口径是否一致，不裁决新 serving speedup 或 GPU efficacy。

## 9. 预定产物

8 TB 原始输出：`RUN_RECORD.json`、`CONFIG.json`、`ENVIRONMENT.json`、`INPUT_MANIFEST.json`、`dispatch_pairing.jsonl`、`lifecycle_cross_table.json`、`timebins.jsonl`、`long_boundary_rows.jsonl`、`SUMMARY.json`、`GATE.json`。每 row 指向原文件/hash/line 或 WAL offset/sequence。代码与配置不可变，扫描结束再次校验输入 hashes。

本地仅带回有界 `SUMMARY/GATE`、36 case 及 8 long case 完整 coverage table、每个首次边界的有限 witnesses、输入/输出 hashes 和报告。长流原失败与原版本身份不覆盖；新增结果走新 release。若实际 dispatch 完整输入不可取到，最终明确不能完成该统计，保留已有 own-pred-end 数字的正确主语，不凭已有摘要推断分母。

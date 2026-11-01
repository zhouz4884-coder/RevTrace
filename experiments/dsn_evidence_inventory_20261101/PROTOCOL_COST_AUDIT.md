# 协议健壮性与控制面成本：DSN 证据机会盘点

盘点日期：2026-11-01。范围：历史 DGFT 事务 fuzz、101.1 µs 主机微基准、memory/WAL 对照，以及更接近当前稿的 CK5 同输入内核成本对照。只读取本地源码、冻结元数据、结果和历史 Git blob；没有启动实验、导入运行项目模块、访问远端或修改论文。

## 结论与优先级

**确有遗漏的可用证据，但最值得补回的不是最大的 fuzz 次数或最小的 µs 数字。** 更有价值的是一条完整成本链：轻量输入资格判断有现成真实轨迹计时；完整协议在一个正常服务点已有开/关内核的端到端配对；持久化本身有独立真实成本。三者分别回答“检查耗时多少”“加上协议后服务付出多少”“同步持久性是否被漏计”，不能合并成一个免费开销结论。

| 项目 | 已有确切结果 | 对 v9 的价值 | 建议 |
|---|---|---|---|
| DGFT 事务状态 fuzz | 64 会话，250,000 **总**尝试；10,000 合法接受，240,000 变异/重放拒绝；0 非法接受、0 状态不变量违规 | 历史可信提交原语的实现拒绝覆盖；不是整套 EL/AU/SUP 的并发证明 | 附录/工件中的一行支持证据；不让它占据摘要或替代现有组合状态机 |
| 历史 host 微基准 | production commit 中位数 101.107 µs；P99 104.514 µs 是 **31 个重复均值的分位数** | 证明旧 DGFT 检查并非只有日志；不代表当前完整协议或 WAL 的实际请求尾延迟 | 作为历史分解或方法附录；不要直接移植为 v9 当前总成本 |
| memory/WAL CPU 对照 | Windows 配对增量 1.921876 ms/commit；Linux/ext4 13.550189 ms/commit | 把耐久性纳入真实实现成本，并解释为何不能拿 101 µs 代替完整开销 | 作为实现边界/工件；跨机器差值不能归因为 OS |
| **CK5 同输入内核控制** | 8 对 early/no-kernel vs early/kernel：Goodput −0.1298% 至 −0.4183%；WER 差 0；正常 24/24 通过双期限 | **最值得恢复展示的完整集成证据**；但内核后续改变，需标明该版本及工作区间 | 至少在附录保留小表；若要作为 v9 精确成本，补一次同合同成本控制 |
| 当前核心的 EL 计时字段 | `private-continuity-proof.proof_host_wall_seconds` 已在真实服务事件中记录 | 有条件无需新 GPU，就能从当前/近当前运行分析输入资格检查时间 | 优先检查冻结汇总；若没有，做独立有界后处理，分别报告成功/拒绝、链长、调用数和时间分布 |

当前 v9 的 `sections/05_evaluation_core.tex`、`05_operating_boundaries.tex`、`05_native_retention.tex` 已讲联合保留及能耗，未发现以上 250k/101.1 µs 或 CK5 开/关内核成本数值。这里是**证据选取机会**，不是建议把所有历史结果塞进正文。

## 1. 250k fuzz：大分母的正确用法

### 结果及合同

- 原始结果：`results/paper_review_closure/transaction_fuzz.json:3–11`，明确标为 `CPU protocol-state fuzz; not a GPU serving, numerical, or population failure-rate result`。
- 64 会话、seed 20260805、250,000 总尝试，10,000 合法接受，240,000 变异或重放拒绝，0 非法接受和 0 状态不变量违规；最终提交检查点 10,000，PASS（同文件 `:63–69`）。
- 24 个非法类加 1 个合法类。非法类包括错会话、旧 epoch/policy/parent、合同/运行时摘要、音频 gap/overlap、空段、缺失音频摘要、prompt、重复段、证书各字段、已消费事务重放。不是“250k 恶意攻击”，不是“24 种独立结构错误”。
- 生成器 `scripts/run_dgft_transaction_fuzzer.py:1–6,34–60,63–100`：合成 ASCII 音频和小 token 序列；在原本合法的 fixture 上一次改变一个绑定字段；`run(:165)` 顺序调用生产 `commit_canonical_segment(:193)`，检查拒绝不改变已提交状态、接受只推进一个检查点且保持连续前沿。
- 明确不覆盖：可信部件 Byzantine、证书墙钟过期、GPU worker crash、浮点执行（结果 `:65–67`）。不包含真实 Consumer 应用/网络并发/WAL 断电。

### 可核查身份

结果自身没有记录执行源码 commit、环境快照或完整 source manifest，只有 payload digest `c34d2feb513a34df451c776dc0fadaae7d00ec90a69e762203aa8cfceb565c96`。本地 Git 历史将 runner 和结果收录于归档提交 `2b5edfcb6c7e93cce098d48f36868935465993af`；归档结果与当前 JSON 解析内容完全相同（文件换行导致字节不同），runner 字节相同，SHA256 `5f968fa44fbcb6e5aadd14a4fa82108bafe091b9462dfe166ccce13cb02fd15a`。**归档提交不是已证实的实际运行 commit。**

归档里的 `src/revtrace/dgft.py` SHA256 为 `ef7a693dd0f859b621f6be3a3ae4c67d10fda529728def0dcf35336d6dd51d90`。与后期 `experiments/physical_retirement_20261028/source_v3/runtime/src/revtrace/dgft.py`（SHA256 `070d93c406efcc86db218712fffea2d532775d87269e63a78762eb8771de0f4b`）逐定义 AST 对比：所有类与校验/提交函数相同；唯一差异是 `digest_bytes` 输入类型注解从 `bytes` 扩为 `bytes | bytearray | memoryview`，函数体相同。因而该 fuzz 对**延续使用的 DGFT 原语**有实质关联，不能简单丢弃为“无关旧实验”。

但后来的跨根输入资格、整视图支持、ReceiptBroker、实际 Consumer 和持久恢复是外围新增义务。旧 `commit_canonical_segment` 字段一致不等于整套协议已 fuzz 250k 次。当前源码里带有 `tests/test_transaction_fuzzer.py` 也不等于此分母已经在新冻结源码上重跑。

### DSN 写作机会

可写：“The underlying transaction validator also accepted 10,000 valid transitions and rejected 240,000 metadata mutations/replays in a sequential CPU state-machine test; the composed service is evaluated separately.” 应同时保留合法进展分母，避免只展示全拒绝。最适合与当前有限状态枚举和实际进程故障试验组成分层验证表，三行分别写边界，不把三种次数相加。

若需要补强：无需扩大到百万次。更有意义的是在当前冻结源码对 EL/AU/SUP 的输入证据、支持路径及实际消费前后交错做少量可区分的合法/非法成对控制，补上旧测试没有的义务；这比重复同字段随机变异更贴合论文主线。

## 2. 101.107 µs：确是生产原语微基准，但不是 v9 总开销

### 原始设计与数值

- 说明：`Paper_TC/reports/TRANSACTION_OVERHEAD.md:7–24`。
- 数据：`results/tc_transaction_overhead/result.json`、`raw_samples.csv`、`summary.csv`；raw CSV 共 **124 个重复级记录（4 variants × 31 repeats）**，不是逐次请求时延文件。
- 环境：Windows 11、CPython 3.13.5（`E:\Anaconda\python.exe`）、24 logical CPUs、QueryPerformanceCounter；结果 `:9–22` 记录 commit `eeca911090b1a1bd01be234246f690331484c874`、`git_dirty: true`，生产文件 SHA `ef7a...`，runner SHA `0201d362dd3a4c637cb6da487fef2a83ee598eb601d8f504ce01e4c60870a9ac`。
- 固定 fixture：64 KiB 合成音频、256 输入 token、32 显示 token、288 下次 prompt token、8 descendant versions。每 variant 2,000 warmups，31 个随机顺序重复，每重复 20,000 次，GC disabled（结果 `:49–60`；runner `scripts/run_tc_transaction_overhead.py:95–144`）。
- 下表 P95/P99 都是 **31 个重复级 ns/op 均值**的分位数，不能称每请求 P99（报告 `:17`）。

| 路径 | 中位数 µs/op | P95 | P99 | 相对原始 materialization 的中位增量 |
|---|---:|---:|---:|---:|
| immutable state materialization，无校验 | 19.077 | 19.813 | 19.885 | — |
| job validation | 24.835 | 25.636 | 25.887 | 5.745 |
| 累计 job + certificate validation | 80.604 | 82.902 | 85.866 | 61.577 |
| production `commit_canonical_segment` | 101.107 | 104.486 | 104.514 | 81.960 |

旧在线交叉检查是 16 文件内 1,048 个 commit 的 `committed_perf - certified_perf`，中位 1.317701 ms、P95 2.716598 ms、P99 3.784038 ms。该间隔混合 lock wait、conversion、certificate construction/hash、validation、state materialization 与 pending-version update（报告 `:11–13`）。它不是纯校验耗时，也不是当前实际 Consumer D2/C8。

### 对当前稿的关系

旧生产文件 SHA 与本地 `git show eeca911...:src/revtrace/dgft.py` 完全一致；该文件可恢复，虽然整棵工作区当时 dirty。与后期 DGFT 定义关系见第 1 节。不能将 dirty 简化为无证据，也不能把一个文件 hash 当完整 clean-run manifest。

runner `:182–223` 的四种操作止于 DGFT job/certificate/commit fixture；不走后期 `continuity_proof.eligible_chain`、整视图 `_compatible`、实际 Consumer receipt、完整 C/D/V/I/J kernel 或 WAL 同步。因此 **101.107 µs 不能闭合“当前 EL/SUP/full protocol overhead”问题**。

可保留于补充材料的实现分解。若正文只能留一个成本结果，更应选择同合同端到端内核控制，而不是把旧微基准重命名为新方法总成本。

## 3. memory 与 WAL：耐久性不是免费项

### Windows 本地 CPU

结果 `results/dsn_wal_overhead_20261004/run_v1/summary.json:2–14,18–44`，ID `DSN-WAL-OVERHEAD-20261004-V1`。31 paired repeats × 20,000 commits/variant，64 KiB 合成音频、3 显示 token、0 prompt。计时真实 `OnlineRevisionCoordinator.commit_segment`，含 certificate validation/install，durable variant 另含 append + fsync；每 session 仅一个 commit，避免历史增长，**不是持续服务负载**。

- volatile 中位重复均值 94.961835 µs/commit；WAL 2.017277 ms/commit。
- 配对 WAL − volatile 增量中位 1.921876 ms/commit。
- frame append + fsync 中位 1.747999 ms；不能描述为纯 fsync syscall 时间。
- 记录 root `7372133...` dirty，但有 source 文件 SHA：online_coordinator `9c9bca18...`、durable_journal `c51c6826...`、dgft `070d93c4...`（同结果 `:52–59`）。这并非当前 v9 全部源码。

### Linux/ext4 的主要 CPU 持久化控制

结果 `results/dsn_wal_overhead_linux_20261004/rtx3090_ext4_v1/summary.json:2–15,19–45`，ID `DSN-WAL-OVERHEAD-LINUX-3090-EXT4-20261004-V1`。同样 31 × 20,000；实际 Linux 5.15、Python 3.12.13、ext4 指定 8 TB 分区。提交标签 `7372133...+dirty-wal-20261004`，`git_dirty: null`，单独 source hashes 保存。

- volatile 中位重复均值 158.789115 µs；durable 13.709843 ms；配对增量 13.550189 ms。
- append + fsync 中位 9.195156 ms；该计时包含 frame write loop，并非纯 syscall。
- `VALIDATION.json:2–16,38`：31 paired repeat means 独立复算 PASS、四个 source bundle fingerprints 匹配；`raw_per_call_transfer_complete: false`。
- `METADATA_CORRECTION.md`：旧 summary 误保留 Windows 字样，但记录的 Linux kernel、host 和 findmnt 能确定 Linux/ext4，原始值未修改；逐次 raw gzip 下载只到 98,304 bytes，完整原件在远端，当前本地为 `.transfer_partial`。故原 summary 的逐调用尾延迟不作为本次已独立核验的数字。

### DSN 意义及不宜操作

这些结果支持“耐久提交成本需要计入”、特定磁盘下同步开销能远高于纯 CPU 校验。Windows/Linux 同时改变 host、storage 和软件，**不是 OS 因果比较**；均不是 host power-loss/device-failure durability 试验。也不能把每 session 单 commit 的 CPU成本直接乘当前服务行数，估计它的全程 P99。

`docs/CLAIM_BOUNDARIES.md:145–149,170–176` 明确旧一批 headline GPU runs 关闭 WAL；后来才补真实 WAL-enabled service。应依各 run config 分开判断，不能用旧 low-overhead 数字覆盖新耐久合同。

**最合理的选取**：在实现或开销附录保留此真实成本边界；当前核心服务的能耗/延迟仍用当前同步 journal 的实测。新成本试验若做，必须沿用当前 group-ready batching 和实际消费路径，不应退回 per-call 单事务 fsync 来制造“不公平高开销”。

## 4. 更有价值的遗漏：CK5 正常态同输入开/关内核

### 完整身份与设计

- 实验 ID `REVTRACE-CK5-20261026`；最终执行 source `b8aa802c687256d3801612dc8bee585ee849ddea`，148 files，`experiments/composed_kernel_20261026/SOURCE_v6.json:2–3`，源码包 `SOURCE_v6.tar.gz`，可恢复 Git bundle `RUNTIME_CK5_v6.bundle`。
- 原始根目录记录于 `FINAL_REPORT.zh.md:14–17`：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/ck5_v6`。本地 bounded evidence 包 5,190,920 bytes，SHA `8a9c2791f7c9080ccd49cc4335c1c75342625edc9655cef75a318add11e8843c`；3,975 原始 files、230,763,651 bytes 留在实验盘（是资料分母，不是运行分母）。
- `collected_v6/normal/FREEZE.json:1–388,1135–1138`：24 cells＝Qwen/Whisper × DGFT/complete Standard × legacy/no-kernel、early/no-kernel、early/kernel × 2 fresh repeats。真正隔离 kernel 的是每 adapter/method/repeat 中 **early/no-kernel vs early/kernel**，共 8 对，不能把所有 legacy 差异归于 kernel。
- normal 每 run 4 来源、199 参考词；整个实验池 8 个唯一复用 N5 来源，不能按 24 runs 扩大独立 acoustic sample。2-s Private grid、rho=3，4 个 offsets 0/.25/.5/.75，FP16 Private/GPU0、FP32 Authority/GPU1，maximum microbatch16。WAL durable/group_ready、two_lane Consumer、retain_verified_private_prefix、canonical_generate、实际 row delivery，D2/C8 原时钟。
- 实例 config：`collected_v6/normal/002-qwen-dgft_original-early-k1-r0/attempt0/config.json:1–23,98–118`，source/manifest/runtime/backend 均记录；Qwen transformers-eager、rollback5/unfixed2。Whisper 是其自己的 get_prompt_ids 反馈合同，不能将两个模型作为同一数值任务。
- `collected_v6/FINAL_RESOURCE_AND_SOURCE_v1.json` 保存 Linux5.15/Python3.12.13、torch2.9.1/transformers4.57.6/qwen-asr0.0.6、双 RTX3090 24 GB 的环境，以及 84 正式 + 6 开发单元的最终 source/退出门。

### 结果与可用性

`analysis_v1/ANALYSIS_v1.json:1332–1412` 的 8 对：

| 端点（kernel on − off） | 8 对范围 |
|---|---:|
| Goodput 相对变化 | −0.418279% 至 −0.129815% |
| GPU J/audio-s 相对变化 | −0.176871% 至 +1.243334% |
| display P99 秒差 | +0.041297 至 +0.404353 |
| commit-view P99 秒差 | −0.007216 至 +0.292302 |
| WER 百分点差 | 全部 0 |

normal 24/24 通过 D2/C8；正式 44 个规范化历史比较组完整 Z/P/text/frontier 相等（`FINAL_REPORT.zh.md:31–42,61–67`）。因此能回答“组合机制进入真实同步服务后是否仍能工作，以及服务代价是否失控”。比单个 CPU fixture 更贴合 DSN 的可部署性问题。

负面边界同样保留：没有吞吐加速；所有 display P99 配对差为正；只有两次 fresh repeats、短窗口、复用少量来源，不能写显著性或总体 P99 保证。fault 36/36 和 post_sync 8/8 未通过全程双 SLO，这也不能被 normal24/24 隐去。

### 与 v9 core 的精确关系

以 `physical_retirement_20261028/source_v3/runtime` 作为后期核心 carrier，SHA 比较发现：

| 文件 | CK5 与后期 core 字节关系 |
|---|---|
| `continuity_proof.py` | 相同（`b1cab992...`） |
| `durable_journal.py` | 相同（`874a4aed...`） |
| `dgft.py` | 相同（`070d93c4...`） |
| `composed_kernel.py` | 改变：`3006b628...` → `7f12f3cd...` |
| `certified_display.py` | 改变：`103629ff...` → `21969898...` |
| `kernel_runtime.py` | 改变：`987698f6...` → `62a5508b...` |
| `live_qwen.py` | 改变：`b8e1c77a...` → `e157bb2a...` |

后期 `composed_kernel.py:75–82` 支持 event-copy/incremental，与 CK5 全状态 deepcopy 行为不同。因此 **不能把 CK5 −0.13%..−0.42% 精确宣称为当前 v9 110-cell 的开销**，更不能推广至 native4f 的另一执行合同。可作为有明确版本的历史集成控制，或用原配对设计补当前冻结源同合同的最小成本控制。

## 5. 当前已有计时埋点：不用凭空再开模型扩展分支

`experiments/physical_retirement_20261028/source_v3/runtime/src/revtrace/live_qwen.py:658–662` 在真实调用 `eligible_chain` 周围用 perf_counter 计时并记录：

```
kind = private-continuity-proof
eligible, witness
proof_host_wall_seconds
certified_frontier, canonical_version, branch_chunk, branch_generation
```

同路径 `continuity_proof.py:2–23` 明确遍历已选根的完整 feedback projection、已完成依赖链、冻结 in-flight successor 输入；这是与论文 [EL] 直接对应的计时范围，不是旧 DGFT commit 的改名。

已有本地真实事件：

- `service_opportunity_v2/covered-F2-r0/attempt0/events.jsonl:199` 可见一个真实 `private-continuity-proof` 事件（单值不作为成本结论）。
- 同轮 `covered-F2-r1`、`row_complete-F2-r0`、`row_complete-F2-r1` 也含此字段。
- `covered-F2-r0/attempt0/config.json:23,61,114–127` 记录 source `1d8c30804a945570429d85d934b3bfcba6171a43`、WAL/group_ready、event-cow、manifest `69560358173834f45fa284c472bdfab8f284f82ff13034efcc4408a7f492ea04`。

本次只定位字段与冻结身份，没有把它新复算为论文数值。这些运行仍不是 v9 全部确认 cell；若取数必须按实际 source/arm/合同分层，并确认事件计时只包 eligibility，不包 Consumer SUP、trusted selection AU 或 fsync。一个图内可同时展示“单次资格检查”和“端到端协议开销”，但要分开面板、分开分母。

## 6. 建议取舍与最小后续动作

1. **优先恢复完整协议成本控制的可见性。** 若页数允许，附录放 CK5 8 对的小表，说明是一个正常服务点的集成控制。正文最多一句指向它，避免把论文写回实验目录。
2. **优先利用已有当前轨迹，而非继续放大 legacy fuzz 分母。** 对确认源或 source-v3 的 `proof_host_wall_seconds` 做可重算的有界摘要；按链长、成功/拒绝分组，同时计总 CPU time/episode，防止只报微小 median 隐去频繁调用的总负担。
3. 若审稿预判要求“当前方法增加多少成本”，最小新实验是当前冻结 core 源、一个已证实可服务的工作点、同输入/同 journal/同 Consumer 的开关证据检查控制，并保留真实质量、完整任务、能耗、P99。**不是继续扩模型，不是再做一个不同 WAL 合同。** 若禁用 kernel 也改变检查义务，应将其命名为成本下界控制而非同等安全强基线。
4. legacy 250k 进入 artifact validation 表，legacy101µs/WAL 进入历史实现成本表。它们补的是可执行拒绝与成本解释，不创造主贡献，不用来覆盖当前故障与持续状态边界。

这套选取能增强 DSN 式论证：在明确失效模型下，不仅阻止错误授权，也允许合法进展，并交代维持该边界需要付出的可测成本。最有竞争力的说法来自这三点的对应，而不是一个没有合同说明的大测试次数。

## 7. 追加定位：当前合同已有的成本字段与 27/35 控制

**检索结论：110 格和 48 格有现成 controller/input-fsync 的逐 run 汇总，但目前没有找到这两组的 EL、SUP 或完整 kernel 微基准汇总。** 不能把“源码有计时”“原始事件有字段”写成“已完成当前协议开销基准”。本节只读取已有汇总的键和值，不运行 reader，不从 raw 新计算分布。

### 7.1 现成汇总与可提取数字

| 已有汇总位置 | 已有记录 | 成本字段 | 状态 |
|---|---:|---|---|
| `physical_retirement_20261028/H3_RESULTS_v2/aggregate/RUNS.json` | 110 | `controller_CPU_seconds`, `controller_host_seconds`, `controller_decisions`, `input_fsync_seconds` | 已完成逐 run 汇总；无 `proof_host_wall_seconds` / `kernel_CPU_seconds` / Consumer CPU 字段 |
| `dsn_service_stability_20261028/RESULTS_v1/aggregate/RUNS.json` | 36 | 同上 | 已完成；不是新的 guard cost 表 |
| `dsn_midpoint_continuity_20261029/RESULTS_v1/core/aggregate/RUNS.json` | 12 | 同上 | 已完成；与前 36 合为稿中 48-run 工作区间 |

例如，现成 joint 行 `primary-qwen-rho1-sync-CA-R1_S1-r0` 报 controller CPU **3.414517 s**、controller host **4.023576 s**、19,647 decisions、input-fsync **0.387306 s**；`stability-c16-staggered-r1_s1-r0` 为 **3.287967 / 5.281243 s**、10,110 decisions、input-fsync **1.720659 s**；`midpoint-c12-staggered-r1_s1-r2` 为 **2.774326 / 4.710814 s**、11,126 decisions、input-fsync **1.855552 s**。这些只是已报告单 run 的定位例子，不是三种工作负载的汇总统计或因果开销差。

这些键由 `physical_retirement_20261028/source_v3/x_service_metrics.py:367–368` 从 `result.json` 复制。`certified_envelope.py:223–238` 的计时覆盖 `_tick` 内 ACK 消费、pressure、mode 选择、ingress 和观察日志；可能包括触发的 input checkpoint/fsync。它**不包整个神经结果安装或 EL/SUP 流程**，也不能与 input-fsync 无条件相加（范围可能重叠）。

### 7.2 五种计时范围不能混为“protocol overhead”

以下源码均位于 `physical_retirement_20261028/source_v3/runtime/`：

| 字段/工件 | 实际计时范围 | 未包含/需要注意 |
|---|---|---|
| events `proof_host_wall_seconds`，`src/revtrace/live_qwen.py:658–662` | 仅 `eligible_chain` 调用的 host wall time；对应 R/[EL] 输入和依赖链资格判断 | 不含之后 branch 根更新、事件序列化、AU、SUP、WAL、Consumer；只在保留开启时调用。现有本地 `service_opportunity_v2` 四份 events 有字段，但这不证明 110/48 已有汇总 |
| `kernel_trace.json.cpu_seconds`，`composed_kernel.py:264–280`；runner `scripts/run_tc_live_qwen.py:662–664` | **先获得 RLock，再起 thread_time**；计 ReceiptBroker 的 payload deepcopy/issue/take 以及 `step`（含 event-copy/状态检查） | 不含锁等待；累加计时之后才做 trace 的 `sha(payload)`、JSON 化和 append。后置 SHA 仍在锁内，只是**在计时外**；调用方 dispatch/result 的 normalization/hash 也在 `Kernel.event` 外。不能称全部内核 CPU 或端到端开销 |
| `consumer.consumer_cpu_seconds`，`certified_display.py:174–205` | FIFO 线程取到项后，JSON parse、`view.consume`（含 KernelView 的预演/SUP 和内核调用）、生成收据及可选 crash diagnostic 写入 | 不含 queue wait、producer `put` 的 JSON serialization、最后 close 时输出全部 records；thread CPU 不计等待时间。可能与 kernel CPU 重叠，不能相加当不重叠分解 |
| Consumer row `view_application_seconds`，同文件 `:177–187` | parse 之后到 `view.consume` 返回的 wall time，涵盖实际视图决策/应用 | 包 KernelView 外层锁等待、preview 的 deepcopy/consume 与 apply gates，不能只称单独 SUP predicate；不是网络显示时间。可在 raw Consumer 轨迹中定位，当前 aggregate 未汇总 |
| commit event `journal_fsync_seconds`，`live_qwen.py:688`；`durable_journal.py:290–330` | group frame 的 write loop + fsync；group 中各 transition 返回**同一个整组 elapsed** | 不含 timer 之前 JSON serialization/hash/frame preparation，也不含之后 `_apply_record`。不可逐 transition 直接求和，否则重复计算一组同步；字段名不意味着 syscall-only |

另外，`input_fsync_seconds` 是 `input_debt_journal.py:78–80` 的 `os.fsync` 周围 wall time累计，范围比 Canonical journal 的 write+fsync 更窄。SUP 实际路径见 `kernel_runtime.py:30–55`：在同一个外层 RLock 内先 deepcopy/preview.consume，再 `apply-request`、替换实际 view、`view-applied`。单独 `kernel.cpu_seconds` 没量到这整段。

当前 runner 确实会写 `kernel_trace.json`，但本地 110/48 的 bounded aggregates 未保留该 CPU 字段；这属于**已埋点、需按 raw 索引确认并有界提取**，不是已经完成的当前版本微基准。上述全部字段也都不适用于 native4f 的另一套 serving source；native 的开销需按其 actual contract 单列。

### 7.3 旧 250k 与当前 27/35：覆盖的是不同判断

| 层级 | 可核查位置/身份 | 实质覆盖与新增价值 | 不能替代 |
|---|---|---|---|
| 旧 250k | 本报告第 1 节 | 顺序事务原语的字段绑定、前沿连续、重复/重放和拒绝不变性；同时有 10k 合法接受 | 完整 frozen native cut、原 C/U provenance、未来 UNKNOWN 的生存、实际整视图、持久接纳和恢复交错 |
| 当前 27 个有限规格命名控制 | `dsn_native_refinement_20261030/FORMAL_RESULTS_v3/SUMMARY.json:2–7`；source `deb3260655e2f3312499a34597cc0be6fc15484b`；`source_v3/test_model.py:28–204` | 明确 UNKNOWN/CONFIRMED/REFUTED 与用途分离、完整 C/U 允许关系、未来结果 buffer、自己的预测错不否定已确认输入、祖先失配后再收敛；兼容 whole view 保留/必要撤销；每 commit 自己的 root；worker-only buffer 原身份、物理 exit 后复用、fsync 后安装、旧域和原时钟 | 手写有限规格，不是从 Python/CUDA 抽取；normal 6,231 状态/11,142 边与 failure 14,074/25,799 分属不同 bounds，12-event 深度确有 cutoff，不是无限活性证明 |
| 当前 35 个 checker synthetic 控制 | `dsn_native_refinement_20261030/trace_source_v2/test_refinement_trace.py:65–261`；source `c4dde9ea9c7abf80fae084bc2293e193262c71e6`；`SHORT_ACTUAL_TRACE_RESULTS_v2/.../CPU_CONTROLS.log` | 独立 binary frame checksum/torn-tail、完整 cut 未知字段拒绝、同 text 隐状态不授权、真实原 full-call/选择 IDs、旧 Owner 不重签、相同/冲突 duplicate、实际 Consumer/path/root、accepted obligation 完结、原 ingress 时钟、真实 PID/exit/GPU release 绑定 | 35 是 distinct synthetic checker 控件，不是 35 种自然故障；六 trial 每次重跑仍只有35种。更晚 actual36/4f 检查应按其新 source/控制包独立引用 |

35 控制对应的既有六个开发 NN trials 实际汇总是 102 durable transitions、305 Consumer applications、107 Private path links（`SHORT_ACTUAL_TRACE_RESULTS_v2.zh.md:9–11,32`）；这些实际记录与 synthetic 控制分母分开。该六 trial 中 policy-local rejection 观测为 **0**（同文 `:26`），所以不能用35控件补造真实 duplicate/late 拒绝次数。当前正式故障 bank 的对应观测应引用其独立检查，不把旧250k或开发0分母移植过去。

## 8. 早期机制 family 的入口覆盖与可迁移教训

本次追加覆盖下列八个目录的最终入口、研究决策及选定机器可读汇总，不逐条读取 raw，也不执行历史工具。这些 family 常被后期 NO-GO 标签遮住，但其**机制见证**仍有价值。它们主要帮助解释时间、权限、依赖和资源的关系，不应重新包装成当前 R×S 的性能确认。

### 8.1 覆盖地图

| 目录 / 实际身份 | 已读入口 | 有用的历史事实与对当前论文的用途 |
|---|---|---|
| `online_admission_20261022`；runtime `55cd52dfdbab71298cdb7eae3b0c08c9424020c6` | `C2_BOTTLENECK_FINDINGS_AND_PLAN.zh.md`；`unpublished_release_build_v1/RESULTS_SUMMARY.md`；`collected_evidence_v1/collected/selective_protocol_v1/SUMMARY.json` | 72 正式单元；Coarse 少做 Authority 工作并节能，却因合法显示窗口损失降低双期限 Goodput；旧失配时仍在途的 Private 暴露及批尾屏障有实际轨迹。这是“安全/少工作不等于服务好”的直接前史。`unpublished_release_build` 仅是本地旧入口，不能当已发布新结果 |
| `causal_row_completion_20261023`；runtime `2bc71af5457de5d065ff9e771d2fad428c5c6ed9` | `README_FINAL_v2.md`；`R3_FINDINGS.zh.md` | 150 真实服务 cells，5,033 次实际 Canonical Consumer 应用早于 physical batch drain，其中812早于失败 peer fallback 完成；说明逻辑完成与资源释放确实有不同时间。属共享执行能力，Standard 也获益，不能用来制造 RevTrace 独占 |
| `causal_evidence_scheduling_20261023`；runtime `e0aeae1b418644c378dde331c59b55fc5948b40f` | `README_DELIVERY.md`；`reports/RESEARCH_REPORT.zh.md`；`OBSERVED_FAILURE_NOTES.zh.md` | 33 pilots +180 正式 cells，固定 fine2/rho1，完整验证/付费 fallback/WAL/Consumer；同步有局部正结果，独立 Mixed 错峰相对 Joint Cost-only Goodput −31.51%、能耗 +18.64%。说明保护更多潜在工作与完整服务收益要分别检验 |
| `ces_v5_20261023`，CPU-only | `README.md`；`RESEARCH_DECISION.zh.md`；`cpu_validation_v2/SUMMARY.json` | 有限 oracle、行CDF、前驱价值反例、CPU优化与历史校准；明确没有该轮GPU。对“期限由均值推出来”“相同完成集合能合并全部隐藏状态”“模型最优等于运行最优”等说法有构造反例 |
| `ces_v5_gpu_20261025`；runtime `126dc815962e8f726b0cbdf214a19318b28a3629` | `README.md`；`RESEARCH_REPORT.zh.md`；`CONTRIBUTION_EVIDENCE_MATRIX.md`；`DECISION.json` | 48 正式在线 cells、16复用来源、2 oracle；同身份已就绪目标被13次放在计划后缀，实际排队13.068s；完整工作计价没有形成跨重规划的服务预留。双路径未来预测还漏掉真实及时 Private |
| `ces_v5_closed_loop_20261025`；runtime `e45c66475ba1173a98b49b8c9e62f3e8cb45b333` | `RESEARCH_REPORT.zh.md`；`IMPLEMENTATION_COVERAGE.md` 入口定位 | 后继期限/价值回传与服务义务已真正接入；72正式 cells 仍未赢强 Fine/Cost，不能继续把负结果归因于“没接上”。单次规划P99中位158ms，说明更复杂的因果调度本身消耗服务余量 |
| `ces_v6_abcd_20261025`；A/B/C `e135683d5bb681bf74f507375352e62b53604574`、A isolated `ed3d4247e28a55cadc02f08139232c838b9c7b57`、D `d3e418b6d1090a78c3a84156ecc87b02a8ee42c4` | `README.md`；`RESEARCH_REPORT.zh.md`；`FINAL_DECISIONS.json` | 98真实服务单元、36 operator submissions；**固定 Authority 完整结果下，安装时序改变未来 Private 输入和物理长尾**，是本 family 最适合 DSN 的机制发现；独立 D 性能门未过，不混用 |
| `evidence_retirement_20261026`；baseline CK5 `b8aa802...`，开发执行 `b4a4502dfcf796b3c509b81ecb93312bcace51e2` | `USER_PAUSE_REPORT.md`；`ACTIVE_STATE.json`；`screen_v3/RETIREMENT_SCREEN.json`、`RETENTION_EQUIVALENCE.csv`；开发 summary 元数据 | CPU 激进收缩在24构造场景中18个丢失合法迟到进展；安全修复保留与强活跃根对照完全相同的证据。非ASR GPU开发质量/预算失败、独立审计未完成，不能作为真实应用成功或长期有界内存证据。旧暂停文档仅说明该轮止点，不是本次用户要求停止检索 |

### 8.2 最值得选择性利用的四条机制证据

**A. 最强补充：反馈安装时刻能够改变尚未冻结的未来计算，而非只改变 UI。**

`ces_v6_abcd_20261025/RESEARCH_REPORT.zh.md:59–63`：Mixed 中1.5s对0s安装干预，三组16会话的48/48 Authority目标的 Parent、输入、完整 batch 张量、Z/P/text 全匹配；GPU0总物理 lease 分别多6.289/6.265/5.839s，专属于未来派发工作也多6.271/6.381/5.715s。每次都由同一已诊断来源触发未来 Private256-token长尾，三重复不是三类独立故障。

最关键的是0.75s敏感性：虽然跨过下一音频释放，却在 Private 真正派发前完成安装，未触发同样长尾。实际因果边界是**下一任务完整输入冻结/派发**，不是“新音频到了”“版本变了”或“文字更新了”。它能支撑 DSN 的问题重要性：可信反馈的协调会改变后继的真实执行条件和资源占用，不能只看 token计数或单点显示。

可迁移的是机制和设计教训；不要移植为当前联合保留的额外6秒收益。该旧试验使用不同 scheduler、注入 Mixed 条件与安装干预，且关键候选在派发后2.60–2.71s才返回，而 Fine Authority约1.70s已完成；报告明确指出即使验证免费，等待该候选也不能赢这条已执行路径。可放附录一个简明时序图/机制验证；若正文已有足够当前同合同证据，Discussion一句及工件定位就够了。

**B. 从安全到活性的分界：完整计价不是服务承诺，合法保留也不是期限保证。**

`ces_v5_gpu_20261025/RESEARCH_REPORT.zh.md:113–145` 的实际 same-parent/prompt/frontier 目标在14次空闲决策中前13次均被排到第二批；就绪至 enqueue13.068001s，而自己的完整行执行仅0.226821s。时间包含别人真实执行，不是13秒免费空档。`CONTRIBUTION_EVIDENCE_MATRIX.md:9–14` 同时记录该机制和45/56个“Private及时、Canonical显示晚但最终Commit及时”的真实路径，说明只预测一条完成路径会误判服务信用。

后续闭环版已经接上服务义务和后继回传，仍在72正式cells中错峰Causal/Fine Goodput配对中位−32.348%，全程双P99为0/72；planner累计中位1.468s/run、单次P99中位158ms（`ces_v5_closed_loop_20261025/RESEARCH_REPORT.zh.md:74–81,106–137`）。因此当前论文应坚定区分“EL/SUP使仍合法的进展持续可用”与“调度保证所有期限”。这不是削弱主张，而是把机制贡献对准能实证证明的故障模式；不建议再把复杂 CES 作为当前主贡献救回。

**C. 保留与回收之间存在可检查的真正困难：ACK/epoch 不是所有证据的死亡证明。**

`evidence_retirement_20261026/screen_v3/RETIREMENT_SCREEN.json:2943–2947`：200 CPU随机控制；激进收缩18/24丢失未来根下的合法进展，精确修复后与 strong live-root tracking 保留证据相同；evidence tier明确为 CPU prototype/synthetic state microbenchmark。`USER_PAUSE_REPORT.md:13–29` 另有 pending operation、view completion逆序、跨session、原时钟等纯core反例，但旧实际ASR wrappers原已有保护，不能写成当前系统被攻破。

这有助于把当前长期状态边界写得具体：要安全减少历史，必须刻画仍在途的冻结任务、实际Consumer支持链、未完成持久事务和未来可合法重连根，而非仅看到ACK/新epoch就删除。**该轮未证明一种优于常规活跃根的方法，也没有完成长期GPU验证。** 适合作为 Discussion 的后续问题及未来有界内存设计的负例约束；不要用它声称当前已经 bounded-state。

**D. “同一输出”与“相同未来可执行状态”曾在真实模型轨迹中分离。**

`causal_row_completion_20261023/R3_FINDINGS.zh.md:4–29`：8个原生长来源、2 adapters、各2重复、652次实际模型调用；Qwen受控改变P后6/8在后续有限步骤重新精确相等，Whisper在已改变P的7来源里0/7于观察期恢复。一个Whisper来源先在后续窗口Z相等、再在下一窗口重新分歧，而P始终不同。它同时否定“输出一样就恢复”和“反馈一旦不同就永久失效”两种过度简化。

对当前主线的价值是给“版本号/文字/producer状态不能替代完整判断”一个独立旧模型机制动机，而非再添加一套主表。两adapter的分段/故障构造不同，不是记忆拓扑的隔离对照；Whisper仅余2个10s后续窗口，0/7不能推永久不恢复。后期native完整cut与此旧历史投影不同，不能把6/8或0/7套到native4f。

### 8.3 适合保留的工程正结果，与不应继续挖的方向

`causal_row_completion_20261023/README_FINAL_v2.md:12–29,42–44` 已有共享 row-complete 的实际服务正结果：旧注册sync16/F2下DGFT batch→row配对Goodput中位+53.56%，Standard同样+43.71%，fsync中位从10到43且计费；5,033次真实认证消费早于batch drain。它解释当前系统为何区分“完成的合法结果可交付”和“物理槽已可复用”，可以作为实现能力的历史验证，不能声称当前R×S实验又得到53.56%独占速度提升。当前稿已经共享该能力时，正文引用结构条件即可，旧结果留工件/附录。

`online_admission_20261022/C2_BOTTLENECK_FINDINGS_AND_PLAN.zh.md:27–59,75–94` 也给出有用负载解释：Coarse真实节省Authority物理调用却损失显示及时率；26个已知失配仍在途暴露里23个发现时尚未过D2、14个有至少1s后续Authority空档，但具体窗口仍只有约1.225s，不能假定Rescue一定来得及。后来的Rescue六目标两次FP32成本调用，五个连最好成本都超过窗口（row README `:26–29`）。选择当前保留机会而非“失配后一律重算”有实在系统背景。

不建议为找漂亮数继续挖：CES的局部同步正结果（强对照并不全赢）、旧 CPU oracle最优值（固定模型）、旧 planner优化287→29ms（CPU实现优化）、B fallback节省3.13%（未过5%门）、未完成非ASR质量开发。更强的论文选取是：**当前同合同R×S主证据 + 一个必要的时序机制解释 + 清晰的负载/回收边界**。其余 family 用于约束过度主张和规划下一次真正有区别的实验，不让主文回到算法尝试目录。

## 9. 更早 Phase 2–7 与 final_closure：补核入口

已按入口核读以下文件，无新 raw 重算：`results/phase2/PAPER_TABLES.md`；`phase3/adaptive_control/REPORT.md`、`idle_audit/REPORT.md`（另核其 `summary.json`）、`rir_pilot/REPORT.md`、`rir_population/REPORT.md`、`second_architecture/REPORT.md`；`phase4/PAPER_TABLES.md`；`phase5/PAPER_TABLES.md`（另核 `baselines/summary.json`）；`phase6/PAPER_TABLES.md`；`phase7/PAPER_TABLES.md`；`final_closure/REPORT.md`。同时核对 `docs/CLAIM_BOUNDARIES.md:131–149,328–375`，避免沿用入口表里过宽的旧命名。

| 入口 family | 最有用的内容 | 对当前 DSN 选取的判断 |
|---|---|---|
| Phase2 + Phase3 adaptive | 旧risk-limited/统计风险证书、冻结失败必须进入后续排除集合；零差异不是算术确定证书 | 风险策略与当前 exact授权协议不同；5–6x旧headline不能移植。若写论文演进，不把经验confidence当[AU] |
| Phase3 idle audit + Phase4 SlackGuard | margin优先审计在离线回放中有用，但VOI未胜margin；全请求审计309.9ms，相对27.5ms侵入预算超11.27倍 | 物理动作粒度决定能否兑现“后台无干扰”，比scheduler/stream优先级名称重要；已有当前物理退出证据时这里只留设计教训 |
| Phase3 RIR pilot/population | output flip可被状态投影吸收；自然/stress分别计，distinct pair仅19/15，50-pair gate未过 | 可支撑“先确认state-entry再谈传播”的动机，不引用其不足的总体率/普遍放大结论 |
| Phase3 second architecture | Voxtral120执行rows、零shape差异；公开音频被tiled，growing-prefix Transformers probe | 是适用边界，不能变成新真实流式部署或跨模型零错保证，不建议加入正文扩模型名单 |
| **Phase4/5 feedback和复制一致性** | 反馈边是损害传播的因果路径；一次输出相等/多次复制一致不足以替代完整状态和原选择权 | 值得作为一个旧合同的机制支持或附录反例，而非性能主表；下面单列范围 |
| Phase5 workload / Phase6 admission / Phase7 queue | 统计状态风险可过而服务期限仍失败；收缩active并未消除外部排队，c64 active P99 1.942s、guard2.042s、E2E44.797s | 支持当前坚持全部offered/原时钟的评估设计；不搬旧capacity值宣称当前D2/C8工作区间 |
| final_closure | 区分online选择权与事后replay draw；精度/布局/attention backend合同；独立steady3seed有1seed P99 2.0277s、28miss | 有力约束“同输入重跑等于唯一真值”“一次P99成功就是容量保证”；当前Native原C/U provenance比重跑固定draw更合适 |

**可选择性恢复的一项具体机制证据。** Phase4/5旧Whisper反馈干预共21个合法 execution-induced 输出对：9对 decoded `prompt_text` 相同、12对不同，8/21在feedback ON传播、OFF为0，6对在两个后续窗口边界仍不同（`docs/CLAIM_BOUNDARIES.md:133–144`）。最大RAF153是含注入窗的累计距离序列1、64、88，terminal-only ratio为88；不得将二者混写，也不得称153倍应用故障或生产风险。该runner传decoded previous-window text，与后期R9 raw-token history及native4f完整cut合同不同。

`results/phase5/PAPER_TABLES.md:25–30` 的replication-consistency控制在base仅护住10/16已知对、tiny仅1/5，表中仍有output/state差异36/32、11/10；它提示“再次算得一样”不能自动形成可信选择/反馈状态的授权依据。入口级检索未在此处展开实际完整runner合同和源码身份，因此如要给正文一个精确独立claim，应再沿其summary source/config核对；当前更稳妥的用途是设计教训和旧结果定位，不把它混入v9的3,976次当前转移审计分母。

**取舍。** 这些最早数据没有揭示一条可以无条件补成当前论文新主贡献的大性能结果。它们确实提供三个适合 DSN 的判断依据：先区分输出差异是否进入反馈状态；可信选择权与重复执行一致性分离；服务评价保留排队和原offered义务。将这三个判断落实在当前机制/评估叙述，比增加一页旧加速比更能稳固当前主线。

## 10. 独立判断：14 个历史合法 view 点值得按持续可用目标重开分析吗？

**值得，优先级高于再扩随机故障或模型名字。** 旧结论对其原目标——新增首次2s显示信用、独立高效索引算法——是合理的；但它没有检验“已经存在合法已登记证据时，是否仍不必要地留下服务空窗”。当前论文主张改为持续合法进展后，仅凭旧首次信用为0继续淘汰这条机会，会把两个不同服务性质混在一起。`S_DECISION.md:53–60` 自己也明确提出 sustained coverage 是可重新开启的目标。因此建议恢复为**有待量化的合法进展完成性机会**，而非撤销旧NO-GO、宣称已有部署收益。

### 10.1 这与当前 v9 的 S 有什么区别？

当前 `Paper_DSN/revisions/20261101_dsn2027_release_v9/sections/03_continuation.tex:65–90` 的命题是：Canonical应用前**当前可见**h若兼容且领先，就保留h；它明确是per-application性质。对应 `physical_retirement_20261028/source_v3/runtime/src/revtrace/certified_display.py:82–95` 只检查 `s['tentative']`；该tip不兼容时清空，未遍历仍留在 `s['nodes']` 的更早合法候选。收到不兼容新Private publication时也会清掉当前tentative；保留proof nodes本身不等于选择了最佳已有view。

历史实现 `legal_progress_20261026/final_source_v2/runtime/src/revtrace/historical_display.py:35–88,107–135` 则在当前根下，从**Consumer已登记、未被独立撤权、合法完整支持路径**的集合中选最大frontier，保留原job、text、epoch、birth和发布身份，且通过原kernel最终申请/应用门。它处理的是：最新tip失效/已清空，但更早tip现在仍合法，是否能恢复或选出它。普通索引与scan同效说明不应主张新索引算法；它**不否定这个更完整的服务性质或它在系统协调中的价值**。

当前110格/48格载体还显式固定latest：`source_v3/runtime/scripts/run_tc_live_qwen.py:154–158` 的physical-retirement入口拒绝混合非latest history selector；`history_selector`默认latest。因此这14例不能简单归为“已经被v9的S实验完全涵盖”。可将S分成“保住当前合法view”和“从合法已登记历史中找回进展”两个层次；是否把第二层纳入论文方法，要由下述服务价值而非名字决定。

### 10.2 三个最直接的原表/工件定位

| 本地位置 | 关键字段及已经证明什么 | 尚未证明什么 |
|---|---|---|
| `legal_progress_20261026/S0_N5_SCAN_v2.json` | `counts`：151 attempts、9,442 Canonical applications、14 consumer-known opportunities、14,207 registered host private rows；`opportunities[]` 有 attempt/source/session/root/version/candidate_job/branch、`actual_frontier`/`oracle_frontier`、`extra_audio_seconds`、`host_received`、`actual_consumer_cut`、mode/revision floor和逐完整网格deadline；每attempt的`trace_identity`给events/Consumer/worker/config/sessions的bytes/SHA | 14是point cuts，集中三条实际正常阶段运行11/1/2；同job可跨多个cut重复，不能当14独立job/窗口，更不能把extra_audio_seconds直接相加为持续收益 |
| `legal_progress_20261026/S_INDEPENDENT_v2.json` | `positive_published_cuts:14`；六策略各自`checks`绑定原job、Canonical事实、前沿、原host receipt、原Consumer apply、重放apply；selected14个旧view都通过实际原job/P/Z/text的独立core检查。`quarantine_eligible:0`，另12个未发布候选均被真实generation retirement排除 | 没有gap起止、右删失、持续area、首次已显示/首次及时显示分类。`wall_replay_seconds`是CPU快放全流耗时，不是原服务空窗；`candidate_age_seconds`也不是损失时长 |
| `legal_progress_20261026/RAW_EVIDENCE.tar.gz` 内 `s_independent_v2/{fine_fair-return_low-r0,fine_fair-return_low-r2,standard_fair-finite_overload-r1}-{latest,scan,mv-index,...}.jsonl`；对应本地 `RAW_INDEX.json:3424–3509` | 本地归档确有3×6=18份FIFO CPU策略重放Consumer轨迹及summary，index逐项bytes/SHA；归档SHA `7b2209a70accd423074353b38e6116168c5ea43f1317875fbab7ddd2b5255285` | 它们的`observed_perf`属于新的快速CPU重放时钟，不能拿作原GPU服务读时点。需要映射回原实际Consumer时序后才可量化原trace持续损失 |

14个positive cut属于**已发布且Consumer已登记**的候选，扫描按mode/revision-floor和原native兼容关系筛选，独立core正例检查通过；与那12个未发布且已退休generation的quarantine候选完全不同。不得恢复已被明确CERTIFIED-ONLY/RECOVERY或epoch fence撤权的内容。

还必须补一个分类：**已登记不等于此前已合法可见。** 当前Consumer对不兼容publication先写入nodes再拒绝显示；因此不能预先把14个都叫“恢复此前用户看过的view”。它们可能是曾实际显示的旧覆盖恢复，也可能是一个旧publication首次在新根下变为合法；两种都可有服务价值，但对应的连续性论证和分母不同。

### 10.3 已有数据能量化什么，还缺什么？

已有summary足以给出**point-cut的合法覆盖差**、选中旧job及原读时点，不能给出持续秒数。应重建每个session在相邻真实Consumer事件间的piecewise-constant合法覆盖，并在每次根变更、Private publication、owner-mode/epoch撤权时重验证。令 `F_registered*(t)` 是当时已登记且当前有完整权限/支持证据的最大frontier，`F_policy(t)` 是某策略的合法实际覆盖；可量化

`∫ max(0, F_registered*(t) − F_policy(t)) / sample_rate dt`

单位为audio-s×wall-s。另报distinct缺失区间、每次空窗持续时长/最长空窗、恢复到首次再被真实消费覆盖的时间，以及与原D2读时点相交的缺失音频。单独分列①曾实际覆盖后恢复，②旧登记view首次在新根变合法，③当前view直接保留；再分首次D2及时/已晚及最终C8及时/已晚。根变更或撤权时重验，末端未结束窗口右删失，重复cut/同一音频不能重复相加。

**本地可做一部分，原时钟完整答案尚需取回/定位原raw。** 已确认本地archive有18份CPU重放轨迹，可离线检查策略view序列；但 `s_independent_audit.py:34–43` 一次性enqueue原事件，时间被压缩。14个检查只保存各自原`original_actual_apply`，没有全序列原Consumer读时点。因此精确积分与空窗结束需要三条原attempt的`consumer.jsonl`、`events.jsonl`；重新完整检查所有资格还需要相应`worker_records.jsonl`、`config.json`和`sessions.json`。具体远端attempt均列在S0表，原始根为8TB的`results/revtrace/dependability_20261025/n5_v3_supervisor_v2/formal_normal/`下：

- `fine_fair-return_low-r0/attempt0`（11点）；
- `standard_fair-finite_overload-r1/attempt0`（1点）；
- `fine_fair-return_low-r2/attempt0`（2点）。

各文件已有原SHA；本次未在本地展开树或检查过的N5常用有界archive内找到这三条完整原Consumer/event银行。原件可按已存SHA取回，不需要新模型调用，也不需要重跑GPU。若只借重放`server_time`作映射，只能报告Owner-publication时轴的离线估计，不能冒充原实际Consumer时轴。

**FIRST2与partial EOS的限定。** 旧scanner `s0_source_v2/scan_historical_views_v2.py:67–76` 用fine=32,000样本步长枚举完整2s网格；多条fractional EOS覆盖机会的`deadlines=[]`。这说明旧FIRST2审计scope与当前v9全部partial-EOS进入offered分母的scope不同，**不直接推出EOS有新收益，也不推翻旧scope下的0**。下一步应按原会话duration/EOS ready重算该类别，完整网格与尾窗分别报告。

### 10.4 具体可证伪下一步

1. **先做一次冻结的CPU机会分析，不开模型。** 按三条正例及全部151/136尝试原索引保留零机会/失败分母，读取旧published registry、实际Consumer/模式时钟；比较当前latest-S、完整scan和普通索引，按同一个原root/event序列执行最终权限门。固定原事件/模型历史得到的是离线机制重放，不是部署端到端效果。
2. **预先冻结新假设：** 最大合法已登记view选择能减少某些“已有合法证据但策略未显示”的净持续缺口；无需增加首次D2信用。先以原Consumer时轴、distinct音频与完整EOS计量，扣除真实选择/应用路径延迟，报告重显旧文本引起的字符修订或同前沿文本代价。若窗口全为瞬时、均在撤权下、原时钟重建后无正时长，或净窗口小于实际应用代价，则保留完成性回归，不升级为服务收益。
3. **再判断是否属于当前主线剩余空间。** 在当前110/48原记录用当前最终native+kernel关系只读扫描，找出latest-S之后仍存在的历史合法tip缺口；不要把旧14点当独立新来源确认。如果当前bank没有此类残余，旧结果适合作为扩展性质/附录；若存在正的、反复出现且无未来信息的持续窗口，再冻结最小真实在线三臂（latest-S、scan、普通索引）验证，给完整Standard相同能力，保持R、WAL、输出合同、offered分母和原时钟。

**研究选择：应把它从“旧索引算法NO-GO”里拆出来，保留为“已登记合法进展完成性”的高优先级CPU检索机会。** 现有14点足以证明当前最新项选择并不完备；还不足以证明14个有效恢复窗口、多少秒持续收益或一项新的部署胜利。普通索引同效不妨碍一个清晰的协议/系统组合贡献，但系统收益必须由新的持续服务目标与原时钟证据完成闭环。

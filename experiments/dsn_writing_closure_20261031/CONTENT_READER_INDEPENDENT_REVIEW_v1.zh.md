# content reader 独立审查 v1（最终审查对象 v4）

审查 ID：`REVIEW_CONTENT_CPU_V4_20261031`。审查范围为本机只读源代码、既有有界元数据、RAM 控制及末节的正式结果有界包 QA；未访问远端、未二次读取远端 raw、未调用 NN、未修改 CURRENT、未修改任何执行源。唯一新增文件为本报告。正式 Linux 控制和 20-trial 补算由 CPU 执行 agent 完成，本审查独立核验其本地有界输出，未把审查本身称为新神经实验。

## 结论

**最终结论：PASS_INDEPENDENT_BOUNDED_RESULT_QA（v4）。** v4 正式 Linux 控制 15/15、完整 20-trial CPU 补算及本地有界包独立 QA 均已完成。具体数据、哈希和局限见末节。预启动阶段的 v4 GO 已由实际结果核验承接；R1 控制文件末尾哈希缺失由 v3 修复，R2 root gate 错绑原 NN 身份由 v4 修复。独立审查先前的 v3 GO 漏检了 R2，已明确撤回，不能把旧 GO 视为覆盖真实启动合同。

最终审查身份：

| 项目 | 独立复核值 |
| --- | --- |
| analysis source commit | `6eb6639478a87e6be971e23282bd2f31789f242f` |
| complete manifest SHA256 | `2dac41b61a84c5de8846564bdcb7c7c6bd8159e51b35012f385c6e781282637c` |
| source root | `D:\VLA_QWEN\RevTrace\experiments\dsn_writing_closure_20261031\content_source_v4` |
| source gate | 执行 RAM 控制前后各 PASS，20 个文件，干净独立 checkout，全 commit 可解析 |
| scientific reader | `content_reader.py` 与 v2/v3 字节完全相同 |
| vendored dependencies | 12/12 与 v2/v3、各原始本机 source 文件字节完全相同 |
| v4 RAM controls | 15/15 PASS，0 skip；`python -B`，无 fixture/raw 文件写入 |
| 本机环境 | `E:\Anaconda\python.exe`；Python 3.13.5（Anaconda）；`Windows-11-10.0.26200-SP0` |

## 逐项语义审查

### 1. 实际文字与 actual-first-G

`content_reader.py::analyze_trial` 使用 byte-exact 原 `content_endpoints.analyze_cell`。新增/撤回按 LCP 维护 Unicode code-point occurrences；同一文字撤回后重现重新计 occurrence。raw 与 `str.isspace()` 去空白版本分开计算。它不建立字符与音频、token 的对齐。

每个原 offered 前沿 F 的首次显示行必须同时满足 `observed >= original_offer(F)` 和 `visible_frontier >= F`。比较所用的 G 是该行自己的 `visible_frontier`。`posterior_support` 将这一行的整段文字与选中 Canonical 在 `(source_id,G)` 的 `next_state.transcript` 比较，未代换 F、最终文字、CER 或模糊相似度。缺失 G 文本为 unknown；mismatch 单列。原信用按 supported/mismatching/unknown 分桶，三者之和必须守恒。全部 offered 的计数单列，未按是否及时筛选。

原逻辑的 `visible_frontier=0` 对空 transcript 不给正 F 显示信用。v2/v3 的连续性输出另行区分 internal ahead empty tip 与 actual nonempty view；不能把前者写成保存了可读短语。

有界既有元数据复核为每臂 8 matched trial：原前沿信用 30.0/65.821625 s；支持信用 22.5/51.0 s；失配 7.5/14.821625 s；unknown 0；introduced/retracted/last-visible 分别两臂均 180/14/166。raw 和去空白结果相同。这一段记录预启动元数据核对；正式 CPU 补算及其独立有界 QA 已在末节完成。

**写作边界：** 22.5→51.0 s 是“及时且事后 actual-G 全文相等的音频前沿权重”；不是新增文字量、临时文字人工正确率或连续正确文本时间。matched 实际字符 occurrence 数未提高；所有 offered 的全文相等计数是 106/136→104/136，不能从加权及时信用推出无条件文字质量提升。

### 2. 完整实际路径与持续性

原 `refinement_trace.audit` 在连续性函数之前验证完整 WAL 链、实际 dispatch/physical owner/incarnation、原 full-call receipt、selected C/token IDs、完整 durable parent/next cut、publication receipt 和逐条实际 Consumer snapshot。private path 的每个完整 cut 与实际 ASR projection/full result 绑定。它是结构追踪审查，仍以 host/source execution integrity 为前提，未重算神经数值。

`continuity` 独立重建同样的完整状态链。Canonical boundary 是否 compatible 由完整 cut 相等决定；单纯 text 相等不足。compatible ahead 时保留整个 tip，incompatible ahead 时清除不再成立的私有后缀；每步预期 canonical SHA、certified frontier、visible frontier、text、private job 均与实际 Consumer 行相等。出现缺链或 snapshot 不一致立即失败，不输出“unknown=0/错误=0”的成功摘要。

同源相邻实际 Consumer 观察形成 `[start,end)` 逻辑 held-state 区间；最后状态在最后一条真实同源观察处右删失，不延伸到 SERVICE_END/UI 关闭。相同完整 tip 跨 compatible boundary 合并为一个 segment；不同合法 tip 是 supersession。包含 compatible update 的 segment 总秒数包括该 tip 在 update 前后的已观察 residence，不能解释成更新后才开始的增益，也不是服务 availability percentage。

`compatible_ahead_applications` 与 c4 原计数保持相同 internal-tip 分母，另有 `compatible_ahead_nonempty_views`、`compatible_ahead_empty_tips`、nonempty segment seconds。正文若论可见成果，必须引用 nonempty 字段。`wrong_compatible_withdrawals=0` 只有在全部实际快照重建通过时成立；不能据此声称人类全文语义正确或在线 G 已获认证。

### 3. resident 原始请求时钟

结构 `audit(...)` 本身不含可悄悄回落的单 origin 计时参数；旧 `check_dispatch_arrivals(origin,...)` 在本 adapter 中未被调用。resident 显式读取 `REQUEST_ORIGINS.json` 与 ledger，并通过 `audit_request_clocks` 检查 admission、前请求 actual certified EOS、ingress 原 offer 和全 EOS。每个 dispatch 用 `origins[job['source_id']] + end/16000` 作下界；每个请求的 `analyze_cell`、`recount` 都传该 sid 自己的 origin。原总 primary 和逐请求 primary 均与旧 SUMMARY 守恒。

除已有 15 项控制外，独立审查在 RAM 拼接两个真实完整结构 fixture：origins=100/110，两请求、四 durable fact、12 Consumer 行、四 offered 前沿、两次 compatible preservation，实际穿过 `analyze_trial`、结构 checker 和 resident ledger，结果 PASS。正确 D99=1.6 s；故意全局借用首 origin 得到 D99=11.588 s，证明此反例能暴露错误时钟。该数是 synthetic RAM 控制，不是 serving 测量。

首次拼接尝试因审查 fixture 转换器只处理 list/dict、遗漏 tuple，未转换 frame 内 source/job，正确被结构 checker 拒绝；修正审查 fixture 后通过。该错误不归因于 reader，也未修改产品源。

## 固定覆盖和输入回链

独立读取本地 `COMPLETED_METADATA_CONTENT_INDEX.json`、两份原 RAW_INDEX、原 campaign SUMMARY 与 preregistered source identities，结果如下：

| cohort / arm | trial | request instance | 原 offered 前沿 |
| --- | ---: | ---: | ---: |
| paired / conservative | 8 | 8 | 136 |
| paired / fullcall | 8 | 8 | 136 |
| resident / conservative | 2 | 8 | 136 |
| resident / fullcall | 2 | 8 | 136 |
| 总计 | 20 | 32 | 544 |

四条独立声学来源保持四条，重复与 cohort 不能增加来源独立性。328 个选中原输入共 130,929,528 bytes；每条路径、bytes、SHA 均与原完整 RAW_INDEX 对应条目相等。builder 另加两份完整 RAW_INDEX，正式输入合计 330。此处检查的是本地已保存元数据一致性，未声称重新哈希远端 raw。

`run_content_recount.py` 先验证全固定 20 分布，再逐个验证 330 输入，回链原 inventory、执行所有 trial、强制 32 个独立 `(cell_id,sid)` 请求，并在末尾复验全部 raw SHA。matched 原端点与字符/support 加总还受明确已知值门约束。所有 path 须落在指定 8TB `/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9`，实际 output 设备/剩余空间另检查。原 raw 与新 output 不得交叠；新 output 与 lease 均独占，失败保留 FAIL gate，不自动覆盖或重启原 worker。

`evidence_io.source_gate` 检查独立 checkout、干净 HEAD、完整解析 commit、全部 tracked 文件与完整 manifest 的 byte/hash、依赖 byte pins。runner 先记录实际 analysis source、原 NN source、config/env/index/stdout/stderr/output/gate 位置，再进行 data analysis；analysis commit 不冒充 4f NN commit 或 evidence archive HEAD。

## 发现与处理

**R1：v2 控制文件缺少结束哈希复核，已修复。** v2 仅对 config/environment/root no-argument receipt/manifest 作启动检查，尾部只有 source 与 raw 的重复验证，不满足本任务明确的 config/env before-after 合同。该问题已第一时间告知 Root/writer，未把 v2 当作正式补算源。

v3 新增 `control_hashes`/`verify_controls_unchanged`；在两种 mode 开始记录四个文件 bytes/SHA，成功尾部比较并保存 `CONTROL_HASHES_AFTER.json`，有漂移立即 fail。独立比较补丁仅涉及 evidence I/O、runner、反例与 README；scientific reader 与 12 依赖未变。新增 drift-negative control 检查不变通过、改变拒绝；v3 15/15 RAM 控制及前后 source gate 均通过。R1 状态：CLOSED。

本审查没有发现需扩展新来源、新 NN、额外负载矩阵、修改旧依赖或改变科学端点的具体缺陷。

**R2：v3 root no-argument gate 错绑 4f NN 身份，已在 v4 修复；先前独立 GO 漏检。** Root 在正式启动准备中发现，v3 `run_content_recount.py` 明确要求 root gate 的 commit/manifest 必须为原 NN 的 4f 身份，但本次实际执行的是新的 CPU analysis source。AGENTS 要求 no-argument gate 验证当前实际执行源，不能用另一源的预检替代。我读到此条件却未把它与实际 analysis launch 完整对照，因此此前 v3 GO 有真实遗漏，已撤回并保留于本报告。该启动门错误与文字/时钟计算无关，也不能当成神经实验负结果。

v4 将此谓词改为 root gate 的 commit/manifest 与 `cfg.analysis_source_commit` / `cfg.analysis_source_manifest_sha256` 相等，继续要求 PASS 与 CURRENT pointer 回执；原 `actual_NN_execution_commit`、内容 adapter 的 FINAL 和 durable 原运行审查仍独立固定为 4f，没有重标原日志。

独立审查读取 v4 冻结源与真实 `ROOT_NOARG_CONTENT_CPU_v4.json`，编译并评估 runner **实际 AST 中的门谓词**：真实 analysis 预检回执通过；将其 commit/manifest 替换为 NN4f 身份则拒绝；manifest 改变也拒绝。v4 source gate 前后各 PASS20，15/15 RAM 控制通过，scientific reader 与原依赖字节未变。R2 状态：CLOSED；此后重新给出以 v4 为准的 GO。

文档判断校正：此前审查曾把 v3 README 的 CURRENT4f 旧句误判为 v4 残留；随后独立读取 v4 `README.md:12` 并对照 v3/v4 diff，确认 v4 已改为“root no-argument CURRENT analysis-source receipt”，与可执行门一致。该先前文档判断撤回，v4 没有这一残留问题。

## 正式执行后的必需核验（预启动要求，完成情况见下节）

Root 应以 v4 的真实 Linux environment、指向当前实际 CPU analysis source 的 no-argument gate 和具体 frozen config 完成独立 controls ID 与 complete20 ID。原 NN4f 只作为既有 trace 的 execution source 单列。正式完成需同时看到 PASS gate、完整 RUN_RECORD/CONFIG/ENVIRONMENT、15 项 Linux 控制、330 输入前后 SHA、不变控制文件前后 SHA、20 trial/32 request/544 offered 守恒以及真实 aggregate。resident support 与本组 nonempty continuous residence 的数字由该正式结果提供；本报告不预填零值或沿用 F 的 90/90。

以上 GO 仅是预启动判断；实际补算完成及数据结论须由正式 gate 决定。下节独立核验这部分实际输出。

## v4 正式有界结果的独立 QA

最终 QA 决策为 **PASS_INDEPENDENT_BOUNDED_RESULT_QA**。只读取 `CONTENT_CPU_V4_RESULTS` 本地有界包并作独立交叉加总，没有再次 SSH 或扫描原 raw。独立 QA 脚本未调用 reader 的 `aggregate()`，直接从 PER_REQUEST、PER_TRIAL、FIRST_G、事件、区间与 segments 重算并比较 SUMMARY。

### 运行身份与完整性

| 项目 | 已核验值 |
| --- | --- |
| controls ID | `SC_FINAL4F_EXISTING20_CONTENT_CONTROLS_V4` |
| complete20 ID | `SC_FINAL4F_EXISTING20_CONTENT_COMPLETE20_V4` |
| actual analysis source | `6eb6639478a87e6be971e23282bd2f31789f242f` |
| 原 NN source，未重标 | `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47` |
| Linux CPU environment | Python 3.12.13 conda-forge；Linux 5.15.0-139；标准库 CPU；`CUDA_VISIBLE_DEVICES=''`；forbidden imports 空 |
| environment SHA256 | `20754f9b6698153792f6ebe14538172f0da2b7980d8b249b9b6aecee733ffbec` |
| controls config SHA256 | `26c1a720cfd937c344e1af129679cabf3129631a1c75ae7c47f4e3fda17d1306` |
| complete20 config SHA256 | `5c8b1933fb9734170740468ec342ff8238686b5005771e31a139b011ab71783f` |
| complete20 SUMMARY SHA256 | `a3c9292ecccebc3660870e181e491d1d41d778941827b51cffa5914f64a26e33` |
| COLLECTION_INDEX SHA256 | `feaad3eeecb8296511401c40e30f4ebe429258e2bdd6e5f5a4c1510120616e94` |
| collection | 38 个清单文件，3,054,652 bytes，逐文件 bytes/SHA 全部一致；除清单自身无漏列或额外文件 |
| 正式 controls | 15/15、0 skip；两 phase stderr 都为空，stdout 与 SUMMARY 一致 |
| 输入 receipt | 330 文件、131,134,574 bytes，INPUT_HASHES_BEFORE/AFTER 完全一致且与 frozen config 的全部 input 条目一致 |
| 控制文件 receipt | 两 phase 各 config/env/rootgate/manifest 四文件前后 bytes/SHA 相同，与收集的实际文件或本机同 manifest 字节一致 |
| 记录闭环 | PRELAUNCH/FINAL/config/summary/GATE 的 ID、source、config/env SHA 与 summary SHA 相互一致 |

真实 no-argument root receipt 指向本次 analysis commit/manifest；原 NN4f 独立保存在 run record 与逐 trial 数据。config 中 source、env、rootgate、raw/output、lease、stdout/stderr 路径均在指定 8TB。正式完整阶段 UTC 为 `2026-10-31T11:15:57.829736+00:00` 至 `11:16:04.237551+00:00`，全阶段记录新 NN 调用为 0。独立 QA 未重新验证远端设备或二次哈希 raw，它核验的是上述完整执行回执及收集字节的一致性。

### 端点与字符结果

20 trial、32 个唯一 `(cell_id,source_id)` request、544 offered 前沿与 544 durable original transitions 全部守恒；四组各 8 请求/136 offered。逐请求只有一个 EOS；FIRST_G 的 offer 与其自身 request origin 一致，G≥F，首次观测时间与保存的原 D 一致，原 dual credit 与原 D2/C8 判定一致。逐请求 code-point occurrences 的 introduced = retracted + last-visible，原信用的 supported + mismatching + unknown 守恒。

| group | 原及时前沿信用 / s | first-G supported / s | mismatching / s | unknown / s | introduced / retracted / last-visible | 原整请求通过 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| paired conservative | 30 | 22.5 | 7.5 | 0 | 180 / 14 / 166 | 0/8 |
| paired fullcall | 65.821625 | 51 | 14.821625 | 0 | 180 / 14 / 166 | 6/8 |
| resident conservative | 31 | 24 | 7 | 0 | 180 / 14 / 166 | 0/8 |
| resident fullcall | 64.118875 | 50.2590625 | 13.8598125 | 0 | 180 / 14 / 166 | 7/8 |

raw 与去空白每个对应字段均一致。544 个实际 first-G 状态共 420 supported、124 mismatching、0 unknown；每组全部 offered 的支持计数仍是 Conservative 106/136、Full-call 104/136。unknown=0 是这些有限完整日志中每个实际 G 均有可比较的选中 Canonical 文本，且每个依赖路径完整重建通过；并非把缺失数据、因果支持未证或人类正确性未知写成零错误。

最终可写“matched 及时且事后同 G 全文一致的前沿信用从 22.5 增至 51.0 s；resident 为 24.0 至 50.2590625 s”。必须同时说明它们是音频前沿加权的 timeliness，实际引入/撤回字符量各组相同、失配保留。不能改写为多产出正确字符或所有文字在线获证。

### 连续性、零机会和删失

逐 trial 的结构状态均 PASS，WAL 忽略尾字节均为 0。1604 条实际 Consumer 行生成 1572 个同源相邻观察区间（1604−32），676 个完整 tip segment。所有区间与 segment 非负且完整路径已验证；逐请求区间/segment 时间边界连续、持续时间加总相等。每个请求恰有一个末 segment 在最后实际同源观察右删失，共 32 个；没有延伸到服务结束。事件、逐 trial 结构计数和 group aggregate 交叉一致。

| group | compatible ahead 实际机会/保留 | 非空 compatible 机会/保留 | 必要不兼容撤回 | crossing-compatible 非空 segment residence |
| --- | --- | --- | ---: | ---: |
| paired conservative | 0 / 0 | 0 / 0 | 0 | 0 s |
| paired fullcall | 0 / 0 | 0 / 0 | 2 | 0 s |
| resident conservative | 0 / 0 | 0 / 0 | 0 | 0 s |
| resident fullcall | 1 / 1 | 1 / 1 | 2 | 0.816859619691968 s |

**matched 的 compatible 机会为零，保存率不可定义，不能写成 100%。** 全部 5 个 ahead 事件包括 4 次必要不兼容撤回和 1 次 compatible 保存，实际 snapshot 与完整边界判据一致。仅 resident fullcall r0、source `BAC009S0905W0246` 出现 1 次非空 compatible 保存：frontier 80000 的相同完整 tip 跨 Canonical 72000 安装保留，12 code points，private job `e0-j000000011` 未变。

该 segment 从 row 24 / `5185848.456899025` 到 row 29 / `5185849.273758644`，在 row 25 / `5185848.563842505` 跨 compatible boundary，最后由合法 supersession 结束。0.816859619691968 s 包含 update 前约 0.1069434807 s 和之后约 0.7099161390 s 的逻辑 held-state residence；它不是一次新的 UI 物理读取、不应全解释为更新后额外收益，也不是新 deadline credit 或整体服务连续可用率。单个事件不能支撑自然发生率、普遍机制成功率或 deployment SLA。

本次有界 QA 未发现新的结果聚合或分母错误。R1/R2 修复过程、v3 独立 GO 的遗漏和 v4 正式结果均保留，最终通过仅覆盖上述固定日志及明确语义。

# 最终 4f 最小只读 CPU 补算草案（未启动）

状态：DRAFT_ONLY_NOT_FROZEN_NOT_LAUNCHED。本文件不授予启动新 NN；不改 CURRENT，不把未执行的计划写成结果。

## 唯一问题与范围

补齐已完成最终 4f matched16 的 compatible-view 保留/持续可用性证据，以及已完成 resident4 的 16 请求实际文字和 actual-first-G 全文事后支持。matched16 已保存的文字和 first-G 数字只作守恒校验，不另开实验；它们已能直接用于正文。

范围固定：`PAIRED32_V2_RESULTS` 中16个 `version=final` cell，及 `RESIDENT4_V2_RESULTS` 的4个cell。共20个既有 trial、32个 request-instance。新模型调用0、不导入或初始化模型、不用 CUDA、不改原 raw/summary/gate、不替换旧失败。没有新增音频来源、重复、矩阵点或故障。

已有 RAW_INDEX 给出候选输入328文件、130929528 bytes，逐文件绝对8TB路径/长度/SHA已列入 `COMPLETED_METADATA_CONTENT_INDEX.json.future_CPU_recount_input_candidates`。候选列表含有可删减的审计旁证；冻结时只允许删去明确不消费的字段依赖，不准扩成全目录扫描。输入总上限256MiB；导出总上限8MiB；单线程、CPU，原始大文件始终留在8TB，不复制本地。

## 冻结与记录后才能执行

建议 experiment ID：`SC_FINAL4F_EXISTING20_CONTENT_AVAILABILITY_CPU_V1`。指定输出（必须为尚不存在目录）：

- raw/analysis output：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_writing_closure_20261031/final4f_existing20_content_cpu_v1`。
- `CONFIG_FROZEN.json`：完整20 cell与328候选文件白名单、各SHA/bytes、32 request身份与原时钟、单位、所有端点公式、unknown规则、输入/输出预算、已有结果守恒目标。
- `ENVIRONMENT.json`：实际8TB Python可执行路径、Python/platform、纯CPU依赖版本、`new_model_calls=0`、模型模块未加载证据、`CUDA_VISIBLE_DEVICES` 为空；生成后冻结SHA。
- `RUN_RECORD_PRELAUNCH.json`：真实分析 `code_commit`、完整 manifest SHA、frozen config/environment hash、原 NN execution commit4f、controller a13、输入白名单SHA、raw/result/summary/gate路径。正式开始前不得有待填 commit/hash。
- 完成产物：`SUMMARY.json`、`GATE.json`、`PER_REQUEST.json`、`AVAILABILITY_EVENTS.json`、有界 `AVAILABILITY_INTERVALS.json`、`INPUT_HASHES_BEFORE.json`/`AFTER.json`、`RUN_RECORD_FINAL.json`、`INDEPENDENT_QA.json`。

需要 resident adapter 和 interval reader，因此不能冒用原4f作为新分析代码身份。新 wrapper 必须在独立干净 source checkout 中提交、生成完整字节manifest并冻结，再执行 explicit source preflight。它的真实 commit 目前 **未创建/未冻结**，不得预填为4f、a13、c4或archive441。

依赖保持完整身份：4f 的 `content_endpoints.py`/`resilience_metrics.py`/`resilience_storage.py`/`feedback_contract.py`；a13 的 `resident_analysis.py::audit_request_clocks`；c4 的 `refinement_trace.py`。优先把所消费的精确模块纳入新source完整manifest，附原commit与原文件SHA；若使用外部干净source依赖，分别验证其完整manifest，不能只校验wrapper。

开始前从root运行 no-argument `experiments/repository_identity_20261027/preflight.py`，要求CURRENT仍匹配原4f与manifest。再用 `--source NEW_CLEAN_ANALYSIS_SOURCE --manifest NEW_MANIFEST --run-record RUN_RECORD_PRELAUNCH.json` 验新分析源。无需为了CPU分析改CURRENT；两种身份分开记录。检查8TB目标真实设备/空间和无相同ID既有进程，确认无并行timed NN后再读raw，以免分析I/O污染别的正式计时。

## 原 raw 的最小充分字段

每cell：CONFIG/ENVIRONMENT/RUN_RECORD、GENESIS、ORIGIN/SERVICE_END、consumer/consumer_rejections、facts.wal、publications、ingress，以及owner的dispatch/worker_results/owner_events。resident额外固定 REQUEST_ORIGINS 和request_ledger。用原facts.wal frame verifier，`repair_tail=False`；任何缺字节或SHA不符直接FAIL，不修复原WAL。

consumer提供实际 `observed/source_id/owner_epoch/kind/text/visible_frontier/certified_frontier/canonical_sha/private_job/publication_id/journal_sequence`；publication提供每条完整 `steps.start/end` 依赖cut；facts提供parent/next完整state与原C/U、receipt和sequence；dispatch/worker_results提供原UID/birth/incarnation、完整输入和原完整回执。只用Consumer文字与最终history相同不能替代因果支持核查。

## 端点与实现

1. **文字和 first-G。** matched16调用原函数只校验已有内容结果。resident按sid拆分consumer和sources，明确用 `REQUEST_ORIGINS[sid]`；用a13 request-clock审计确认500ms/EOS/all-offered和准入顺序后，再调用4f `analyze_cell`。F的首显行是`observed >= offer(F)`且`visible_frontier >= F`的首行，G取该行实际visible_frontier。只在完整fact存在 `(sid,G)` 时按wholetext exact equality分类supported/mismatching，否则unknown。raw与whitespace-stripped同时保留；信用三桶守恒、全部offered计数单列。
2. **事件级 compatible-view。** 复用c4实际Consumer重放，从full dependency cut判断Canonical同边界是否相等、更新前tip是否ahead，验证after snapshot的完整预期字段；输出compatible-ahead总数、保留数、失配后必要withdrawal数、wrong withdrawal、完整源身份和实际row/perf索引。事件分母为实际应用，不是模型调用或自然发生率。
3. **观察区间与持续性。** 在已验证完整日志前缀内，按每source实际Consumer `observed`排序，把Consumer快照视为从本行保持到下一条同源实际应用；最后一行严格在最后实际观察右删失，不能延伸到SERVICE_END或假想浏览器关闭。逐compatible更新记录原ahead tip在更新前/后是否仍由完整依赖链支持、是否发生frontier或整段对象的撤回；记录从其首次实际可见到合法supersession/必要失配/末次观察的区间。若更新后仍是同一完整tip，跨compatible事件合并持续区间；若换成不同合法进展，标superseded，不把变化自动记为中断。unknown/fullstate缺失单列，不能记零缺陷。
4. **限定可解释性。** 可计算逻辑Consumer状态的事件间可见区间、compatible更新时的保留和错误撤回，以及必要修订引起的显示回退。这个“持续可用性”是在完整应用日志与实现状态保持前提下的observed logical-view连续性，不是网络/browser物理可达性、人工正确率、一般生产availability或在线认证。若不能证明某区间支持，报告unknown或只保留事件级计数；不得为出正结果新增推断规则。
5. **分层。** paired与resident分别表，所有Conservative/Full-call及每request的原deadline失败保留。既有actual36只作机制参照，不合并分母，不重新扫描其raw。

## 最小控制与 gate

在冻结source中预先保存四个有意义的CPU fixture：兼容Canonical更新保留原ahead view；同边界完整state失配必须撤回；只有text相同而完整cut不同不能判兼容；缺少G canonical必须unknown。另加一个resident双request不同origin fixture，防止把第二请求错接trial ORIGIN。采用有界真实row样本作read-only schema预检，不加载NN。

正式gate需要：全部指定输入before/after长度SHA一致；完整WAL/receipt/publication/Consumer绑定通过；resident请求时钟与全部32 request-instance身份守恒；matched16现有`180/14/166`、`22.5/7.5/0`与`51/14.821625/0`、原D2/C8/credit全都守恒；supported+mismatching+unknown守恒；interval不越source、请求origin或末次实际观察，unknown不补零；CPU fixtures通过；新模型调用与模型初始化0；预算不超限。任何错误保留FAIL_GATE与异常，不修饰为性能负结果或重跑NN。

独立QA只审有界summary、输入hash索引、逐request守恒和预选interval witness，不启动第二次全raw扫描；如发现代码错误，保留原分析失败并按新commit重新冻结，不能改结果标签。此草案的目标是一次小CPU收尾；没有结果之前，论文继续使用现成matched16内容数字和F旧36明确分层的机制证据。

# Phase N：源码与协议审计

2026-10-21。正式协议为用户附件 `PROTOCOL_USER.md`，SHA 在 `INTAKE.json`。
项目现行 `AGENTS.md` 已完整读取，副本为 `AGENTS_READ.md`。

## 版本关系

- 当前主仓库 HEAD 为 `7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f`，存在大量用户未提交改动。未 reset、checkout 覆盖或清理。
- 现行核心与 2026-10-15 审计快照的字节关系、与 10-20 E1/E2 SDK 的差异在 `SOURCE_DIFFS.json` 和逐文件 diff。**当前工作树不含 10-20 独立 SDK 的 lazy/canonical-display 改动。** 不能把 10-20 测量当成当前主仓库默认实现的结果。
- 本轮 `sdk/` 从现行工作树复制；显式合入 10-20 已审计的 opt-in lazy carrier、worker fault seam，再逐项添加 A/B/C、完整终止检查与阻塞仪表。没有按旧行号 patch。
- T1 正式源码为 `3b16f2471dade4e69373797706e28fd508eeb61e`；文件 manifest 和 archive 身份见 `SOURCE_T1_IDENTITY.json`。103 个文件的 Git blob 与工作文件逐字节核验。早期 v1 只冻结未运行；v2 在 GPU 启动前修正了显示时间戳一致性及 Git 行尾身份，原 v1 保留。

最终版本晋升记录：以上 v2 是首个完整前后对照（18 cells），不是结项 headline。v3 完整重测 18 cells，去掉循环内富记录序列化；v4 再完整重测 18 cells，分开 worker/同步 GPU model-call/owner 时钟，最终正式表取 **v4 commit `e73115c66d42a15fc3a6907e7161e37ea5e07662`**。先前版本不删、不混入新中位数。所有 SDK 的实际文件/Git blob 字节身份均逐项验证，具体 archive/manifest SHA 由各 `SOURCE_*_IDENTITY.json` 给出。

五个关键现行文件在 intake 时与 10-15 快照逐字节相同，故显式合入 10-20 opt-in 变更没有遗漏其后的用户编辑。28 个源模块和完整当前 tests 仍以当前工作树复制为基础。

公开 `zhouz4884-coder/RevTrace` 的 main 预检为 `eeca911090b1a1bd01be234246f690331484c874`，2180 blobs；该上游尚无 `live_qwen.py`/`tc_live_worker.py` 对应 carrier，另一些核心文件不同。同步采用独立 Phase N 冻结运行时/测试/报告的有界追加，不盲目用旧本地 HEAD 覆盖上游，也不发布无关脏稿件。

## 已读证据

E0 审计 `exports/E0_invariant_audit_20261015.md`，10-20 `RESULTS_REPORT.zh.md`、`EVIDENCE_INDEX.json` 及其全部被索引文件已核对哈希。原稿 II/III/IV 对 selection、可信 caller、frontier rebase、durability 和 adapter 的主张已对照现行实现；本轮不修改这些稿件。

E0 的 621 parent-superseded 不是 621 违规；历史离线重分析为 7/3348 covered-target publication，且没有证明 canonical 污染。10-20 的 delay 收益只属人工交付阻塞，不能作正常性能。正确 context 的 FP16 re-score 识别 24/24 不等于完整 FP32 token/stop/Phi 认证。

## Source → Claim → Trace

| 对象 | 实现/检查 | 必须留下的证据 |
|---|---|---|
| A | proposal receive 的 covered/generation 检查；dispatch 前 lazy scan | enqueue、executor-complete、retired/skipped、逐 fine-window outcome |
| B | 单 in-flight、有限窗口 scan、只对实际下一任务 rebase | 静态前提、CPU 交错及终端无 private 工作退出 |
| C | `_publish_display` 完整版本化文本快照 | transaction、canonical version、实际文本、F/D_ever/visible frontier、回撤/擦除、安装 ACK |
| Canonical history | `commit_canonical_segment` 与 journal frame | certificate、合法父状态/音频区间、WAL 同步/安装、独立重放 |
| Pre-enqueue | event-driven `BlockingObserver` | 原始重叠位图、任务/批成员、进入/退出；UNKNOWN 不补零 |
| Physical WAL | `_write_frame` timing hook | write、fsync 和 owner-call 区间，组共享时间不当独立 GPU 时间 |
| 实际 conditioning | worker processor 之后记录输入 | waveform、rollback prefix、IDs/mask、特征 digest、dtype/batch/stop/预算 |
| V1 | 全候选 token argmax + 终止合法性 + 可信输入下 Phi | 独立 FP32 完整序列/投影 oracle、重复和实际 fallback 成本 |

## 实现审计纠正

1. `verification_tokens=64` 是候选宽度向上补齐，不是截断到 64。
2. 原 `matched == len(candidate)` 可以接受缺 EOS、又未达到预算的短前缀；新增完整 stop/cap 检查，保留合法 token-cap 等价。FP16 margin 不用于 FP32 认证。
3. `auth_busy` 是未接收请求占用，不能标作 GPU 正在执行。新 worker start/complete telemetry 与 owner 接收分开；消息尚未观察到时 execution=UNKNOWN。
4. `auth_result` 不自动表示 barrier hold；只有真实缺 final private result 的 segment commit gate 标记 barrier。并行存在 worker busy 时保留 BOTH。
5. 无 token/audio 对齐，因此 canonical correction 是完整快照，不“无损保留未来字幕”；F 与 D_ever 单调不保证当前可见 frontier/文字不回撤。

## 冻结与状态

原项目测试基线 303 passed；修订核心对完整原 fixtures 加新增测试 353 passed；远端 Linux 定向 65 passed。失败、改版和测量原始数据保留；最终结果与 GO/NO-GO 在对应实验报告给出，不在本审计阶段预判。
